from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from helpers.bash_wrapper import bash
from importlib.resources import files, as_file

import argparse
import json
import shutil
import pandas as pd


def add_subparser(subparsers: argparse._SubParsersAction) -> None:
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
        help="Override the built-in template directory.",
    )

    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    log_path = Path(args.log_file_location)

    with log_path.open("r", encoding="utf-8") as f:
        log = json.load(f)

    input_dir = log_path.parent
    output_dir = input_dir / "report"
    output_dir.mkdir(exist_ok=True)

    board_dir = next((p for p in input_dir.glob("*board*") if p.is_dir()), None)
    if board_dir is None:
        print(f"No board directory found in {input_dir}. Add full_board.png to report/ directory")
    else:
        bash(f"pnvision stitch {board_dir}", "board_stitch")

        board_image = board_dir / "full_board.png"
        if board_image.exists():
            shutil.copy2(board_image, output_dir / "full_board.png")
        else:
            print("Add full_board.png to report/ directory.")

    components_dir = next((p for p in input_dir.glob("*components*") if p.is_dir()), None)
    if components_dir is None:
        print(f"No components directory found in {input_dir}.")
    else:
        shutil.copytree(components_dir, output_dir / "components", dirs_exist_ok=True)

    if args.template_dir is not None:
        template_dir = args.template_dir
        environment = Environment(loader=FileSystemLoader(template_dir))
        template = environment.get_template("report.html")

        for asset in ("logo.svg", "favicon.ico"):
            shutil.copy2(template_dir / asset, output_dir / asset)

    else:
        with as_file(files("template")) as template_dir:
            environment = Environment(loader=FileSystemLoader(template_dir))
            template = environment.get_template("report.html")

            for asset in ("logo.svg", "favicon.ico"):
                shutil.copy2(template_dir / asset, output_dir / asset)

    parts = pd.DataFrame(log.get("parts", []))

    content = template.render(
        metadata=log.get("metadata", {}), project_name=log.get("project_name", "Unknown"), parts=parts
    )

    output_path = output_dir / "report.html"

    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)

    print(f"Report written to {output_path}")
