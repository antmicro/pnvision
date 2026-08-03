import os

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane
from java.lang import ProcessBuilder
from java.io import IOException

SCRIPTS_DIR = os.path.expanduser("~/.openpnp2/scripts")


def launch_secondary_script(filename):
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


def xdg_config_home():
    return os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))


def xdg_state_home():
    return os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state"))


def read_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read().strip()


def write_file(path, value):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, "w") as f:
        f.write(value)


def get_user_input(prompt="Enter serial number:", title="Input"):
    config_file = os.path.join(xdg_config_home(), "PnVision", "location")
    state_file = os.path.join(xdg_state_home(), "PnVision", "serial_number")

    # Serial number
    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    if value is None:
        SN = "-"
    else:
        value = value.strip().replace(" ", "_")
        SN = value if value else "-"

    write_file(state_file, SN)

    location = read_file(config_file)

    if not location:
        # Assembly place / Assembly machine
        options = ["POZ", "WRO", "GDA", "GOT"]

        location = JOptionPane.showInputDialog(
            None,
            "Select location:",
            "Location",
            JOptionPane.QUESTION_MESSAGE,
            None,
            options,
            options[0],
        )

        if location is None:
            location = "-"

        write_file(config_file, location)

    return SN, location


def finish_task():
    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park is not None:
        head.getDefaultNozzle().moveTo(park)

    from javax.swing import SwingUtilities

    SwingUtilities.invokeLater(
        lambda: JOptionPane.showMessageDialog(
            None, "Job finished successfully", "OpenPnP", JOptionPane.INFORMATION_MESSAGE
        )
    )


def main():
    global initial_report_data

    SN, location = get_user_input()
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())
    initial_report_data = {
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

    launch_secondary_script("capture_board.py")
    # run_command(capture_board_scan_dir, "pnvision", "stitch", ".")

    launch_secondary_script("capture_components.py")

    machine.submit(lambda: finish_task())


main()
