from pathlib import Path


class Paths:
    ROOT = Path(__file__).resolve().parent.parent.parent

    TEMPLATE_DIR = ROOT / "template"
