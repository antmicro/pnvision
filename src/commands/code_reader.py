from pathlib import Path

import cv2
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


def detect_codes(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(f"Unable to load image: {image_path}")

    found = False
    seen = set()

    qr_detector = cv2.QRCodeDetector()

    success, decoded_info, points, _ = qr_detector.detectAndDecodeMulti(image)

    if success:
        for text in decoded_info:
            if text:
                print(f"QR Code : {text}")
                seen.add(text)
                found = True

    for code in decode(image):
        value = code.data.decode("utf-8", errors="ignore")

        if value in seen:
            continue

        seen.add(value)
        found = True

        print(f"{code.type}: {value}")

    if not found:
        print("No barcode or QR code found.")


def run(args):
    image = Path(args.image_location)

    if not image.exists():
        raise FileNotFoundError(image)

    print(f"Searching for QR codes and barcodes in {image}...")

    detect_codes(image)
