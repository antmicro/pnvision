from __future__ import absolute_import, division
import re
import json
import math
import os
import csv

from java.io import File
from java.lang import System, Thread
from java.text import SimpleDateFormat
from java.util import Date, ArrayList
from javax.imageio import ImageIO
from javax.swing import ProgressMonitor
from java.lang import Thread

from org.openpnp.model import LengthUnit
from org.openpnp.util import Utils2D, MovableUtils

# ---------------- USER SETTINGS ----------------

# Delay initialized after motion before image capture is executed.
EXTRA_SETTLE_MS = 300

# False = camera.settleAndCapture()
# True  = camera.captureRaw()
USE_CAPTURE_RAW = False

# Crop passive component images
CROP_IMAGES = True

# Component image cropping variables
ANGLE_DEVIATION = 5.0
CROP_MARGIN_SCALE = 1.1

# ------------------------------------------------


def main():
    global scan_dir
    global report_file
    global board_location

    camera = machine.getDefaultHead().getDefaultCamera()

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
        scan_dir,
        safe_board_name,
    )

    print("Component image capture sequence complete.")


def data_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


def optimize_placements(placements):

    if placements.size() <= 1:
        return placements

    points = []

    for i in range(placements.size()):
        loc = placements.get(i).getLocation()
        points.append((loc.getX(), loc.getY()))

    size = len(points)

    distance_matrix = []

    for i in range(size):
        row = []
        for j in range(size):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            row.append(math.sqrt(dx * dx + dy * dy))
        distance_matrix.append(row)

    route = list(range(size))

    improved = True

    while improved:
        improved = False

        for i in range(1, size - 2):
            for j in range(i + 1, size):

                if j - i == 1:
                    continue

                a = route[i - 1]
                b = route[i]
                c = route[j]
                d = route[(j + 1) % size]

                old = distance_matrix[a][b] + distance_matrix[c][d]

                new = distance_matrix[a][c] + distance_matrix[b][d]

                if new < old:
                    route[i : j + 1] = reversed(route[i : j + 1])
                    improved = True

    optimized = ArrayList()

    for index in route:
        optimized.add(placements.get(index))

    return optimized


def get_time_left(active_placements, photographed_placements, camera):
    if USE_CAPTURE_RAW:
        additional_settle_time = 0
    else:
        additional_settle_time = EXTRA_SETTLE_MS

    remaining = active_placements - photographed_placements

    seconds_per_component = 0.25 + (additional_settle_time + camera.getSettleTimeMs()) / 1000.0

    total_seconds = int(remaining * seconds_per_component)

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return "%02d:%02d" % (minutes, seconds)


def load_bom_data(bom_file):
    if bom_file is None:
        return None

    bom_indexed = {}

    with open(bom_file, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            designator = row.get("Reference Designators", "").strip()

            if designator:
                bom_indexed[designator] = {
                    "designator": designator,
                    "manufacturer": row.get("Manufacturer", "").strip(),
                    "mpn": row.get("Manufacturer Part Number", "").strip(),
                    "DNP": row.get("DNP", "").strip(),
                }

    return bom_indexed


def process_board_placements(
    camera,
    board_location,
    scan_dir,
    safe_board_name,
):
    print("Scanning board: %s" % safe_board_name)

    with open(report_file.getAbsolutePath(), "r") as f:
        report = json.load(f)

    pcbdata = initial_report_data.get("pcb", {}) if "initial_report_data" in globals() else {}
    serial_number = pcbdata.get("serial_number")

    board = board_location.getBoard()
    board_side = board_location.getSide()
    placements = filter_placements(board.getPlacements(), board_side)
    placements = optimize_placements(placements)

    active_placements = placements.size()
    photographed_placements = 0

    bom_indexed = load_bom_data(report.get("sourcing", {}).get("bom_file"))

    monitor = ProgressMonitor(
        None,
        "Board SN: %s\nScanning components..." % serial_number,
        "Parts: %d/%d Time left: %s"
        % (
            photographed_placements,
            active_placements,
            get_time_left(active_placements, photographed_placements, camera),
        ),
        0,
        active_placements,
    )
    try:
        for placement_index in range(active_placements):
            if monitor.isCanceled():
                raise Exception("User cancelled scan")

            placement = placements.get(placement_index)
            part_name = placement.getPart().getId() if placement.getPart() is not None else None
            placement_designator = placement.getId()

            monitor.setProgress(photographed_placements + 1)
            monitor.setNote(
                "Parts: %d/%d Time left: %s"
                % (
                    photographed_placements,
                    active_placements,
                    get_time_left(active_placements, photographed_placements, camera),
                )
            )
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

            parts = [safe_placement_designator]

            if serial_number is not None:
                parts.append(serial_number)

            if part_name is not None:
                parts.append(safe_part_name)

            image_file_name = "_".join(parts) + ".png"

            file_obj = File(scan_dir, image_file_name)
            ImageIO.write(image, "PNG", file_obj)

            photographed_placements += 1

            loc = placement.getLocation()

            print("Captured %s (%d/%d)" % (safe_placement_designator, photographed_placements, active_placements))
            log_placement(
                report,
                safe_placement_designator,
                part_name,
                loc.getX(),
                loc.getY(),
                loc.getRotation(),
                image_file_name,
                report_file,
                bom_indexed,
            )
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

        # Skip parts by ID
        if (
            placement_designator.startswith("MP")
            or placement_designator.startswith("TP")
            or placement_designator.startswith("FD")
            or placement_designator.startswith("REF**")
        ):
            print("Skipping %s" % placement_designator)
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


def make_scan_directory(board_location):
    board = board_location.getBoard()
    board_name = board.getName()
    if board_name.endswith(".board.xml"):
        board_name = board_name[: -len(".board.xml")]
    safe_board_name = sanitize(board_name)

    root = File(data_home(), safe_board_name)
    if not root.exists():
        root.mkdirs()

    serial_number = ""
    board_side = str(board_location.getSide()).lower()
    location = ""
    time_str = SimpleDateFormat("yyyy-MM-dd_HH-mm-ss").format(Date())

    if "initial_report_data" in globals():
        scandata = initial_report_data.get("scan", {})
        pcbdata = initial_report_data.get("pcb", {})
        serial_number = pcbdata.get("serial_number")
        location = scandata.get("location")
        time_str = scandata.get("timestamp")

    parts = [serial_number, board_side, time_str, location]

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
    part_name,
    position_x,
    position_y,
    rotation,
    image_file_name,
    report_file,
    bom_indexed,
):
    if "parts" not in report:
        report["parts"] = []

    mpn_original = ""
    manufacturer_original = ""
    dnp_status = ""

    if bom_indexed is not None:
        bom_entry = bom_indexed.get(safe_placement_designator)

        if bom_entry is not None:
            mpn_original = bom_entry.get("mpn", "")
            manufacturer_original = bom_entry.get("manufacturer", "")
            dnp_status = bom_entry.get("DNP", "")

    report["parts"].append(
        {
            "designator": safe_placement_designator,
            "name": part_name,
            "position": {"x": position_x, "y": position_y},
            "rotation": rotation,
            "feeder": "",
            "footprint": "",
            "mpn_original": mpn_original,
            "mpn_placed": "",
            "manufacturer_original": manufacturer_original,
            "manufacturer_placed": "",
            "dnp_status": dnp_status,
            "analyzed_placement_status": "",
            "image_file": image_file_name,
        }
    )

    with open(report_file.getAbsolutePath(), "w") as f:
        json.dump(report, f, indent=4)


main()
