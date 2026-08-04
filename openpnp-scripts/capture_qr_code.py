from org.openpnp.util.UiUtils import submitUiMachineTask
from org.openpnp.util import Utils2D, MovableUtils
from org.openpnp.model import LengthUnit
from java.io import File
from javax.imageio import ImageIO


def main():
    submitUiMachineTask(capture_qr_code)


def capture_qr_code():
    board = board_location.getBoard()
    board_side = board_location.getSide()
    camera = machine.getDefaultHead().getDefaultCamera()

    for placement in board.getPlacements():
        placement_designator = placement.getId()

        if placement_designator.startswith("QR") and placement.getSide() == board_side:

            machine_location = Utils2D.calculateBoardPlacementLocation(
                board_location, placement.getLocation()
            ).convertToUnits(LengthUnit.Millimeters)

            MovableUtils.moveToLocationAtSafeZ(camera, machine_location)

            image = camera.settleAndCapture()

            file_obj = File(qr_image)
            ImageIO.write(image, "PNG", file_obj)

            return True

    return False


main()
