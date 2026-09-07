from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

MIN_COMP_AREA_RATIO = 0.20
MIN_PAD_AREA_RATIO = 0.05

CANNY_THRESH1 = 40
CANNY_THRESH2 = 120

BLUR_KERNEL_RATIO = 0.010
MORPH_KERNEL_RATIO = 0.025

COLOR_COMP = (0, 255, 0)
COLOR_PAD = (255, 0, 0)


def detect_placement(image: np.ndarray, debug_path: Path) -> bool:
    h, w = image.shape[:2]
    total_area = h * w

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    norm_img = clahe.apply(gray)

    b_k = max(3, int(min(w, h) * BLUR_KERNEL_RATIO) | 1)
    m_k = max(3, int(min(w, h) * MORPH_KERNEL_RATIO))

    blurred = cv2.GaussianBlur(norm_img, (b_k, b_k), 0)
    edges = cv2.Canny(blurred, CANNY_THRESH1, CANNY_THRESH2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (m_k, m_k))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    dilated = closed

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    debug_img = image.copy()

    large_contours = []
    pad_contours = []

    for cnt in contours:
        x, y, w_box, h_box = cv2.boundingRect(cnt)
        ratio = (w_box * h_box) / total_area

        if ratio >= MIN_COMP_AREA_RATIO:
            large_contours.append((x, y, w_box, h_box))
        elif MIN_PAD_AREA_RATIO <= ratio < MIN_COMP_AREA_RATIO:
            pad_contours.append((x, y, w_box, h_box))

    placed = False

    if len(large_contours) == 1:
        placed = True
        for x, y, w_box, h_box in large_contours:
            cv2.rectangle(debug_img, (x, y), (x + w_box, y + h_box), COLOR_COMP, 3)
    else:
        placed = False
        for x, y, w_box, h_box in large_contours + pad_contours:
            cv2.rectangle(debug_img, (x, y), (x + w_box, y + h_box), COLOR_PAD, 3)

    cv2.imwrite(str(debug_path), debug_img)

    return placed


def detect_components(
    report_file: Path,
    components_directory: Path,
) -> None:

    with report_file.open("r", encoding="utf-8") as file:
        report: dict[str, Any] = json.load(file)

    parts: list[dict[str, Any]] = report.get("parts", [])

    debug_dir = components_directory / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    discrepancies = 0

    print("--- Starting Component Inspection ---")

    for part in parts:
        designator = str(part.get("designator", "UNKNOWN"))
        image_file = str(part.get("image_file", ""))
        dnp_status = str(part.get("dnp_status", "")).strip().upper()

        if not image_file:
            continue

        image_path = components_directory / image_file

        if not image_path.is_file():
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            continue

        debug_path = debug_dir / f"debug_{image_file}"
        placed = detect_placement(image, debug_path)

        is_dnp = dnp_status == "DNP"

        if is_dnp and placed:
            print(f"DISCREPANCY: JSON says DNP, but component is PLACED | Designator: {designator} ({image_file})")
            part["analyzed_placement_status"] = "DISCREPANCY"
            discrepancies += 1

        elif not is_dnp and not placed:
            print(f"DISCREPANCY: JSON says Placed, but component is MISSING | Designator: {designator} ({image_file})")
            part["analyzed_placement_status"] = "DISCREPANCY"
            discrepancies += 1

    with report_file.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("-------------------------------------")
    print(f"Total Discrepancies Found: {discrepancies}")
    print(f"Debug images exported to: {debug_dir.resolve()}")
