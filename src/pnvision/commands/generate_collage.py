from pathlib import Path
from importlib.resources import as_file, files
from jinja2 import Environment, FileSystemLoader

import json
import shutil


def generate_report(
    scans_directory: Path,
    output: Path | None = None,
) -> None:
    if not scans_directory.exists():
        raise FileNotFoundError(scans_directory)

    with as_file(files("pnvision") / "collage_template") as template_dir:
        generate_html_report(
            scans_directory=scans_directory,
            template_dir=template_dir,
            output=output,
        )

    print(f"Generating HTML report from {scans_directory}...")

    generate_html_report(
        scans_directory=scans_directory,
        template_dir=template_dir,
        output=output,
    )
