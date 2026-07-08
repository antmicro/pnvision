from pathlib import Path

import cv2
import numpy as np
from pyzbar.pyzbar import decode


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "code",
        help="Find and read QR-code or Code128 barcode.",
    )

    parser.add_argument(
        "image_location",
        help="Location of image to inspect.",
    )

    parser.set_defaults(func=run)


def generate_variants(image):
    """Generate multiple image variants to improve decoding robustness."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    variants = []

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    sharpen_kernel = np.array(
        [
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0],
        ],
        dtype=np.float32,
    )

    variants.append(gray)
    cv2.imwrite("test_gray.png", gray)
    # CLAHE
    variants.append(clahe.apply(gray))
    cv2.imwrite("test_clahe.png", clahe.apply(gray))
    # Otsu
    _, otsu = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    variants.append(otsu)
    cv2.imwrite("test_otsu.png", otsu)
    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        3,
    )
    variants.append(adaptive)
    cv2.imwrite("test_adaptive.png", adaptive)
    # Sharpen
    sharpen = cv2.filter2D(
        gray,
        -1,
        sharpen_kernel,
    )
    cv2.imwrite("test_sharpen.png", sharpen)
    variants.append(sharpen)

    # Blackhat
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (15, 5),
    )

    blackhat = cv2.morphologyEx(
        gray,
        cv2.MORPH_BLACKHAT,
        kernel,
    )
    cv2.imwrite("test_blackhat.png", blackhat)
    variants.append(blackhat)

    return variants


def rotations(image):
    """Generate four image orientations."""
    yield image
    yield cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    yield cv2.rotate(image, cv2.ROTATE_180)
    yield cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)


def detect_codes(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(f"Unable to load image: {image_path}")

    qr_detector = cv2.QRCodeDetector()

    seen = set()

    for variant in generate_variants(image):

        for candidate in rotations(variant):

            # ---------- QR ----------
            value, _, _ = qr_detector.detectAndDecode(candidate)

            if value and value not in seen:
                seen.add(value)
                print(f"QR Code : {value}")
                return

            # ---------- Barcode ----------
            barcodes = decode(candidate)

            for barcode in barcodes:

                value = barcode.data.decode(
                    "utf-8",
                    errors="ignore",
                )

                if value in seen:
                    continue

                seen.add(value)

                print(f"{barcode.type}: {value}")
                return

    print("No barcode or QR code found.")


def run(args):
    image = Path(args.image_location)

    if not image.exists():
        raise FileNotFoundError(image)

    print(f"Searching for QR codes and barcodes in {image}...")

    detect_codes(image)
