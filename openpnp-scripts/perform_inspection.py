import os

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane
from java.lang import ProcessBuilder
from java.io import IOException

SCRIPTS_DIR = os.path.expanduser("~/.openpnp2/scripts")

def launch_secondary_script(filename, inital_report_data):
    target_path = os.path.join(SCRIPTS_DIR, filename)

    script_globals = globals()
    execfile(target_path, script_globals, script_globals)

    return script_globals.get("scan_dir")


# def run_command(dir, *command):
#     try:
#         pb = ProcessBuilder(list(command))
#         pb.directory(dir)
#         pb.inheritIO()

#         process = pb.start()
#         exit_code = process.waitFor()

#         print("%s exited with: %d" % (command[0], exit_code))
#         return exit_code

#     except IOException as e:
#         print("%s is not installed or not on PATH." % command[0])
#         print(e)
#         return -1


def get_user_input(prompt="Enter serial number:", title="Input"):
    # Serial number
    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    if value is None:
        value = "-"

    value = value.strip().replace(" ", "_")

    if value == "":
        SN = "-"
    else:
        SN = value

    # Assembly place / Assembly machine
    options = ["POZ", "WRO", "GDA", "GOT"]

    location = JOptionPane.showInputDialog(
        None, "Select location:", "Location", JOptionPane.QUESTION_MESSAGE, None, options, options[0]
    )

    if location is None:
        location = "-"

    return SN, location


def main():
    global inital_report_data

    SN, location = get_user_input()
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())
    inital_report_data = {
        "metadata": {
            "time_stamp": time_str,
            "sn": SN,  # serial number will be read from qr or bar code (code_reader.py)
            "project_reference": "",  # this will be taken from CI
            "commit_sha": "",  # this will be taken from CI
            "location": location,
        },
        "parts": [],
        "logs": [],
    }

    launch_secondary_script("capture_board.py", inital_report_data)
    #run_command(capture_board_scan_dir, "pnvision", "stitch", ".")

    launch_secondary_script("capture_components.py", inital_report_data)


main()
