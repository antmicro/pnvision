from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np

CLAHE_WEIGHT = 0.30
LOCAL_CONTRAST_WEIGHT = 0.55
EDGE_WEIGHT = 0.15
IMAGE_SIZE = (256, 256)
OUTLIER_Z_THRESHOLD = 10.0

SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
}


def prep(img: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(img)

    background = cv2.GaussianBlur(
        enhanced,
        (0, 0),
        sigmaX=3.0,
        sigmaY=3.0,
    )

    local_contrast = cv2.absdiff(
        enhanced,
        background,
    )

    normalized = np.empty_like(local_contrast)

    cv2.normalize(
        local_contrast,
        normalized,
        0,
        255,
        cv2.NORM_MINMAX,
    )

    local_contrast = normalized.astype(np.uint8)

    edges = cv2.Canny(
        enhanced,
        20,
        80,
    )

    return enhanced, local_contrast, edges


def load_json(path: Path) -> dict[str, Any]:
    import json

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")

    return data


def find_serial_number(report: dict[str, Any], path: Path) -> str:
    candidates = (
        ("scan", "serial_number"),
        ("scan", "serial"),
        ("pcb", "serial_number"),
        ("pcb", "serial"),
        ("sourcing", "serial_number"),
        ("serial_number",),
        ("serial",),
    )

    for keys in candidates:
        value: Any = report

        for key in keys:
            if not isinstance(value, dict):
                value = None
                break

            value = value.get(key)

        if value is not None and str(value).strip():
            return str(value)

    raise ValueError(f"Could not find serial number in {path}")


def find_parts(report: dict[str, Any], path: Path) -> list[dict[str, Any]]:
    parts = report.get("parts")

    if not isinstance(parts, list):
        raise ValueError(f"Could not find 'parts' list in {path}")

    return [part for part in parts if isinstance(part, dict)]


def find_component_file(
    components_dir: Path,
    part: dict[str, Any],
) -> Path | None:
    image_file = part.get("image_file")

    if isinstance(image_file, str):
        path = components_dir / image_file

        if path.is_file():
            return path

    designator = part.get("designator")

    if not isinstance(designator, str):
        return None

    matches = sorted(
        path
        for path in components_dir.iterdir()
        if (path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and path.name.startswith(f"{designator}_"))
    )

    if not matches:
        return None

    return matches[0]


def center_component(
    image: np.ndarray,
) -> np.ndarray:
    height, width = image.shape

    border_size = max(
        5,
        min(height, width) // 20,
    )

    border_pixels = np.concatenate(
        (
            image[:border_size, :].ravel(),
            image[-border_size:, :].ravel(),
            image[:, :border_size].ravel(),
            image[:, -border_size:].ravel(),
        )
    )

    background_value = float(np.median(border_pixels))

    difference = cv2.absdiff(
        image,
        np.full_like(image, background_value),
    )

    threshold = max(
        10.0,
        float(np.percentile(difference, 85)),
    )

    mask = (difference > threshold).astype(np.uint8) * 255

    kernel = np.ones(
        (3, 3),
        dtype=np.uint8,
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel,
    ).astype(np.uint8)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
    ).astype(np.uint8)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return cv2.resize(
            image,
            IMAGE_SIZE,
            interpolation=cv2.INTER_AREA,
        )

    contour = max(
        contours,
        key=cv2.contourArea,
    )

    x, y, w, h = cv2.boundingRect(contour)

    if w < 3 or h < 3:
        return cv2.resize(
            image,
            IMAGE_SIZE,
            interpolation=cv2.INTER_AREA,
        )

    cropped = image[y : y + h, x : x + w]

    target_width, target_height = IMAGE_SIZE

    scale = min(
        (target_width * 0.70) / w,
        (target_height * 0.70) / h,
    )

    new_width = max(1, int(round(w * scale)))
    new_height = max(1, int(round(h * scale)))

    resized = cv2.resize(
        cropped,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )

    canvas = np.full(
        (target_height, target_width),
        int(round(background_value)),
        dtype=np.uint8,
    )

    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2

    canvas[
        y_offset : y_offset + new_height,
        x_offset : x_offset + new_width,
    ] = resized

    return canvas


def load_image(path: Path) -> np.ndarray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE,
    )

    if image is None:
        raise ValueError(f"Could not read image: {path}")

    return center_component(image)


def representation(image: np.ndarray) -> np.ndarray:
    enhanced, local_contrast, edges = prep(image)

    enhanced_f = enhanced.astype(np.float32) / 255.0
    local_f = local_contrast.astype(np.float32) / 255.0
    edges_f = edges.astype(np.float32) / 255.0

    return CLAHE_WEIGHT * enhanced_f + LOCAL_CONTRAST_WEIGHT * local_f + EDGE_WEIGHT * edges_f


def difference_score(
    image: np.ndarray,
    reference: np.ndarray,
) -> float:
    return float(np.mean(np.abs(image - reference)))


def robust_z_scores(scores: np.ndarray) -> np.ndarray:
    median = np.median(scores)

    mad = np.median(np.abs(scores - median))

    if mad < 1e-9:
        return np.zeros_like(scores)

    return 0.6745 * (scores - median) / mad


def compare_group(
    designator: str,
    components: list[tuple[str, Path]],
) -> None:
    if len(components) < 2:
        return

    images: list[np.ndarray] = []
    valid_components: list[tuple[str, Path]] = []

    for serial_number, path in components:
        try:
            image = load_image(path)
        except ValueError as exc:
            print(f"WARNING: {exc}")
            continue

        images.append(representation(image))

        valid_components.append((serial_number, path))

    if len(images) < 2:
        return

    stacked = np.stack(
        images,
        axis=0,
    )

    reference = np.median(
        stacked,
        axis=0,
    )

    scores = np.array(
        [
            difference_score(
                image,
                reference,
            )
            for image in images
        ],
        dtype=np.float32,
    )

    z_scores = robust_z_scores(scores)

    for (
        (
            serial_number,
            _path,
        ),
        score,
        z_score,
    ) in zip(
        valid_components,
        scores,
        z_scores,
        strict=True,
    ):
        if abs(float(z_score)) > OUTLIER_Z_THRESHOLD:
            print(f"OUTLIER  " f"{designator:<8} " f"{serial_number:<15} " f"score={score:.4f} " f"z={z_score:.2f}")


def compare_components(
    scans_directory: Path,
) -> None:
    scans_directory = scans_directory.resolve()

    if not scans_directory.is_dir():
        raise NotADirectoryError(scans_directory)

    by_designator: dict[
        str,
        list[tuple[str, Path]],
    ] = defaultdict(list)

    scan_dirs = sorted(path for path in scans_directory.iterdir() if path.is_dir())

    for scan_dir in scan_dirs:
        components_dir = scan_dir / "components"

        if not components_dir.is_dir():
            continue

        json_files = sorted(scan_dir.glob("*.json"))

        if not json_files:
            print(f"WARNING: No JSON file found in {scan_dir}")
            continue

        report_path = json_files[0]

        try:
            report = load_json(report_path)
            serial_number = find_serial_number(report, report_path)
            parts = find_parts(report, report_path)
        except ValueError as exc:
            print(f"WARNING: {exc}")
            continue

        for part in parts:
            designator = part.get("designator")

            if not isinstance(designator, str):
                continue

            component_path = find_component_file(components_dir, part)

            if component_path is None:
                continue

            by_designator[designator].append((serial_number, component_path))

    for designator in sorted(by_designator):
        compare_group(
            designator,
            by_designator[designator],
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=("Compare components with the same designator " "across scans and detect outliers.")
    )

    parser.add_argument(
        "scans_directory",
        type=Path,
        help="Directory containing scan directories.",
    )

    args = parser.parse_args()

    compare_components(
        scans_directory=args.scans_directory,
    )
