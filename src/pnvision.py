"""OpenPnP automation scripts"""

import typer
from pathlib import Path

app = typer.Typer()


@app.command()
def code(image_path: Path):
    from commands.code_reader import read_code

    read_code(image_path)


if __name__ == "__main__":
    app()
