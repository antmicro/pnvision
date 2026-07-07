"""OpenPnP automation scripts"""

import argparse
import os
import sys
from typing import Callable, List

import commands

######## ARGUMENT PARSING ########


def get_help_formatter() -> Callable:
    """Returns help formatter."""
    return lambda prog: argparse.HelpFormatter(prog, max_help_position=35)


def get_parser() -> argparse.ArgumentParser:
    formatter = get_help_formatter()

    parser = argparse.ArgumentParser(
        prog="PnVision",
        formatter_class=formatter,
        description="OpenPnP visual inspection utilities.",
    )

    subparsers = parser.add_subparsers(
        title="Subcommands",
        dest="subcommand",
        required=True,
        help='Use "pnvision SUBCOMMAND -h" for command help.',
    )

    command_files = {
        f[:-3] for f in os.listdir(os.path.join(os.path.dirname(__file__), "commands")) if f.endswith(".py")
    }

    for module_name in dir(commands):
        if module_name.startswith("__"):
            continue
        if module_name in command_files:
            getattr(commands, module_name).add_subparser(subparsers)

    return parser


def parse_arguments(args: List[str]) -> argparse.Namespace:
    return get_parser().parse_args(args)


######## MAIN ########


def main() -> None:
    args = parse_arguments(sys.argv[1:])

    args.func(args)


if __name__ == "__main__":
    main()
