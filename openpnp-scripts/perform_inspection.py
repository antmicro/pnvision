from datetime import datetime
from time import sleep
import os

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane

import json

metadata = {
    "metadata": {
        "time_stamp": time_str,
        "unit": unit,  # code_reader.py can read unit from qr codes, not implemented
        "project_reference": "BMC Breakout Board",  # this will be taken from CI
        "commit_sha": "a1b2c3d4",  # this will be taken from CI
        "location": location,
    }
}

unit = "NA"
location = "NA"

SCRIPTS_DIR = "/home/pnp/.openpnp2/scripts"


def launch_secondary_script(filename):
    target_path = os.path.join(SCRIPTS_DIR, filename)
    execfile(target_path, globals(), globals())


result = {
    "capture_board": {
        "status": None,
        "timestamp": None,
        "log": None,
        "scan_dir": None,
    },
    "capture_components": {
        "status": None,
        "timestamp": None,
        "log": None,
    },
}


def get_user_input(prompt="Enter unit number:", title="Input"):
    # Unit number
    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    if value is None:
        value = "NA"

    value = value.strip()

    if value == "":
        unit = "NA"
    else:
        unit = value

    # Assembly place
    options = ["POZ", "WRO", "GDA", "GOT"]

    location = JOptionPane.showInputDialog(
        None, "Select location:", "Location", JOptionPane.QUESTION_MESSAGE, None, options, options[0]
    )

    if location is None:
        location = "NA"

    return unit, location


def capture_board_task():
    try:
        launch_secondary_script("capture_board.py")

        result["capture_board"]["status"] = "SUCCESS"
        result["capture_board"]["timestamp"] = datetime.now().isoformat()
        result["capture_board"]["log"] = "Board capture completed"
        result["capture_board"]["scan_dir"] = capture_board_scan_dir

    except Exception as e:
        result["capture_board"]["status"] = "FAILED"
        result["capture_board"]["timestamp"] = datetime.now().isoformat()
        result["capture_board"]["log"] = str(e)


def capture_components_task():
    try:
        launch_secondary_script("capture_components.py")

        result["capture_components"]["status"] = "SUCCESS"
        result["capture_components"]["timestamp"] = datetime.now().isoformat()
        result["capture_components"]["log"] = "Component capture completed"
        result["capture_components"]["scan_dir"] = capture_components_scan_dir

    except Exception as e:
        result["capture_components"]["status"] = "FAILED"
        result["capture_components"]["timestamp"] = datetime.now().isoformat()
        result["capture_components"]["log"] = str(e)


def main():
    global unit, location, time_str
    unit, location = get_user_input()
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    with open("config.json", "w") as f:
        json.dump(metadata, f, indent=4)

    capture_board_task()

    if result["capture_board"]["status"] != "SUCCESS":
        raise Exception("Board Capture Error: " + result["capture_board"]["log"])

    result_scan_dir = result["capture_board"]["scan_dir"]
    # stitch_script = machine.getScripting().getScript("pnvision/stitch_board.py")
    # stitch_script.execute(result_scan_dir.getAbsolutePath())

    capture_components_task()

    if result["capture_components"]["status"] != "SUCCESS":
        raise Exception("Component Capture Error: " + result["capture_components"]["log"])


main()
