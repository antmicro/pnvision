from __future__ import absolute_import, division
import re
import json

from java.io import File
from java.lang import System, Thread
from java.text import SimpleDateFormat
from java.util import Date
from javax.imageio import ImageIO
from javax.swing import ProgressMonitor

from org.openpnp.model import LengthUnit, Location
from org.openpnp.util import Utils2D, MovableUtils

# ---------------- USER SETTINGS ----------------

# Calibrate before use
CAMERA_FOV_X_MM = 16
CAMERA_FOV_Y_MM = 9.0

# Overlap between neighboring images.
OVERLAP = 0.6

# Optional margin from board edges.
EDGE_MARGIN_X_MM = 0.0
EDGE_MARGIN_Y_MM = 0.0

# Extra delay after motion before capture.
EXTRA_SETTLE_MS = 300

# False = camera.settleAndCapture()
# True  = camera.captureRaw()
USE_CAPTURE_RAW = False

if "OUT_FOLDER" not in globals():
    OUT_FOLDER = System.getProperty("user.home") + "/.openpnp2/vision/log/"

# Reduces long travel
SERPENTINE = False

# ------------------------------------------------


def main():
    global scan_dir
    global board_location

    camera = machine.defaultHead.defaultCamera
    job_obj = get_current_job()

    fov_x, fov_y = get_camera_fov_mm(camera)
    step_x = fov_x * (1.0 - OVERLAP)
    step_y = fov_y * (1.0 - OVERLAP)

    print("Camera FOV: %.3f x %.3f mm" % (fov_x, fov_y))
    print("Tile step: %.3f x %.3f mm" % (step_x, step_y))

    safe_board_name, scan_dir = make_scan_directory(board_location)
    print("Output: %s" % scan_dir.getAbsolutePath())

    report_file = File(scan_dir.getParentFile(), "report.json")
    if not report_file.exists():
        initial_report = globals().get("initial_report_data", {})
        with open(report_file.getAbsolutePath(), "w") as f:
            json.dump(initial_report, f, indent=4)

    scan_board_location(
        camera,
        board_location,
        fov_x,
        fov_y,
        step_x,
        step_y,
        safe_board_name,
        scan_dir,
    )

    print("Board tile scan complete.")


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

    raise Exception("No job available. Load an active OpenPnP job first.")


def scan_board_location(
    camera,
    board_location,
    fov_x,
    fov_y,
    step_x,
    step_y,
    safe_board_name,
    scan_dir,
):

    board = board_location.getBoard()

    dimensions = board.getDimensions().convertToUnits(LengthUnit.Millimeters)
    width = dimensions.getX()
    height = dimensions.getY()

    print("Scanning board: %s" % safe_board_name)
    print("Board dimensions: %.3f x %.3f mm" % (width, height))

    xs = make_axis_centers(width, fov_x, step_x, EDGE_MARGIN_X_MM)
    ys = make_axis_centers(height, fov_y, step_y, EDGE_MARGIN_Y_MM)

    print("Grid: %d columns x %d rows = %d images" % (len(xs), len(ys), len(xs) * len(ys)))

    monitor = ProgressMonitor(None, "Scanning board...", "", 0, len(xs) * len(ys))

    try:
        for row in range(len(ys)):
            y = ys[row]

            for col0 in range(len(xs)):
                if monitor.isCanceled():
                    raise Exception("User cancelled scan")

                monitor.setProgress(row * len(xs) + col0)
                monitor.setNote("Scanning row: %d, col: %d" % (row, col0))

                if SERPENTINE and row % 2 == 1:
                    col = len(xs) - 1 - col0
                else:
                    col = col0

                x = xs[col]

                board_local_location = Location(LengthUnit.Millimeters, x, y, 0.0, 0.0)

                machine_location = Utils2D.calculateBoardPlacementLocation(
                    board_location, board_local_location
                ).convertToUnits(LengthUnit.Millimeters)

                MovableUtils.moveToLocationAtSafeZ(camera, machine_location)

                if EXTRA_SETTLE_MS > 0:
                    Thread.sleep(EXTRA_SETTLE_MS)

                if USE_CAPTURE_RAW:
                    image = camera.captureRaw()
                else:
                    image = camera.settleAndCapture()

                board_id = (
                    initial_report_data.get("metadata", {}).get("sn", safe_board_name)
                    if "initial_report_data" in globals()
                    else safe_board_name
                )
                image_file_name = "%s_r%s_c%s_x%s_y%s.png" % (
                    board_id,
                    pad(row, 3),
                    pad(col, 3),
                    fmt(x),
                    fmt(y),
                )

                file_obj = File(scan_dir, image_file_name)
                ImageIO.write(image, "PNG", file_obj)

                print("Saved %s" % image_file_name)

    finally:
        monitor.close()


def get_camera_fov_mm(camera):
    fov_x = CAMERA_FOV_X_MM
    fov_y = CAMERA_FOV_Y_MM

    if fov_x is None or fov_y is None:
        upp = camera.getUnitsPerPixelAtZ().convertToUnits(LengthUnit.Millimeters)

        if fov_x is None:
            fov_x = abs(camera.getWidth() * upp.getX())

        if fov_y is None:
            fov_y = abs(camera.getHeight() * upp.getY())

    if fov_x <= 0 or fov_y <= 0:
        raise Exception("Camera FOV could not be determined. " "Set CAMERA_FOV_X_MM and CAMERA_FOV_Y_MM manually.")

    return fov_x, fov_y


def make_axis_centers(size, fov, step, margin):
    pts = []

    if size <= 0:
        return pts

    start = margin  # + fov / 2.0
    end = size - margin  # - fov / 2.0

    # Board smaller than one camera frame.
    if end <= start:
        pts.append(size / 2.0)
        return pts

    p = start

    while p <= end + 0.001:
        pts.append(p)
        p += step

    # Force final tile near far edge.
    if len(pts) == 0 or abs(pts[-1] - end) > 0.001:
        pts.append(end)

    return pts


def is_board_location_enabled(board_location):
    try:
        return board_location.isEnabled()
    except Exception:
        return True


def make_scan_directory(board_location):
    board = board_location.getBoard()
    board_name = board.getName()
    if board_name.endswith(".board.xml"):
        board_name = board_name[: -len(".board.xml")]
    safe_board_name = sanitize(board_name)

    root = File(OUT_FOLDER, safe_board_name)
    if not root.exists():
        root.mkdirs()

    sn = ""
    board_side = str(board_location.getSide()).lower()
    location = ""
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    if "initial_report_data" in globals():
        metadata = initial_report_data.get("metadata", {})
        sn = metadata.get("sn")
        location = metadata.get("location")
        time_str = metadata.get("time_stamp")

    parts = [sn, board_side, time_str, location]

    dir_name = "_".join(part for part in parts if part and part != "-")

    scan_dir = File(File(root, dir_name), "board")
    if not scan_dir.exists():
        scan_dir.mkdirs()

    return safe_board_name, scan_dir


def sanitize(value):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(value))


def pad(value, width):
    s = str(value)
    while len(s) < width:
        s = "0" + s
    return s


def fmt(value):
    return "%.3f" % float(value)


def csv(value):
    s = str(value)

    if "," in s or '"' in s or "\n" in s:
        return '"' + s.replace('"', '""') + '"'

    return s


main()
