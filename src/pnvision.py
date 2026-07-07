"""OpenPnP automation scripts"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands"


def run_script(script_name: str) -> None:
    """Run a command script."""
    script = COMMANDS / script_name

    if not script.exists():
        print(f"Error: {script} not found.", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([sys.executable, str(script)])
    sys.exit(result.returncode)


######## MAIN ########

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="PnVision",
        description="OpenPnP visual inspection utilities.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("stitch", help="Run board stitching")

    args = parser.parse_args()

    if args.command == "stitch":
        run_script("stitch_board.py")


if __name__ == "__main__":
    main()
