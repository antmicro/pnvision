from __future__ import absolute_import, division
import re
import json

from java.io import File
from java.lang import System, Thread
from java.text import SimpleDateFormat
from java.util import Date, ArrayList
from javax.imageio import ImageIO
from javax.swing import ProgressMonitor
from java.lang import Thread

from org.openpnp.model import LengthUnit
from org.openpnp.util import Utils2D, MovableUtils
from org.openpnp.util.UiUtils import submitUiMachineTask

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
    OUT_FOLDER = System.getProperty("user.home") + "/.openpnp2/vision/log/"

# Component image cropping variables
ANGLE_DEVIATION = 5.0
CROP_MARGIN_SCALE = 1.1

# ------------------------------------------------


def main():
    submitUiMachineTask(scan_components)


def scan_components():
    Thread.sleep(1500)
    global scan_dir
    global report_file

    camera = machine.getDefaultHead().getDefaultCamera()
    job_obj = get_current_job()

    board_locations = job_obj.getBoardLocations()

    for board_index in range(board_locations.size()):
        board_location = board_locations.get(board_index)

        if not is_board_location_enabled(board_location):
            print("Skipping disabled board location %d" % board_index)
            continue

        safe_board_name, scan_dir = make_scan_directory(board_location)
        print("Output: %s" % scan_dir.getAbsolutePath())
        print("Output directory generated: %s" % scan_dir.getAbsolutePath())

        report_file = File(scan_dir.getParentFile(), "report.json")
        if not report_file.exists():
            initial_report = globals().get("initial_report_data", {})
            with open(report_file.getAbsolutePath(), "w") as f:
                json.dump(initial_report, f, indent=4)

        process_board_placements(
            camera,
            board_location,
            safe_board_name,
            scan_dir,
        )

    print("Component image capture sequence complete.")


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
    safe_board_name,
    scan_dir,
):
    with open(report_file.getAbsolutePath(), "r") as f:
        report = json.load(f)

    board_id = (
        initial_report_data.get("metadata", {}).get("sn", safe_board_name)
        if "initial_report_data" in globals()
        else safe_board_name
    )

    board = board_location.getBoard()
    board_side = board_location.getSide()
    placements = filter_placements(board.getPlacements(), board_side)

    active_placements = placements.size()
    photographed_placements = 0

    monitor = ProgressMonitor(None, "Board SN: %s\nScanning components..." % board_id, "", 0, active_placements)
    try:
        for placement_index in range(active_placements):
            if monitor.isCanceled():
                raise Exception("User cancelled scan")

            placement = placements.get(placement_index)
            part_name = placement.getPart().getId()
            placement_designator = placement.getId()

            monitor.setProgress(photographed_placements + 1)
            monitor.setNote("Scanning %d of %d" % (photographed_placements + 1, active_placements))
            safe_part_name = sanitize(part_name)
            safe_placement_designator = sanitize(placement_designator)

            board_local_location = placement.getLocation()

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

            if CROP_IMAGES:
                rotation = machine_location.getRotation()
                image = crop_small_passives(image, safe_part_name, rotation)

            image_file_name = "%s_%s_%s.png" % (
                safe_placement_designator,
                board_id,
                safe_part_name,
            )

            file_obj = File(scan_dir, image_file_name)
            ImageIO.write(image, "PNG", file_obj)

            photographed_placements += 1
            print("Captured %s (%d/%d)" % (safe_placement_designator, photographed_placements, active_placements))
            log_placement(report, safe_placement_designator, safe_part_name, image_file_name, report_file)
    finally:
        monitor.close()


def filter_placements(placements, board_side):
    filtered_placements = ArrayList()

    for placement in placements:
        placement_designator = placement.getId()

        # Skip if no part assigned
        # if placement.getPart() is None:
        #    print("Skipping %s: no part assigned." % placement_designator)
        #    continue

        # Skip parts by active placement side
        if placement.getSide() != board_side:
            continue

        part_name = placement.getPart().getId()
        # Skip parts by ID
        if (
            placement_designator.startswith("MP")
            or placement_designator.startswith("TP")
            or placement_designator.startswith("FD")
            or placement_designator.startswith("REF**")
        ):
            print("Skipping %s (%s)" % (placement_designator, part_name))
            continue
        filtered_placements.add(placement)

    return filtered_placements


def crop_small_passives(image, safe_part_name, rotation_deg):
    if "0201" in safe_part_name:
        scale = 0.11 * CROP_MARGIN_SCALE
    elif "0402" in safe_part_name:
        scale = 0.11 * CROP_MARGIN_SCALE
    elif "0603" in safe_part_name:
        scale = 0.16 * CROP_MARGIN_SCALE
    elif "0805" in safe_part_name:
        scale = 0.22 * CROP_MARGIN_SCALE
    elif "1206" in safe_part_name:
        scale = 0.32 * CROP_MARGIN_SCALE
    else:
        return image

    # Normalize to [0, 360)
    r = rotation_deg % 360

    def near(angle):
        return abs((r - angle + 180) % 360 - 180) <= ANGLE_DEVIATION

    w = image.getWidth()
    h = image.getHeight()

    if near(0) or near(180):
        # Landscape (16:9)
        target_h = int(h * scale)
        target_w = int(target_h * (16.0 / 9.0))

    elif near(90) or near(270):
        # Portrait (9:16)
        target_w = int(h * scale)
        target_h = int(target_w * (16.0 / 9.0))

    else:
        # Square
        side = int(max(w, h) * scale)
        target_w = side
        target_h = side

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

    scan_dir = File(File(root, dir_name), "components")
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


def log_placement(
    report,
    safe_placement_designator,
    safe_part_name,
    image_file_name,
    report_file,
):
    if "parts" not in report:
        report["parts"] = []

    report["parts"].append(
        {
            "part_designator": safe_placement_designator,
            "part_name": safe_part_name,
            "image_file": image_file_name,
        }
    )

    with open(report_file.getAbsolutePath(), "w") as f:
        json.dump(report, f, indent=4)


main()
