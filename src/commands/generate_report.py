from pathlib import Path
import json
import shutil

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from helpers.bash_wrapper import bash


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "report",
        help="Generate HTML report from log file.",
    )

    parser.add_argument(
        "log_file_location",
        help="Location of log file.",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "template",
        help="Directory defualt containing template for report.html",
    )

    parser.set_defaults(func=run)


def run(args):
    log_path = Path(args.log_file_location)

    with log_path.open("r", encoding="utf-8") as f:
        log = json.load(f)

    input_dir = log_path.parent

    scan_dir = next((p for p in input_dir.glob("scan*") if p.is_dir()), None)
    if scan_dir is None:
        raise FileNotFoundError(f"No scan* directory found in {input_dir}")
    print(scan_dir)

    bash(f"pnvision stitch {scan_dir}", "board_stitch")

    output_dir = input_dir / "report"
    output_dir.mkdir(exist_ok=True)

    template_dir = Path(__file__).resolve().parents[2] / "template"

    environment = Environment(loader=FileSystemLoader(template_dir))

    template = environment.get_template("report.html")

    for asset in (
        "logo.svg",
        "favicon.ico",
    ):
        source = template_dir / asset
        if source.exists():
            shutil.copyfile(source, output_dir / asset)

    board_image = input_dir / "full_board.png"
    if board_image.exists():
        shutil.copyfile(board_image, output_dir / "full_board.png")

    parts = pd.DataFrame(log.get("parts", []))

    content = template.render(
        metadata=log.get("metadata", {}), project_name=log.get("project_name", "Unknown"), parts=parts
    )

    output_path = output_dir / "report.html"

    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)

    print(f"Report written to {output_path}")
