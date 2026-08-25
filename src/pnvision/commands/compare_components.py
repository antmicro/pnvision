import glob
from pathlib import Path

import cv2
import numpy as np

ROTATIONS = range(0, 360, 15)
TOP_N = 10
BASE_DIR = Path(__file__).resolve().parent.parent

CLAHE_WEIGHT = 0.25
LOCAL_CONTRAST_WEIGHT = 0.45
EDGE_WEIGHT = 0.30


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
        borderMode=cv2.BORDER_REPLICATE,
    )


def load_templates(
    path: Path,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    templates = []

    files = glob.glob(str(path / "*.png"))

    for filename in files:
        image = cv2.imread(
            filename,
            cv2.IMREAD_GRAYSCALE,
        )

        if image is None:
            print(f"Could not read: {filename}")
            continue

        for angle in ROTATIONS:
            rotated = rotate(image, angle)
            templates.append(prep(rotated))

    return templates


def match_representation(
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

    return float(np.mean(top_scores))


def best_match(
    image: np.ndarray,
    templates: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> float:
    image_clahe, image_local, image_edges = prep(image)

    clahe_templates = [template[0] for template in templates]
    local_templates = [template[1] for template in templates]
    edge_templates = [template[2] for template in templates]

    clahe_score = match_representation(
        image_clahe,
        clahe_templates,
    )

    local_score = match_representation(
        image_local,
        local_templates,
    )

    edge_score = match_representation(
        image_edges,
        edge_templates,
    )

    return CLAHE_WEIGHT * clahe_score + LOCAL_CONTRAST_WEIGHT * local_score + EDGE_WEIGHT * edge_score


def detect_component(input_path: Path) -> None:
    image = cv2.imread(
        str(input_path),
        cv2.IMREAD_GRAYSCALE,
    )

    if image is None:
        raise ValueError(f"Could not read image: {input_path}")

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

    print(result)
    # print(f"placed_score:     {placed_score:.4f}")
    # print(f"not_placed_score: {not_placed_score:.4f}")
    # print(f"margin:           {margin:+.4f}")
    # print(f"result:           {result}")
