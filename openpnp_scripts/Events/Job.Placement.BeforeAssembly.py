from java.io import File
import json
import os
import sys

scripts_dir = os.path.os.path.join(str(scripting.getScriptsDirectory()), "secondary_scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from utils import state_home


def get_feeder_state_file():
    directory = File(state_home())

    if not directory.exists():
        directory.mkdirs()

    return File(directory, "feeder_state.json")


def load_state():
    state_file = get_feeder_state_file()

    if not state_file.exists():
        return {}

    try:
        with open(state_file.getAbsolutePath(), "r") as f:
            return json.load(f)
    except Exception:
        return {}


placement_designator = placement.getId()
part_id = part.getId()

state = load_state()

state[placement_designator] = {"part": part_id}

state_file = get_feeder_state_file()

with open(state_file.getAbsolutePath(), "w") as f:
    json.dump(state, f, indent=4)

print("Assembly: %s -> %s" % (placement_designator, part_id))
