import os
import subprocess
from time import sleep
import getpass
import sys

from org.openpnp.util.UiUtils import submitUiMachineTask
import org.openpnp.Main as Main

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane, SwingUtilities
from java.lang import ProcessBuilder, System
from java.io import IOException, BufferedReader, InputStreamReader, File
from java.lang import Exception as JavaException

SCRIPTS_DIR = os.path.expanduser("~/.openpnp2/scripts/secondary_scripts")


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
        if dir is not None:
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
        f.write("null" if value is None else value)


def handle_user_comment():
    user_comment = JOptionPane.showInputDialog(
        None,
        "Enter comment:",
        "User Comment",
        JOptionPane.QUESTION_MESSAGE,
    )

    return user_comment if user_comment else None


def handle_serial_number(board_location, prompt="Enter serial number:", title="Input"):
    state_dir = state_home()
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
        SN = None
    else:
        value = value.strip().replace(" ", "_")
        SN = value if value else None

    write_file(state_file, SN)
    return SN


def handle_location():
    config_file = os.path.join(config_home(), "location")
    location = read_file(config_file)

    if location:
        return location

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

    write_file(config_file, location)
    return location


def get_os_name():
    if os.path.exists("/etc/os-release"):
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.strip().split("=", 1)[1].strip('"')
    return ""


def get_metadata(board_location, board_index):

    user_comment = handle_user_comment()

    user = getpass.getuser()

    board_side = str(board_location.getSide()).lower()

    sn = handle_serial_number(board_location)

    location = handle_location()

    openpnp_version = str(Main.getVersion())

    python_version = "{}.{}.{}".format(*sys.version_info[:3])

    os_name = get_os_name()
    kernel_version = subprocess.check_output(["uname", "-r"]).strip()

    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    scripts_version = run_command(None, "pnvision", "version")

    initial_report_data = {
        "metadata": {
            "timestamp": time_str,
            "board_index": board_index,
            "sn": sn,
            "side": board_side,
            "user": user,
            "openpnp_version": openpnp_version,
            "python_version": python_version,
            "user_comment": user_comment,
            "project_reference": "",
            "commit_sha": "",
            "location": location,
            "host": {"os_name": os_name, "kernel_version": kernel_version},
            "scripts_version": scripts_version,
        },
        "parts": [],
        "logs": [],
    }

    return initial_report_data


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


def is_board_disabled(board_location, board_index):
    try:
        if not board_location.isEnabled():
            print("Skipping disabled board with index %d" % board_index)
            return True
    except Exception:
        return False

    return False


def calibrate_pnp():
    locator = machine.getFiducialLocator()

    try:
        locator.locatePlacementsHolder(board_location)

    except JavaException as e:
        print("Fiducial location failed, continuing without correction:", e)


def capture_board():
    capture_board_scan_dir = launch_secondary_script("capture_board.py")
    run_command(capture_board_scan_dir, "pnvision", "stitch", ".")


def capture_components():
    launch_secondary_script("capture_components.py")


def finish_job():
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

        if is_board_disabled(board_location, board_index):
            continue

        calibrate_pnp()

        initial_report_data = get_metadata(board_location, board_index)

        sleep(2.0)

        capture_board()

        capture_components()

        finish_job()


def main():
    submitUiMachineTask(perform_inspection)


main()
