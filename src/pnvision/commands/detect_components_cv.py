from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def detect_components(
    report_file: Path,
    components_directory: Path,
) -> None:
    with report_file.open("r", encoding="utf-8") as file:
        report: dict[str, Any] = json.load(file)

    parts: list[dict[str, Any]] = report.get("parts", [])

    for part in parts:
        designator = str(part.get("designator", "UNKNOWN"))
        image_file = str(part.get("image_file", ""))
        dnp_status = str(part.get("dnp_status", "")).strip()

        if not image_file:
            continue

        image_path = components_directory / image_file

        if not image_path.is_file():
            continue

        image = cv2.imread(str(image_path))

        if image is None:
            continue

        placed = detect_placement(image)

        if dnp_status and placed:
            print(f"DNP status but component placed: {designator} " f"({image_file})")

        elif not dnp_status and not placed:
            print(f"No DNP status but component not placed: {designator} " f"({image_file})")


def detect_placement(image: np.ndarray) -> bool:
    return True
