import os

from org.openpnp.util.UiUtils import submitUiMachineTask
from org.openpnp.util import Utils2D, MovableUtils

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane
from java.lang import ProcessBuilder
from java.io import IOException, File
import subprocess
import time

SCRIPTS_DIR = os.path.expanduser("~/.openpnp2/scripts")


def launch_secondary_script(filename, **kwargs):
    target_path = os.path.join(SCRIPTS_DIR, filename)

    script_globals = globals()
    for key, value in kwargs.iteritems():
        script_globals[key] = value

    execfile(target_path, script_globals, script_globals)

    return script_globals.get("scan_dir")


def run_command(dir, *command):
    try:
        pb = ProcessBuilder(list(command))
        pb.directory(dir)
        pb.inheritIO()

        process = pb.start()
        exit_code = process.waitFor()

        print("%s exited with: %d" % (command[0], exit_code))
        return exit_code

    except IOException as e:
        print("%s is not installed or not on PATH." % command[0])
        print(e)
        return -1


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


def handle_serial_number(board_location, prompt="Enter serial number:", title="Input"):
    state_dir = os.path.join(xdg_state_home(), "PnVision")
    state_file = os.path.join(state_dir, "serial_number")
    qr_image = os.path.join(state_dir, "qr_code.png")

    launch_secondary_script("capture_qr_code.py", board_location=board_location, qr_image=qr_image)

    result = run_command(File(state_dir), "pnvision", "code", qr_image)

    if result:
        code = result.strip().replace(" ", "_")
        if code:
            write_file(state_file, code)
            return
    print(result)
    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park is not None:
        head.getDefaultCamera().moveTo(park)

    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    if value is None:
        SN = "-"
    else:
        value = value.strip().replace(" ", "_")
        SN = value if value else "-"

    write_file(state_file, SN)


def get_user_input(board_location):
    config_file = os.path.join(xdg_config_home(), "PnVision", "location")

    handle_serial_number(board_location)

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


def get_current_job():
    try:
        if job is not None:
            return job
    except NameError:
        pass

    try:
        if gui is not None:
            tab = gui.getJobTab()
            if tab is not None:
                return tab.getJob()
    except NameError:
        pass

    raise Exception("Active OpenPnP job not detected. Load a job prior to execution.")


def finish_task():
    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park is not None:
        head.getDefaultCamera().moveTo(park)

    from javax.swing import SwingUtilities

    SwingUtilities.invokeLater(
        lambda: JOptionPane.showMessageDialog(
            None, "Job finished successfully", "OpenPnP", JOptionPane.INFORMATION_MESSAGE
        )
    )

    for _ in range(3):
        subprocess.Popen(["canberra-gtk-play", "-i", "complete"])
        time.sleep(0.5)


def main():
    job_obj = get_current_job()
    board_locations = job_obj.getBoardLocations()

    for board_index in range(board_locations.size()):
        board_location = board_locations.get(board_index)
        global initial_report_data

        SN, location = get_user_input(board_location)
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

        submitUiMachineTask(lambda: finish_task())


main()
