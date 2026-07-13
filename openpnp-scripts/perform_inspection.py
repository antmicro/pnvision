from datetime import datetime
from time import sleep
from org.openpnp.util.UiUtils import submitUiMachineTask
import os

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

    except Exception as e:
        result["capture_components"]["status"] = "FAILED"
        result["capture_components"]["timestamp"] = datetime.now().isoformat()
        result["capture_components"]["log"] = str(e)


def main():

    capture_board_task()

    while result["capture_board"]["status"] is None:
        sleep(1)

    if result["capture_board"]["status"] != "SUCCESS":
        raise Exception("Board Capture Error: " + result["capture_board"]["log"])

    result_scan_dir = result["capture_board"]["scan_dir"]

    # stitch_script = machine.getScripting().getScript("pnvision/stitch_board.py")
    # stitch_script.execute(result_scan_dir.getAbsolutePath())

    capture_components_task()

    while result["capture_components"]["status"] is None:
        sleep(1)

    if result["capture_components"]["status"] != "SUCCESS":
        raise Exception("Component Capture Error: " + result["capture_components"]["log"])


main()
