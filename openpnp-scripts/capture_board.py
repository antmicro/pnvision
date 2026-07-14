from __future__ import absolute_import, division

import re

from java.io import File, PrintWriter
from java.lang import System, Thread
from java.text import SimpleDateFormat
from java.util import Date
from java.lang import ProcessBuilder
from javax.imageio import ImageIO

from org.openpnp.model import LengthUnit, Location
from org.openpnp.util import Utils2D, MovableUtils
from org.openpnp.util.UiUtils import submitUiMachineTask

capture_board_scan_dir = None

# ---------------- USER SETTINGS ----------------

# Calibrate before use
CAMERA_FOV_X_MM = 16
CAMERA_FOV_Y_MM = 9.0

# Overlap between neighboring images.
OVERLAP = -2.0

# Optional margin from board edges.
EDGE_MARGIN_X_MM = 0.0
EDGE_MARGIN_Y_MM = 0.0

# Extra delay after motion before capture.
EXTRA_SETTLE_MS = 300

# False = camera.settleAndCapture()
# True  = camera.captureRaw()
USE_CAPTURE_RAW = False

if "OUT_FOLDER" not in globals():
    OUT_FOLDER = System.getProperty("user.home") + "/.openpnp/vision/log/"

# Reduces long travel
SERPENTINE = False

# ------------------------------------------------


def main():
    submitUiMachineTask(scan_board_tiles)


def scan_board_tiles():
    camera = machine.getDefaultHead().getDefaultCamera()
    job_obj = get_current_job()

    fov_x, fov_y = get_camera_fov_mm(camera)
    step_x = fov_x * (1.0 - OVERLAP)
    step_y = fov_y * (1.0 - OVERLAP)

    print("Camera FOV: %.3f x %.3f mm" % (fov_x, fov_y))
    print("Tile step: %.3f x %.3f mm" % (step_x, step_y))

    board_locations = job_obj.getBoardLocations()

    for board_index in range(board_locations.size()):
        board_location = board_locations.get(board_index)

        if not is_board_location_enabled(board_location):
            print("Skipping disabled board location %d" % board_index)
            continue

        capture_board_scan_dir = make_scan_directory(board_location)
        print("Output: %s" % capture_board_scan_dir.getAbsolutePath())

        scan_board_location(
            camera,
            board_location,
            board_index,
            fov_x,
            fov_y,
            step_x,
            step_y,
            capture_board_scan_dir,
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
    board_index,
    fov_x,
    fov_y,
    step_x,
    step_y,
    capture_board_scan_dir,
):

    board = board_location.getBoard()
    board_name = board.getName()
    safe_board_name = sanitize(board_name)

    dimensions = board.getDimensions().convertToUnits(LengthUnit.Millimeters)
    width = dimensions.getX()
    height = dimensions.getY()

    print("Scanning board %d: %s" % (board_index, board_name))
    print("Board dimensions: %.3f x %.3f mm" % (width, height))

    xs = make_axis_centers(width, fov_x, step_x, EDGE_MARGIN_X_MM)
    ys = make_axis_centers(height, fov_y, step_y, EDGE_MARGIN_Y_MM)

    print("Grid: %d columns x %d rows = %d images" % (len(xs), len(ys), len(xs) * len(ys)))

    for row in range(len(ys)):
        y = ys[row]

        for col0 in range(len(xs)):
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

            image_file_name = "board%s_%s_r%s_c%s_x%s_y%s.png" % (
                pad(board_index, 2),
                safe_board_name,
                pad(row, 3),
                pad(col, 3),
                fmt(x),
                fmt(y),
            )

            file_obj = File(capture_board_scan_dir, image_file_name)
            ImageIO.write(image, "PNG", file_obj)

            print("Saved %s" % image_file_name)


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
    except:
        return True


def make_scan_directory(board_location):
    global time_str
    board = board_location.getBoard()
    board_name = board.getName()
    safe_board_name = sanitize(board_name)

    root = File(OUT_FOLDER, safe_board_name)
    if not root.exists():
        root.mkdirs()

    if "time_str" not in globals():
        time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    parts = []

    if "unit" in globals() and unit and unit != "N/A":
        parts.append(unit)

    parts.append(time_str)

    if "location" in globals() and location and location != "N/A":
        parts.append(location)

    dir_name = "_".join(parts)

    scan_dir = File(File(root, dir_name), "board")
    if not scan_dir.exists():
        scan_dir.mkdirs()

    return scan_dir


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
