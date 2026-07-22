from pathlib import Path
import glob
import os
import re

import cv2
import numpy as np

DEFAULT_PIXELS_PER_UNIT_X = 77
DEFAULT_PIXELS_PER_UNIT_Y = 76
DEAFULT_OUTPUT_FILENAME = "full_board.png"


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "stitch",
        help="Stitch OpenPnP images into a single board image.",
    )
    parser.add_argument(
        "image_directory",
        help="Directory containing PNG images.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEAFULT_OUTPUT_FILENAME,
        help=f"Output image filename (default: {DEAFULT_OUTPUT_FILENAME})",
    )
    parser.add_argument(
        "-ppx",
        "--pixels-per-unit-x",
        type=float,
        default=DEFAULT_PIXELS_PER_UNIT_X,
        help=f"Pixels per unit in X (default: {DEFAULT_PIXELS_PER_UNIT_X})",
    )
    parser.add_argument(
        "-ppy",
        "--pixels-per-unit-y",
        type=float,
        default=DEFAULT_PIXELS_PER_UNIT_Y,
        help=f"Pixels per unit in Y (default: {DEFAULT_PIXELS_PER_UNIT_Y})",
    )
    parser.add_argument(
        "-d",
        "--delete_tiles",
        action="store_true",
        help="Delete board tiles after stitching is finished.",
    )

    parser.set_defaults(func=run)


def create_feather_mask(shape):
    # 2D Bartlett window mask for weighted spatial blending
    h, w = shape[:2]
    y = np.linspace(0, 1, h)
    y = np.minimum(y, 1 - y)
    x = np.linspace(0, 1, w)
    x = np.minimum(x, 1 - x)
    mask = np.outer(y, x)
    mask = np.clip(mask, 1e-5, None)
    if len(shape) == 3:
        mask = np.dstack([mask] * shape[2])
    return mask


def normalize_image(img):
    return cv2.normalize(
        img,
        None,
        alpha=0,
        beta=255,
        norm_type=cv2.NORM_MINMAX,
        dtype=cv2.CV_32F,
    )


def stitch_macro_grid(
    image_directory,
    output_filename,
    delete_tiles=False,
    pixels_per_unit_x=DEFAULT_PIXELS_PER_UNIT_X,
    pixels_per_unit_y=DEFAULT_PIXELS_PER_UNIT_Y,
):
    pattern = re.compile(r"x(\d+\.\d+)_y(\d+\.\d+)\.png$")

    file_list = glob.glob(os.path.join(image_directory, "*.png"))
    image_data = []

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")
    img_shape = None

    for filepath in file_list:
        match = pattern.search(filepath)
        if not match:
            continue

        x_coord = float(match.group(1))
        y_coord = float(match.group(2))
        image_data.append((filepath, x_coord, y_coord))

        min_x = min(min_x, x_coord)
        min_y = min(min_y, y_coord)
        max_x = max(max_x, x_coord)
        max_y = max(max_y, y_coord)

        if img_shape is None:
            sample = cv2.imread(filepath)
            if sample is not None:
                img_shape = sample.shape

    if not image_data or img_shape is None:
        print("No valid images detected.")
        return

    canvas_w = int(round((max_x - min_x) * pixels_per_unit_x)) + img_shape[1]
    canvas_h = int(round((max_y - min_y) * pixels_per_unit_y)) + img_shape[0]

    blended_canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
    weight_canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)

    feather_mask = create_feather_mask(img_shape)

    for filepath, x_coord, y_coord in image_data:
        img = cv2.imread(filepath)
        if img is None:
            continue

        img = normalize_image(img)

        x_pix = int(round((x_coord - min_x) * pixels_per_unit_x))
        y_pix = int(round((max_y - y_coord) * pixels_per_unit_y))

        blended_canvas[y_pix : y_pix + img_shape[0], x_pix : x_pix + img_shape[1]] += img * feather_mask

        weight_canvas[y_pix : y_pix + img_shape[0], x_pix : x_pix + img_shape[1]] += feather_mask

    final = np.divide(
        blended_canvas,
        weight_canvas,
        out=np.zeros_like(blended_canvas),
        where=weight_canvas != 0,
    )

    final = np.clip(final, 0, 255).astype(np.uint8)

    cv2.imwrite(output_filename, final)
    print(f"Algorithm terminated. Data written to: {output_filename}")

    if delete_tiles:
        for filepath, _, _ in image_data:
            os.remove(filepath)
        print("Deleted input tile images.")


def run(args):
    image_dir = Path(args.image_directory)
    output = Path(args.output)

    if args.output == DEAFULT_OUTPUT_FILENAME:
        output = image_dir / DEAFULT_OUTPUT_FILENAME
    else:
        if output.exists() and output.is_dir():
            output = output / DEAFULT_OUTPUT_FILENAME

        if output.suffix == "":
            output = output.with_suffix(".png")

    print("Initiating coordinate-mapped stitching routine...")

    stitch_macro_grid(
        image_directory=args.image_directory,
        output_filename=str(output),
        delete_tiles=args.delete_tiles,
        pixels_per_unit_x=args.pixels_per_unit_x,
        pixels_per_unit_y=args.pixels_per_unit_y,
    )
