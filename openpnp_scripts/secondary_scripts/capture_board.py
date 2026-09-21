"""Moves the camera head to capture images of the whole board.

Moves the camera over a set distance and saves the captured images
in the board/ directory with stamped filenames.
"""

from __future__ import absolute_import, division
import json
import os
import sys

from java.io import File
from java.lang import Thread
from javax.imageio import ImageIO
from javax.swing import ProgressMonitor

from org.openpnp.model import LengthUnit, Location
from org.openpnp.util import Utils2D, MovableUtils

scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from utils import make_scan_directory

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

# Reduces long travel
SERPENTINE = False

# ------------------------------------------------


def capture_board(machine, board_location, initial_report_data):

    camera = machine.defaultHead.defaultCamera
    fov_x, fov_y = get_camera_fov_mm(camera)
    step_x = fov_x * (1.0 - OVERLAP)
    step_y = fov_y * (1.0 - OVERLAP)

    print("Camera FOV: %.3f x %.3f mm" % (fov_x, fov_y))
    print("Tile step: %.3f x %.3f mm" % (step_x, step_y))

    safe_board_name, scan_dir = make_scan_directory(board_location, initial_report_data, "board")
    print("Output: %s" % scan_dir.getAbsolutePath())

    report_file = File(scan_dir.getParentFile(), "report.json")
    if not report_file.exists():
        with open(report_file.getAbsolutePath(), "w") as f:
            json.dump(initial_report_data, f, indent=4)

    scanned = scan_board_location(
        camera,
        board_location,
        fov_x,
        fov_y,
        step_x,
        step_y,
        safe_board_name,
        scan_dir,
        initial_report_data,
    )

    if scanned:
        print("Board tile scan complete.")

    return scanned, scan_dir


def scan_board_location(
    camera,
    board_location,
    fov_x,
    fov_y,
    step_x,
    step_y,
    safe_board_name,
    scan_dir,
    initial_report_data,
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

    pcbdata = initial_report_data.get("pcb", {})
    serial_number = pcbdata.get("serial_number")

    monitor = ProgressMonitor(
        None,
        "Board SN: %s\nScanning board..." % serial_number,
        "",
        0,
        len(xs) * len(ys),
    )

    try:
        for row in range(len(ys)):
            y = ys[row]

            for col0 in range(len(xs)):
                if monitor.isCanceled():
                    raise Exception("User cancelled scan")

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

                global_x = machine_location.getX()
                global_y = machine_location.getY()

                monitor.setProgress(row * len(xs) + col0)
                monitor.setNote("Scanning row: %d, col: %d | global X: %.3f, Y: %.3f" % (row, col, global_x, global_y))

                if EXTRA_SETTLE_MS > 0:
                    Thread.sleep(EXTRA_SETTLE_MS)

                if USE_CAPTURE_RAW:
                    image = camera.captureRaw()
                else:
                    image = camera.settleAndCapture()

                if serial_number is not None:
                    image_file_name = "%s_r%s_c%s_x%s_y%s.png" % (
                        serial_number,
                        pad(row, 3),
                        pad(col, 3),
                        fmt(global_x),
                        fmt(global_y),
                    )
                else:
                    image_file_name = "r%s_c%s_x%s_y%s.png" % (
                        pad(row, 3),
                        pad(col, 3),
                        fmt(global_x),
                        fmt(global_y),
                    )

                file_obj = File(scan_dir, image_file_name)
                ImageIO.write(image, "PNG", file_obj)

                print("Saved %s" % image_file_name)

    finally:
        monitor.close()

    return len(xs) * len(ys) > 0


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


def pad(value, width):
    s = str(value)
    while len(s) < width:
        s = "0" + s
    return s


def fmt(value):
    return "%.3f" % float(value)
