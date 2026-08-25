import glob
from pathlib import Path

import cv2
import numpy as np


ROTATIONS = range(0, 360, 15)
TOP_N = 10
BASE_DIR = Path(__file__).resolve().parent.parent


def prep(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    return clahe.apply(gray)


def rotate(img: np.ndarray, angle: int) -> np.ndarray:
    height, width = img.shape[:2]

    matrix = cv2.getRotationMatrix2D(
        (width / 2, height / 2),
        angle,
        1.0,
    )

    return cv2.warpAffine(
        img,
        matrix,
        (width, height),
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def load_templates(path: Path) -> list[np.ndarray]:
    templates: list[np.ndarray] = []

    files = glob.glob(str(path / "*.png"))

    for filename in files:
        image = cv2.imread(filename)

        if image is None:
            print(f"Could not read: {filename}")
            continue

        for angle in ROTATIONS:
            rotated = rotate(image, angle)
            templates.append(prep(rotated))

    return templates


def best_match(
    image: np.ndarray,
    templates: list[np.ndarray],
) -> float:
    scores: list[float] = []

    for template in templates:
        if template.shape != image.shape:
            continue

        result = cv2.matchTemplate(
            image,
            template,
            cv2.TM_CCOEFF_NORMED,
        )

        score = float(cv2.minMaxLoc(result)[1])
        scores.append(score)

    if not scores:
        return -1.0

    scores.sort(reverse=True)

    top_scores = scores[:TOP_N]

    return sum(top_scores) / len(top_scores)


def detect_component(input_path: Path) -> None:
    image = cv2.imread(str(input_path))

    if image is None:
        raise ValueError(f"Could not read image: {input_path}")

    image = prep(image)

    placed = load_templates(
        BASE_DIR / "examples" / "placed",
    )

    not_placed = load_templates(
        BASE_DIR / "examples" / "not_placed",
    )

    placed_score = best_match(
        image,
        placed,
    )

    not_placed_score = best_match(
        image,
        not_placed,
    )

    margin = placed_score - not_placed_score

    result = "placed" if margin > 0 else "not_placed"

    # print(result)
    print(f"placed_score:     {placed_score:.4f}")
    print(f"not_placed_score: {not_placed_score:.4f}")
    print(f"margin:           {margin:+.4f}")
    print(f"result:           {result}")
