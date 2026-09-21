import os
from java.lang import System


def config_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")), "pnvision"
        )

    return os.path.join(
        os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming")), "pnvision"
    )


def state_home():
    if not System.getProperty("os.name").lower().startswith("windows"):
        return os.path.join(
            os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state")), "pnvision"
        )

    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")), "pnvision"
    )
