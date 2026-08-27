from pathlib import Path
from importlib.resources import as_file, files
from jinja2 import Environment, FileSystemLoader

import json
import shutil


def generate_html_report(
    scans_directory: Path,
    template_dir: Path,
    output: Path | None = None,
) -> None:
    scans_directory = scans_directory.resolve()

    if not scans_directory.is_dir():
        raise NotADirectoryError(scans_directory)

    if output is None:
        output_dir = scans_directory / "report"
        output_path = output_dir / "collage_report.html"
    else:
        output = output.resolve()

        if output.suffix.lower() == ".html":
            output_path = output
            output_dir = output.parent
        else:
            output_dir = output
            output_path = output_dir / "collage_report.html"

    output_dir.mkdir(parents=True, exist_ok=True)

    scan_dirs = sorted(p for p in scans_directory.iterdir() if p.is_dir() and (p / "report.json").is_file())

    reports: list[dict] = []

    # designator -> serial number -> component filename
    components_by_designator: dict[str, dict[str, str]] = {}
    serial_numbers: list[str] = []

    components_output_dir = output_dir / "components"
    components_output_dir.mkdir(parents=True, exist_ok=True)

    for scan_dir in scan_dirs:
        report_path = scan_dir / "report.json"

        with report_path.open("r", encoding="utf-8") as f:
            report = json.load(f)

        report["_scan_directory"] = scan_dir.name
        reports.append(report)

        components_dir = scan_dir / "components"

        if not components_dir.is_dir():
            continue

        for component_path in components_dir.iterdir():
            if not component_path.is_file():
                continue

            designator = component_path.name.split("_", 1)[0]
            serial_number = scan_dir.name.split("_", 1)[0]

            if serial_number not in serial_numbers:
                serial_numbers.append(serial_number)

            destination = components_output_dir / component_path.name
            shutil.copy2(component_path, destination)

            components_by_designator.setdefault(
                designator,
                {},
            )[serial_number] = component_path.name

    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
    )

    template = environment.get_template("report.html")

    content = template.render(
        reports=reports,
        scans=reports,
        components=components_output_dir,
        components_by_designator=components_by_designator,
        serial_numbers=serial_numbers,
    )

    output_path.write_text(content, encoding="utf-8")

    for asset_name in ("logo.svg", "favicon.ico"):
        asset_path = template_dir / asset_name

        if asset_path.is_file():
            shutil.copy2(
                asset_path,
                output_dir / asset_name,
            )

    print(f"Report written to {output_path}")


def generate_report(
    scans_directory: Path,
    output: Path | None = None,
) -> None:
    if not scans_directory.exists():
        raise FileNotFoundError(scans_directory)

    print(f"Generating HTML report from {scans_directory}...")

    with as_file(files("pnvision") / "collage_template") as template_dir:
        generate_html_report(
            scans_directory=scans_directory,
            template_dir=template_dir,
            output=output,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python generate_collage.py <scans dir>")

    generate_report(scans_directory=Path(sys.argv[1]))
