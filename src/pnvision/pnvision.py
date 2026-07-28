"""OpenPnP automation scripts"""

import typer
from pathlib import Path
from typing import Annotated
from typing import Optional

app = typer.Typer(no_args_is_help=True)


@app.command(help="Generate HTML report from log file.")
def report(
    log_file_location: Annotated[
        Path,
        typer.Argument(help="Location of log file."),
    ],
    template_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--template-dir",
            help="Override the built-in template directory.",
        ),
    ] = None,
) -> None:
    from .commands.generate_report import generate_report

    generate_report(
        report_location=log_file_location,
        template_dir=template_dir,
    )


@app.command(help="Stitch OpenPnP images into a single board image.")
def stitch(
    image_directory: Annotated[
        Path,
        typer.Argument(help="Directory containing PNG images."),
    ],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output image filename."),
    ] = None,
    pixels_per_unit_x: Annotated[
        Optional[float],
        typer.Option("--pixels-per-unit-x", "-ppx", help="Pixels per unit in X."),
    ] = None,
    pixels_per_unit_y: Annotated[
        Optional[float],
        typer.Option("--pixels-per-unit-y", "-ppy", help="Pixels per unit in Y."),
    ] = None,
    delete_tiles: Annotated[
        bool,
        typer.Option(
            "--delete-tiles",
            "-d",
            help="Delete board tiles after stitching is finished.",
        ),
    ] = False,
) -> None:
    from .commands.stitch_board import stitch_board

    stitch_board(
        image_directory=image_directory,
        output=output,
        pixels_per_unit_x=pixels_per_unit_x,
        pixels_per_unit_y=pixels_per_unit_y,
        delete_tiles=delete_tiles,
    )


@app.command(help="Read a QR code from an image file and print the decoded contents.")
def code(
    image_path: Annotated[
        Path,
        typer.Argument(..., help="Path to the image containing the QR code."),
    ],
) -> None:
    from .commands.read_code import read_code

    read_code(image_path)


@app.command(help="Read BOM-ALL-ReferenceNotGrouped and return list of dnp designators.")
def bom(
    bom_path: Annotated[
        Path,
        typer.Argument(..., help="Path to the bom."),
    ],
) -> None:
    from .commands.read_bom import read_bom

    read_bom(bom_path)


if __name__ == "__main__":
    app()
