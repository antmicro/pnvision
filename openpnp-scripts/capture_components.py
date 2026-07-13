from __future__ import absolute_import, division

import re

from java.io import File, PrintWriter
from java.lang import System, Thread
from java.text import SimpleDateFormat
from java.util import Date
from javax.imageio import ImageIO

from org.openpnp.model import LengthUnit, Location
from org.openpnp.util import Utils2D, MovableUtils
from org.openpnp.util.UiUtils import submitUiMachineTask

from javax.swing import JOptionPane

capture_components_scan_dir = None

# ---------------- USER SETTINGS ----------------

# Delay initialized after motion before image capture is executed.
EXTRA_SETTLE_MS = 300

# False = camera.settleAndCapture()
# True  = camera.captureRaw()
USE_CAPTURE_RAW = False

# Crop passive component images
CROP_IMAGES = True

# Base directory for the output images.
if "OUT_FOLDER" not in globals():
    OUT_FOLDER = System.getProperty("user.home") + "/.openpnp/vision/log/"

# ------------------------------------------------


def main():
    submitUiMachineTask(scan_components)


def scan_components():
    manifest = None

    try:
        camera = machine.getDefaultHead().getDefaultCamera()
        job_obj = get_current_job()

        board_locations = job_obj.getBoardLocations()

        for board_index in range(board_locations.size()):
            board_location = board_locations.get(board_index)

            if not is_board_location_enabled(board_location):
                print("Skipping disabled board location %d" % board_index)
                continue

            capture_components_scan_dir = make_scan_directory(board_location)
            print("Output: %s" % capture_components_scan_dir.getAbsolutePath())

            manifest = PrintWriter(File(capture_components_scan_dir, "manifest.csv"))
            manifest.println(
                "file,board_index,board_name,placement_id,part_name,local_x_mm,local_y_mm,"
                "machine_x_mm,machine_y_mm,machine_z_mm,rotation_deg"
            )
            print("Output directory generated: %s" % capture_components_scan_dir.getAbsolutePath())

            process_board_placements(
                camera,
                board_location,
                board_index,
                capture_components_scan_dir,
                manifest,
            )

        print("Component image capture sequence complete.")

    finally:
        if manifest is not None:
            manifest.close()


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


def process_board_placements(
    camera,
    board_location,
    board_index,
    capture_components_scan_dir,
    manifest,
):
    board = board_location.getBoard()
    board_name = board.getName()
    safe_board_name = sanitize(board_name)

    placements = board.getPlacements()
    total_placements = placements.size()

    print("Scanning board %d (%s) - Placements detected: %d" % (board_index, board_name, total_placements))

    for placement_index in range(total_placements):
        placement = placements.get(placement_index)

        placement_id = placement.getId()

        if placement.getPart() is None:
            print("Skipping %s: no part assigned." % placement_id)
            continue

        part_name = placement.getPart().getId()

        # Skip parts by ID
        if (
            placement_id.startswith("MP")
            or placement_id.startswith("TP")
            or placement_id.startswith("FD")
            or placement_id.startswith("REF**")
        ):
            print("Skipping %s (%s)" % (placement_id, part_name))
            continue

        safe_part_name = sanitize(part_name)
        safe_placement_id = sanitize(placement_id)

        board_local_location = placement.getLocation()

        machine_location = Utils2D.calculateBoardPlacementLocation(board_location, board_local_location).convertToUnits(
            LengthUnit.Millimeters
        )

        MovableUtils.moveToLocationAtSafeZ(camera, machine_location)

        if EXTRA_SETTLE_MS > 0:
            Thread.sleep(EXTRA_SETTLE_MS)

        if USE_CAPTURE_RAW:
            image = camera.captureRaw()
        else:
            image = camera.settleAndCapture()

        if CROP_IMAGES:
            rotation = machine_location.getRotation()
            image = crop_small_passives(image, safe_part_name, rotation)

        file_name = "b%s_%s_%s_%s.png" % (
            safe_board_name,
            pad(board_index, 2),
            safe_placement_id,
            safe_part_name,
        )

        file_obj = File(capture_components_scan_dir, file_name)
        ImageIO.write(image, "PNG", file_obj)

        manifest.println(
            ",".join(
                [
                    csv(file_name),
                    str(board_index),
                    csv(board_name),
                    csv(placement_id),
                    csv(part_name),
                    fmt(board_local_location.getX()),
                    fmt(board_local_location.getY()),
                    fmt(machine_location.getX()),
                    fmt(machine_location.getY()),
                    fmt(machine_location.getZ()),
                    fmt(machine_location.getRotation()),
                ]
            )
        )

        print("Captured %s (%d/%d)" % (placement_id, placement_index + 1, total_placements))


def crop_small_passives(image, safe_part_name, rotation_deg):
    if "0201" in safe_part_name:
        scale = 0.11
    elif "0402" in safe_part_name:
        scale = 0.11
    elif "0603" in safe_part_name:
        scale = 0.16
    elif "0805" in safe_part_name:
        scale = 0.22
    else:
        return image

    w = image.getWidth()
    h = image.getHeight()

    r = abs(rotation_deg) % 360
    rotated = (45 < r < 135) or (225 < r < 315)

    if rotated:
        # portrait (9:16)
        target_w = int(h * scale)
        target_h = int(target_w * (16.0 / 9.0))
    else:
        # landscape (16:9)
        target_h = int(h * scale)
        target_w = int(target_h * (16.0 / 9.0))

    target_w = max(1, min(target_w, w))
    target_h = max(1, min(target_h, h))

    if target_w >= w or target_h >= h:
        return image

    x = (w - target_w) // 2
    y = (h - target_h) // 2

    return image.getSubimage(x, y, target_w, target_h)


def is_board_location_enabled(board_location):
    try:
        return board_location.isEnabled()
    except:
        return True


def make_scan_directory(board_location):
    board = board_location.getBoard()
    board_name = board.getName()
    safe_board_name = sanitize(board_name)

    root = File(OUT_FOLDER, safe_board_name)
    if not root.exists():
        root.mkdirs()

    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    parts = []

    if "unit" in globals() and unit and unit != "N/A":
        parts.append(unit)

    parts.append(time_str)

    if "location" in globals() and location and location != "N/A":
        parts.append(location)

    dir_name = "_".join(parts)

    scan_dir = File(File(root, dir_name), "components")
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
