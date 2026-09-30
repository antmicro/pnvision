"""Reads qr code and barcode in the image using computer vision."""

from pathlib import Path
from pyzbar.pyzbar import decode
from collections.abc import Iterator

import cv2
import numpy as np


def get_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert an image to grayscale."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def get_clahe(gray: np.ndarray) -> np.ndarray:
    """Enhance local contrast using CLAHE."""
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def get_otsu(gray: np.ndarray) -> np.ndarray:
    """Binarize an image using Otsu's thresholding."""
    _, otsu = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return otsu


def get_adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Binarize an image using adaptive Gaussian thresholding."""
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        3,
    )


def get_sharpened(gray: np.ndarray) -> np.ndarray:
    """Sharpen image details using a convolution kernel."""
    sharpen_kernel = np.array(
        [
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0],
        ],
        dtype=np.float32,
    )
    return cv2.filter2D(gray, -1, sharpen_kernel)


def get_blackhat(gray: np.ndarray) -> np.ndarray:
    """Extract dark regions on a light background using black-hat morphology."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    return cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)


def generate_variants(image: np.ndarray) -> list[np.ndarray]:
    """Generate multiple image variants to improve decoding robustness."""
    gray = get_grayscale(image)

    return [
        gray,
        get_clahe(gray),
        get_otsu(gray),
        get_adaptive_threshold(gray),
        get_sharpened(gray),
        get_blackhat(gray),
    ]


def rotations(image: np.ndarray) -> Iterator[np.ndarray]:
    """Generate four image orientations."""
    yield image
    yield cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    yield cv2.rotate(image, cv2.ROTATE_180)
    yield cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def detect_codes(image_path: Path) -> set[str]:
    """Loop through every variant and detect qr and barcode."""
    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(f"Unable to load image: {image_path}")

    qr_detector = cv2.QRCodeDetector()

    seen = set()

    for variant in generate_variants(image):
        for candidate in rotations(variant):
            # QR code detection
            value, _, _ = qr_detector.detectAndDecode(candidate)

            if value and value not in seen:
                seen.add(value)
                continue

            # Code128 Barcode detection
            decoded_objects = decode(candidate)

            for obj in decoded_objects:
                barcode_data = obj.data.decode("utf-8")
                seen.add(barcode_data)
                continue
    return seen


def read_code(image: Path) -> set[str]:
    """Read qr codes and barcodes from image, print first one found."""
    if not image.exists():
        raise FileNotFoundError(image)

    codes = detect_codes(image)

    if codes:
        print(next(iter(codes)))  # first element of set

    return codes


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python code_reader.py <image_path>")

    codes = read_code(Path(sys.argv[1]))
    print(codes)
