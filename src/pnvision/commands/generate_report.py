from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from importlib.resources import as_file, files
from .read_bom import read_bom

import json
import shutil
import pandas as pd

from .helpers.bash_wrapper import bash


def generate_html_report(
    report_location: Path,
    template_dir: Path,
) -> None:

    with report_location.open("r", encoding="utf-8") as f:
        log = json.load(f)

    input_dir = report_location.parent

    # bom_path = next(input_dir.glob("*BOM-ALL*.csv"))
    bom_path = next(input_dir.glob("*BOM-ALL-ReferenceNotGrouped.csv"), None)
    output_dir = input_dir / "report"
    output_dir.mkdir(exist_ok=True)

    copydirs(input_dir, output_dir, report_location, template_dir)

    environment = Environment(loader=FileSystemLoader(template_dir))
    template = environment.get_template("report.html")

    parts = pd.DataFrame(log.get("parts", []))
    if bom_path is not None:
        parts = add_bom_status(parts, bom_path)
    else:
        print("No BOM file found.")

    content = template.render(
        tools=log.get("tools", {}),
        scan=log.get("scan", {}),
        pcb=log.get("pcb", {}),
        sourcing=log.get("sourcing", {}),
        parts=parts,
    )

    output_path = output_dir / "report.html"

    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)

    print(f"Report written to {output_path}")


def copydirs(input_dir: Path, output_dir: Path, report_location: Path, template_dir: Path) -> Path | None:
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
        bash(f"pnvision detect-cv {report_location} {components_dir}", "detect_dnp_disrepancies")

    for asset in ("logo.svg", "favicon.ico"):
        shutil.copy2(template_dir / asset, output_dir / asset)

    return output_dir / "components"


def add_bom_status(part: pd.DataFrame, bom_path: Path) -> pd.DataFrame:
    bom_designators, bom_dnp_designators = read_bom(bom_path)

    # Parts in the report come from the openPnP board (from position files).
    def bom_status(designator: str) -> str:
        if designator in bom_dnp_designators:
            return "DNP"
        if designator in bom_designators:
            return "NO"
        return "-"

    part = part.copy()
    part["dnp"] = part["designator"].map(bom_status)
    return part


def generate_report(
    report_location: Path,
    template_dir: Path | None = None,
) -> None:
    if not report_location.exists():
        raise FileNotFoundError(report_location)

    if template_dir is None:
        with as_file(files("pnvision") / "template") as template_dir:
            generate_html_report(report_location, template_dir)
        return
    print(f"Generating HTML report from {report_location}...")

    generate_html_report(
        report_location=report_location,
        template_dir=template_dir,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python generate_report.py <report.json>")

    generate_report(report_location=Path(sys.argv[1]))
