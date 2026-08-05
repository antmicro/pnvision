import os
import subprocess
from time import sleep

from org.openpnp.util.UiUtils import submitUiMachineTask

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane, SwingUtilities
from java.lang import ProcessBuilder
from java.io import IOException, BufferedReader, InputStreamReader, File
from java.lang import Exception as JavaException

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

        process = pb.start()

        output = []
        reader = BufferedReader(InputStreamReader(process.getInputStream()))

        line = reader.readLine()
        while line is not None:
            output.append(line)
            line = reader.readLine()

        exit_code = process.waitFor()

        result = "\n".join(output)

        print("%s exited with: %d" % (command[0], exit_code))
        return result

    except IOException as e:
        print("%s is not installed or not on PATH." % command[0])
        print(e)
        return None


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
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)

    launch_secondary_script("capture_qr_code.py", board_location=board_location, qr_image=qr_image)

    code = run_command(File(state_dir), "pnvision", "code", qr_image)

    if code:
        if code != "None":
            code = code.strip().replace(" ", "_")
            if code:
                write_file(state_file, code)
                return code

    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park is not None:
        head.getDefaultCamera().moveTo(park)

    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    file_qr_image = File(qr_image)
    if file_qr_image.exists():
        file_qr_image.delete()

    if value is None:
        # User pressed Cancel or closed the dialog
        raise Exception("User cancelled scan")

    if value == "":
        SN = "-"
    else:
        value = value.strip().replace(" ", "_")
        SN = value if value else "-"

    write_file(state_file, SN)
    return SN


def handle_location():
    config_file = os.path.join(xdg_config_home(), "PnVision", "location")
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
    return location


def get_user_input(board_location):

    SN = handle_serial_number(board_location)

    location = handle_location()

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


def is_board_location_enabled(board_location):
    try:
        return board_location.isEnabled()
    except Exception:
        return True


def calibrate_pnp():
    locator = machine.getFiducialLocator()

    try:
        locator.locatePlacementsHolder(board_location)

    except JavaException as e:
        print("Fiducial location failed, continuing without correction:", e)


def finishJob():
    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park is not None:
        head.getDefaultCamera().moveTo(park)

    for _ in range(4):
        subprocess.Popen(["canberra-gtk-play", "-i", "complete"])
        sleep(0.5)

    SwingUtilities.invokeLater(
        lambda: JOptionPane.showMessageDialog(
            None, "Job finished successfully", "OpenPnP", JOptionPane.INFORMATION_MESSAGE
        )
    )


def perform_inspection():
    job_obj = get_current_job()
    board_locations = job_obj.getBoardLocations()

    for board_index in range(board_locations.size()):
        global initial_report_data, board_location
        board_location = board_locations.get(board_index)

        if not is_board_location_enabled(board_location):
            print("Skipping disabled board location %d" % board_index)
            continue

        calibrate_pnp()

        SN, location = get_user_input(board_location)
        time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())
        initial_report_data = {
            "metadata": {
                "time_stamp": time_str,
                "board_index": board_index,
                "sn": SN,  # serial number will be read from qr or bar code (code_reader.py)
                "project_reference": "",  # this will be taken from CI
                "commit_sha": "",  # this will be taken from CI
                "location": location,
            },
            "parts": [],
            "logs": [],
        }
        sleep(1.5)

        capture_board_scan_dir = launch_secondary_script("capture_board.py")
        run_command(capture_board_scan_dir, "pnvision", "stitch", ".")

        launch_secondary_script("capture_components.py")

        finishJob()


def main():
    submitUiMachineTask(perform_inspection)


main()
