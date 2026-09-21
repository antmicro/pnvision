from java.io import File
import os
import sys

scripts_dir = os.path.os.path.join(str(scripting.getScriptsDirectory()), "secondary_scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from utils import state_home

state_file = File(state_home(), "feeder_state.json")

if state_file.exists():
    state_file.delete()

print("Feeder state cleared.")
