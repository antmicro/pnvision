"""Detects whether SMD components are placed using computer vision methods."""

import cv2
import json
import numpy as np
from pathlib import Path
from typing import Any

GAUSSIAN_BLUR_KSIZE = 5
MEDIAN_BLUR_KSIZE = 5
THRESH_MIN_VAL = 15
MIN_CONTOUR_AREA = 1000.0
MIN_COMPONENT_RATIO = 0.15


def process_image(image_path: Path, debug_dir: Path | None) -> tuple[bool, np.ndarray | None, list, list]:
    """Applies the vision pipeline to determine if a rectangular SMD component is placed."""

    img = cv2.imread(str(image_path))
    if img is None:
        return False, None, [], []

    debug_img = img.copy() if debug_dir else None
    image_area = img.shape[0] * img.shape[1]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gauss = cv2.GaussianBlur(gray, (GAUSSIAN_BLUR_KSIZE, GAUSSIAN_BLUR_KSIZE), 0)

    median = cv2.medianBlur(gauss, MEDIAN_BLUR_KSIZE)

    _, thresh = cv2.threshold(median, THRESH_MIN_VAL, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= MIN_CONTOUR_AREA:
            valid_contours.append(cnt)

    valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)

    is_placed = False
    component_rects = []
    pad_rects = []

    if not valid_contours:
        is_placed = False
    else:
        largest_area = cv2.contourArea(valid_contours[0])

        if largest_area >= (MIN_COMPONENT_RATIO * image_area) or len(valid_contours) == 1:
            is_placed = True
            component_rects.append(cv2.minAreaRect(valid_contours[0]))
        else:
            is_placed = False
            for cnt in valid_contours:
                pad_rects.append(cv2.minAreaRect(cnt))

    if debug_img is not None:
        for rect in pad_rects:
            box = cv2.boxPoints(rect)
            box_i32 = box.astype(np.int32)
            cv2.drawContours(debug_img, [box_i32], 0, (255, 0, 0), 4)

        for rect in component_rects:
            box = cv2.boxPoints(rect)
            box_i32 = box.astype(np.int32)
            cv2.drawContours(debug_img, [box_i32], 0, (0, 255, 0), 4)

    return is_placed, debug_img, component_rects, pad_rects


def detect_components(report_file: Path, components_directory: Path, save_debug: bool = False) -> None:
    """Compares DNP status from report with images using computer vision."""

    with report_file.open("r", encoding="utf-8") as file:
        report: dict[str, Any] = json.load(file)

    parts: list[dict[str, Any]] = report.get("parts", [])

    debug_dir = None
    if save_debug:
        debug_dir = components_directory / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)

    discrepancies = 0

    print("Starting Component Inspection")

    for part in parts:
        designator = str(part.get("designator", "UNKNOWN"))
        image_file = str(part.get("image_file", ""))
        dnp_status = str(part.get("dnp_status", "")).strip().upper()

        is_dnp = dnp_status == "DNP"

        if not image_file:
            continue

        image_path = components_directory / image_file
        if not image_path.is_file():
            print(f"Warning: Image file not found for {designator} ({image_file})")
            continue

        placed, debug_img, _, _ = process_image(image_path, debug_dir)

        if save_debug and debug_img is not None and debug_dir is not None:
            debug_path = debug_dir / image_file
            cv2.imwrite(str(debug_path), debug_img)

        if is_dnp and placed:
            print(f"DISCREPANCY: JSON says DNP, but component is PLACED | Designator: {designator} ({image_file})")
            part["analyzed_placement_status"] = "DISCREPANCY"
            discrepancies += 1

        elif not is_dnp and not placed:
            print(f"DISCREPANCY: JSON says Placed, but component is MISSING | Designator: {designator} ({image_file})")
            part["analyzed_placement_status"] = "DISCREPANCY"
            discrepancies += 1

        else:
            part["analyzed_placement_status"] = "MATCH"

    with report_file.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=4)

    print("Inspection Complete")
    print(f"Total discrepancies found: {discrepancies}")
