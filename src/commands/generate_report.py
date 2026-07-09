from pathlib import Path
import json


def add_subparser(subparsers):
    parser = subparsers.add_parser(
        "report",
        help="Generate HTML report from log file.",
    )

    parser.add_argument(
        "log_file_location",
        help="Location of log file.",
    )

    parser.set_defaults(func=run)


def run(args):
    with open(args.config_file_location, "r", encoding="utf-8") as f:
        log = json.load(f)

    print(log)
