"""Shared functions between scripts."""

import os
import re

from java.lang import System
from java.text import SimpleDateFormat
from java.util import Date
from java.io import File


def config_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")), "pnvision"
        )

    return os.path.join(
        os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming")), "pnvision"
    )


def state_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


def data_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


def is_board_enabled(board_location):
    if board_location.isEnabled():
        return True

    return False


def sanitize(value):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(value))


def make_scan_directory(board_location, initial_report_data, directory_name):
    board = board_location.getBoard()
    board_name = board.getName()
    if board_name.endswith(".board.xml"):
        board_name = board_name[: -len(".board.xml")]
    safe_board_name = sanitize(board_name)

    root = File(data_home(), safe_board_name)
    if not root.exists():
        root.mkdirs()

    serial_number = ""
    board_side = str(board_location.getSide()).lower()
    location = ""
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    if initial_report_data:
        scandata = initial_report_data.get("scan", {})
        pcbdata = initial_report_data.get("pcb", {})
        serial_number = pcbdata.get("serial_number")
        location = scandata.get("location")
        time_str = scandata.get("time")
    else:
        serial_number = None
        location = board_location
        time_str = None

    parts = [serial_number, board_side, time_str, location]

    dir_name = "_".join(part for part in parts if part and part != "-")

    scan_dir = File(File(root, dir_name), directory_name)
    if not scan_dir.exists():
        scan_dir.mkdirs()

    return safe_board_name, scan_dir
