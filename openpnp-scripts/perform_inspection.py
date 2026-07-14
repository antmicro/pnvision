from datetime import datetime
from time import sleep
import os

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane

SCRIPTS_DIR = "/home/pnp/.openpnp2/scripts"


def launch_secondary_script(filename):
    target_path = os.path.join(SCRIPTS_DIR, filename)
    execfile(target_path, globals(), globals())


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

    # Assembly place / Assembly machine
    options = ["POZ", "WRO", "GDA", "GOT"]

    location = JOptionPane.showInputDialog(
        None, "Select location:", "Location", JOptionPane.QUESTION_MESSAGE, None, options, options[0]
    )

    if location is None:
        location = "NA"

    return unit, location


def main():
    global report_data, unit, location

    unit, location = get_user_input()
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())
    report_data = {
        "metadata": {
            "time_stamp": time_str,
            "unit": unit,  # unit will be read from qr or bar code (code_reader.py)
            "project_reference": "",  # this will be taken from CI
            "commit_sha": "",  # this will be taken from CI
            "location": location,
        },
        "parts": [],
        "logs": [],
    }

    launch_secondary_script("capture_board.py")

    # stitch_script = machine.getScripting().getScript("pnvision/stitch_board.py")
    # stitch_script.execute(result_scan_dir.getAbsolutePath())

    launch_secondary_script("capture_components.py")


main()
