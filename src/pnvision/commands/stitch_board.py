from pathlib import Path
from numpy.typing import NDArray
from typing import cast

import glob
import os
import re
import cv2
import numpy as np

DEFAULT_PIXELS_PER_UNIT_X = 77
DEFAULT_PIXELS_PER_UNIT_Y = 76
DEFAULT_OUTPUT_FILENAME = "full_board.png"


def create_feather_mask(shape: tuple[int, ...]) -> np.ndarray:
    """2D Bartlett window mask for weighted spatial blending"""
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


def normalize_image(img: NDArray[np.integer | np.floating]) -> NDArray[np.float32]:
    dst = np.empty(img.shape, dtype=np.float32)

    return cast(
        NDArray[np.float32],
        cv2.normalize(
            img,
            dst,
            alpha=0,
            beta=255,
            norm_type=cv2.NORM_MINMAX,
            dtype=cv2.CV_32F,
        ),
    )


def stitch_macro_grid(
    image_directory: Path,
    output_filename: Path,
    delete_tiles: bool = False,
    pixels_per_unit_x: float = DEFAULT_PIXELS_PER_UNIT_X,
    pixels_per_unit_y: float = DEFAULT_PIXELS_PER_UNIT_Y,
) -> None:
    pattern = re.compile(r"^(.+)_r\d+_c\d+_x(\d+\.\d+)_y(\d+\.\d+)\.png$")

    file_list = glob.glob(os.path.join(image_directory, "*.png"))
    image_data = []

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")
    img_shape = None

    for filepath in file_list:
        match = pattern.search(filepath)
        if not match:
            continue

        x_coord = float(match.group(2))
        y_coord = float(match.group(3))
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


def stitch_board(
    image_directory: Path,
    output: Path | None = None,
    pixels_per_unit_x: float | None = None,
    pixels_per_unit_y: float | None = None,
    delete_tiles: bool = False,
) -> None:
    if pixels_per_unit_x is None:
        pixels_per_unit_x = DEFAULT_PIXELS_PER_UNIT_X

    if pixels_per_unit_y is None:
        pixels_per_unit_y = DEFAULT_PIXELS_PER_UNIT_Y

    if output is None:
        output = image_directory / DEFAULT_OUTPUT_FILENAME
    else:
        if output.exists() and output.is_dir():
            output = output / DEFAULT_OUTPUT_FILENAME

        if output.suffix == "":
            output = output.with_suffix(".png")

    print("Initiating coordinate-mapped stitching routine...")

    stitch_macro_grid(
        image_directory=image_directory,
        output_filename=(output),
        delete_tiles=delete_tiles,
        pixels_per_unit_x=pixels_per_unit_x,
        pixels_per_unit_y=pixels_per_unit_y,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python stitch_board.py <image_directory>")

    stitch_board(image_directory=Path(sys.argv[1]))
