"""Runs an inspection procedure for an OpenPnP machine.

Asks for user input, captures component images, and saves
report.json and scan results.
"""

import os
import subprocess
from time import sleep
import getpass
import sys
import re
import shutil

from org.openpnp.util.UiUtils import submitUiMachineTask
import org.openpnp.Main as Main

from java.text import SimpleDateFormat
from java.util import Date
from javax.swing import JOptionPane, SwingUtilities, JFileChooser
from java.lang import ProcessBuilder
from java.io import IOException, BufferedReader, InputStreamReader, File
from java.lang import Exception as JavaException

scripts_dir = os.path.os.path.join(str(scripting.getScriptsDirectory()), "secondary_scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from utils import config_home, state_home, is_board_enabled, read_file, sanitize
from capture_qr_code import capture_qr_code
from capture_board import capture_board
from capture_components import capture_components

# Assembly place / Assembly machine
ALLOWED_LOCATIONS = ["POZ", "WRO", "GDA", "GOT"]


def run_command(command_dir, *command):
    """Runs a command and returns its standard output."""

    try:
        pb = ProcessBuilder(list(command))
        if command_dir:
            pb.directory(command_dir)

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
        print("%s is not installed or not on PATH." % command[0], e)

        return None


def write_file(path, value):
    """Writes a file, adds parent directories."""

    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, "w") as f:
        f.write("null" if value is None else value)


def handle_scan_directory():
    """Handles scan directory and saves to config."""

    config_file = os.path.join(config_home(), "scan_directory")
    scan_directory = read_file(config_file)

    if scan_directory:
        return scan_directory

    chooser = JFileChooser()
    chooser.setDialogTitle("Select scan directory:")
    chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)

    result = chooser.showOpenDialog(None)

    if result != JFileChooser.APPROVE_OPTION:
        return None

    scan_directory = chooser.getSelectedFile().getAbsolutePath()

    write_file(config_file, scan_directory)
    return scan_directory


def handle_user_comment():
    """Handles user input at the beginning of scan."""

    user_comment = JOptionPane.showInputDialog(
        None,
        "Enter comment:",
        "User Comment",
        JOptionPane.QUESTION_MESSAGE,
    )

    return user_comment if user_comment else None


def handle_serial_number(board_location, prompt="Enter serial number:", title="Input"):
    """Handles reading serial number from QR code or user input."""

    state_dir = state_home()
    state_file = os.path.join(state_dir, "serial_number")
    qr_image = os.path.join(state_dir, "qr_code.png")
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)

    capture_qr_code(machine, board_location, qr_image)

    code = run_command(File(state_dir), "pnvision", "code", qr_image)

    code = code.strip().replace(" ", "_") if code and code != "None" else None
    if code:
        write_file(state_file, code)
        return code

    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park:
        head.getDefaultCamera().moveTo(park)

    value = JOptionPane.showInputDialog(None, prompt, title, JOptionPane.QUESTION_MESSAGE)

    file_qr_image = File(qr_image)
    if file_qr_image.exists():
        file_qr_image.delete()

    if value is None:
        # User pressed Cancel or closed the dialog
        raise Exception("User cancelled scan")

    SN = None
    if value:
        SN = value.strip().replace(" ", "_")

    write_file(state_file, SN)
    return SN


def handle_location():
    """Handles reading location from config or user input."""

    config_file = os.path.join(config_home(), "location")
    location = read_file(config_file)

    if location:
        return location

    location = JOptionPane.showInputDialog(
        None,
        "Select location:",
        "Location",
        JOptionPane.QUESTION_MESSAGE,
        None,
        ALLOWED_LOCATIONS,
        ALLOWED_LOCATIONS[0],
    )

    write_file(config_file, location)
    return location


def handle_project_name(board_location):
    board = board_location.getBoard()
    board_name = board.getName()

    BOARD_NAME = re.compile(r"^(?P<project_reference>.+)-(?P<sha>[0-9a-fA-F]{7,40})-inspection\.board\.xml$")

    match = BOARD_NAME.match(board_name)

    if not match:
        return None, None

    return (str(match.group("project_reference")), str(match.group("sha")))


def get_bom_from_user():
    """Handles reading BOM from user input."""

    state_dir = str(state_home())
    if not os.path.isdir(state_dir):
        os.makedirs(state_dir)

    for filename in os.listdir(state_dir):
        if not filename.endswith("-BOM-ALL-ReferenceNotGrouped.csv"):
            continue

        bom_file_path = os.path.join(state_dir, filename)

        if not os.path.isfile(bom_file_path):
            continue

        result = JOptionPane.showConfirmDialog(
            None,
            "A previous BOM file was found:\n\n" + filename + "\n\n" + "Do you want to use it?",
            "Previous BOM",
            JOptionPane.YES_NO_OPTION,
            JOptionPane.QUESTION_MESSAGE,
        )

        if result == JOptionPane.YES_OPTION:
            return File(bom_file_path)

    chooser = JFileChooser()
    chooser.setDialogTitle("Select BOM-ALL-ReferenceNotGrouped CSV File")

    result = chooser.showOpenDialog(None)

    if result != JFileChooser.APPROVE_OPTION:
        return None

    file = chooser.getSelectedFile()
    return file


def save_bom_to_state(bom_path):
    """Saves bom to state home location."""

    state_dir = str(state_home())
    filename = os.path.basename(str(bom_path))

    saved_bom_file_path = os.path.join(state_dir, filename)
    source_path = str(bom_path.getAbsolutePath())

    if os.path.abspath(source_path) == os.path.abspath(saved_bom_file_path):
        return
    try:
        shutil.copy2(source_path, saved_bom_file_path)
    except (IOError, OSError):
        return


def handle_bom():
    """Handles reading BOM from user input."""

    bom_path = get_bom_from_user()

    if bom_path is None:
        return None

    save_bom_to_state(bom_path)

    return str(bom_path.getAbsolutePath())


def get_os_name():
    """Reads os name from os-release."""

    if not os.path.exists("/etc/os-release"):
        return ""

    with open("/etc/os-release", "r") as f:
        for line in f:
            if not line.startswith("PRETTY_NAME="):
                continue
            return line.strip().split("=", 1)[1].strip('"')

    return ""


def get_metadata(board_location, board_index):
    """Returns initial_report_data with all metadata."""

    handle_scan_directory()

    user_comment = handle_user_comment()

    user = getpass.getuser()

    board_side = str(board_location.getSide()).lower()

    sn = handle_serial_number(board_location)

    location = handle_location()

    project_reference, sha = handle_project_name()

    bom_file_path = handle_bom(board_location)

    openpnp_version = str(Main.getVersion())

    python_version = "{}.{}.{}".format(*sys.version_info[:3])

    os_name = get_os_name()
    kernel_version = subprocess.check_output(["uname", "-r"]).strip()

    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    scripts_version = run_command(None, "pnvision", "version")

    initial_report_data = {
        "tools": {
            "scripts_version": scripts_version,
            "python_version": python_version,
            "openpnp_version": openpnp_version,
            "host_pc": {"os_name": os_name, "kernel_version": kernel_version},
        },
        "scan": {
            "timestamp": time_str,
            "location": location,
            "side": board_side,
            "board_index": board_index,
            "statistics": {"populated_components": "", "dnp_components": ""},
            "user": user,
            "user_comment": user_comment,
        },
        "pcb": {
            "serial_number": sn,
            "project_reference": project_reference,
            "sha": sha,
        },
        "sourcing": {
            "bom_file": bom_file_path,
            "sourcing_file": "",
        },
        "parts": [],
    }

    return initial_report_data


def get_current_job():
    """Returns job object."""

    if globals().get("job"):
        return job

    gui_obj = globals().get("gui")
    if gui_obj:
        tab = gui_obj.getJobTab()
        if tab:
            return tab.getJob()

    raise Exception("Active OpenPnP job not detected. Load a job prior to execution.")


def calibrate_pnp(board_location):
    """Calibrates pnp based on fiducials."""

    locator = machine.getFiducialLocator()

    try:
        locator.locatePlacementsHolder(board_location)

    except JavaException as e:
        print("Fiducial location failed, continuing without correction:", e)


def finish_job():
    """Parks head and plays sound."""

    head = machine.getDefaultHead()
    park = head.getParkLocation()

    if park:
        head.getDefaultCamera().moveTo(park)

    sleep(1)

    for _ in range(4):
        subprocess.Popen(["canberra-gtk-play", "-i", "complete"])
        sleep(0.5)

    SwingUtilities.invokeLater(
        lambda: JOptionPane.showMessageDialog(
            None, "Job finished successfully", "OpenPnP", JOptionPane.INFORMATION_MESSAGE
        )
    )


def perform_inspection():
    """Runs an inspection procedure for an OpenPnP machine."""

    job_obj = get_current_job()
    board_locations = job_obj.getBoardLocations()

    for board_index in range(board_locations.size()):

        board_location = board_locations.get(board_index)

        if not is_board_enabled(board_location):
            print("Skipping disabled board with index %d" % board_index)
            continue

        initial_report_data = get_metadata(board_location, board_index)

        sleep(1.5)

        calibrate_pnp(board_location)

        board_scanned, capture_board_scan_dir = capture_board(machine, board_location, initial_report_data)
        if board_scanned:
            run_command(capture_board_scan_dir, "pnvision", "stitch", ".")

        capture_components(machine, board_location, initial_report_data)

        finish_job()


def main():
    """Submits perform_inspection as asynchronous task to the machine."""

    submitUiMachineTask(perform_inspection)


main()
