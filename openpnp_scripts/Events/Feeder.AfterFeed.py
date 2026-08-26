from java.io import File
from java.lang import System
import os
import json


def state_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )


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


part_id = part.getId()
feeder_name = feeder.getName()
feeder_id = feeder.getId()

state = load_state()

state[part_id] = {"feeder": feeder_name, "feeder_id": feeder_id}

state_file = get_feeder_state_file()

with open(state_file.getAbsolutePath(), "w") as f:
    json.dump(state, f, indent=4)

print("Feeder state: %s -> %s (%s)" % (part_id, feeder_name, feeder_id))
