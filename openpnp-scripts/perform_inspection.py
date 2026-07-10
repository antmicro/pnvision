from datetime import datetime

import capture_board
import capture_components
import pnvision.stitch_board

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
        scan_dir = capture_board.main()

        result["capture_board"]["status"] = "SUCCESS"
        result["capture_board"]["timestamp"] = datetime.now().isoformat()
        result["capture_board"]["log"] = "Board capture completed"
        result["capture_board"]["scan_dir"] = scan_dir

    except Exception as e:
        result["capture_board"]["status"] = "FAILED"
        result["capture_board"]["timestamp"] = datetime.now().isoformat()
        result["capture_board"]["log"] = str(e)


def capture_components_task():
    try:
        capture_components.main()

        result["capture_components"]["status"] = "SUCCESS"
        result["capture_components"]["timestamp"] = datetime.now().isoformat()
        result["capture_components"]["log"] = "Component capture completed"

    except Exception as e:
        result["capture_components"]["status"] = "FAILED"
        result["capture_components"]["timestamp"] = datetime.now().isoformat()
        result["capture_components"]["log"] = str(e)


def main():

    submitUiMachineTask(capture_board_task)

    while result["capture_board"]["status"] is None:
        wait(100)

    if result["capture_board"]["status"] != "SUCCESS":
        raise Exception(result["capture_board"]["log"])

    pnvision.stitch_board.main(scan_dir.getAbsolutePath())

    submitUiMachineTask(capture_components_task)

    while result["capture_components"]["status"] is None:
        wait(100)

    if result["capture_components"]["status"] != "SUCCESS":
        raise Exception(result["capture_components"]["log"])

    process_results.main()


main()
