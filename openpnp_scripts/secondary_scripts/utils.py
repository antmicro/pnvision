"""Shared functions between scripts."""

import os
import re

from java.lang import System
from java.text import SimpleDateFormat
from java.util import Date
from java.io import File


def config_home():
    """Returns config home file."""

    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")), "pnvision"
        )

    return os.path.join(
        os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming")), "pnvision"
    )


def state_home():
    """Returns state home file."""

    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


def data_home():
    """Returns data home file, scans are stored by default here."""

    config_file = os.path.join(config_home(), "scan_directory")
    scan_directory = read_file(config_file)

    if scan_directory:
        return scan_directory

    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


def read_file(path):
    """Reads a file if exists."""

    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read().strip()


def sanitize(value):
    """Replaces slashes, special characters, and whitespace with underscores."""

    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(value))


def get_safe_board_name(board_location):
    """Return sanitized board name without .board.xml."""

    board = board_location.getBoard()
    board_name = board.getName()
    if board_name.endswith(".board.xml"):
        board_name = board_name[: -len(".board.xml")]

    safe_board_name = sanitize(board_name)

    return safe_board_name


def make_scan_directory(board_location, initial_report_data, directory_name):
    """Generates directory where scan is stored."""

    root = data_home()
    if not os.path.exists(root):
        os.makedirs(root)

    serial_number = ""
    board_side = str(board_location.getSide()).lower()
    location = ""
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    scandata = initial_report_data.get("scan", {})
    pcbdata = initial_report_data.get("pcb", {})
    serial_number = pcbdata.get("serial_number", "")
    location = scandata.get("location", "")
    time_str = scandata.get("timestamp", "")

    parts = [serial_number, board_side, time_str, location]

    dir_name = "_".join(part for part in parts if part and part != "-")

    scan_dir = File(File(root, dir_name), directory_name)
    if not scan_dir.exists():
        scan_dir.mkdirs()

    return scan_dir
