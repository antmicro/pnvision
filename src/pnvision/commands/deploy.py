import os
from pathlib import Path
from zipfile import ZipFile
import shutil


def get_state_home() -> Path:
    if "XDG_STATE_HOME" in os.environ:
        return Path(os.environ["XDG_STATE_HOME"]) / "pnvision"

    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "pnvision"

    return Path.home() / ".local" / "state" / "pnvision"


def copy_files_from_zip(artifacts_directory: Path, state_directory: Path) -> None:
    with ZipFile(artifacts_directory) as zip_file:
        files = [Path(name) for name in zip_file.namelist()]

        bom_file = next(
            (file for file in files if file.name.endswith("-BOM-ALL-ReferenceNotGrouped.csv")),
            None,
        )

        bottom_pos_file = next(
            (
                file
                for file in files
                if file.name.startswith("visual-inspection-") and file.name.endswith("-bottom.pos")
            ),
            None,
        )

        top_pos_file = next(
            (file for file in files if file.name.startswith("visual-inspection-") and file.name.endswith("-top.pos")),
            None,
        )

        if bom_file is None:
            raise FileNotFoundError("Could not find *-BOM-ALL-ReferenceNotGrouped.csv")

        if bottom_pos_file is None:
            raise FileNotFoundError("Could not find visual-inspection-*-bottom.pos")

        if top_pos_file is None:
            raise FileNotFoundError("Could not find visual-inspection-*-top.pos")

        state_directory.mkdir(parents=True, exist_ok=True)

        for source in (bom_file, bottom_pos_file, top_pos_file):
            with zip_file.open(source.as_posix()) as source_file:
                with (state_directory / source.name).open("wb") as destination:
                    shutil.copyfileobj(source_file, destination)


def deploy(artifacts_directory: Path) -> None:

    state_directory = get_state_home()
    if state_directory.exists():
        shutil.rmtree(state_directory)

    copy_files_from_zip(artifacts_directory, state_directory)
