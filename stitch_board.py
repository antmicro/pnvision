import cv2
import numpy as np
import re
import os
import glob
import argparse

# ---------------- USER SETTINGS ----------------

PIXELS_PER_UNIT_X = 77
PIXELS_PER_UNIT_Y = 76
OUTPUT_FILENAME = "output.png"

# ------------------------------------------------


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
        img, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F
    )


def stitch_macro_grid(image_directory, pixels_per_unit_x, pixels_per_unit_y):
    pattern = re.compile(r"x(\d+\.\d+)_y(\d+\.\d+)\.png$")

    file_list = glob.glob(os.path.join(image_directory, "*.png"))
    image_data = []

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")
    img_shape = None

    for filepath in file_list:
        match = pattern.search(filepath)
        if match:
            x_coord, y_coord = float(match.group(1)), float(match.group(2))
            image_data.append((filepath, x_coord, y_coord))
            min_x, min_y = min(min_x, x_coord), min(min_y, y_coord)
            max_x, max_y = max(max_x, x_coord), max(max_y, y_coord)

            if img_shape is None:
                sample_img = cv2.imread(filepath)
                if sample_img is not None:
                    img_shape = sample_img.shape

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

        # Rounding is applied to bound truncation drift to +/- 0.5 pixels
        x_pix = int(round((x_coord - min_x) * pixels_per_unit_x))
        y_pix = int(round((max_y - y_coord) * pixels_per_unit_y))

        blended_canvas[y_pix : y_pix + img_shape[0], x_pix : x_pix + img_shape[1]] += (
            img * feather_mask
        )
        weight_canvas[
            y_pix : y_pix + img_shape[0], x_pix : x_pix + img_shape[1]
        ] += feather_mask

    final_stitched = np.divide(
        blended_canvas,
        weight_canvas,
        out=np.zeros_like(blended_canvas),
        where=weight_canvas != 0,
    )
    final_stitched = np.clip(final_stitched, 0, 255).astype(np.uint8)

    cv2.imwrite(OUTPUT_FILENAME, final_stitched)
    print(f"Algorithm terminated. Data written to: {OUTPUT_FILENAME}")


def main():
    parser = argparse.ArgumentParser(description="Stitch images from PnP.")
    parser.add_argument(
        "image_directory", help="Path to the directory containing PNG images"
    )
    args = parser.parse_args()

    print("Initiating coordinate-mapped stitching routine...")
    stitch_macro_grid(args.image_directory, PIXELS_PER_UNIT_X, PIXELS_PER_UNIT_Y)


if __name__ == "__main__":
    main()
