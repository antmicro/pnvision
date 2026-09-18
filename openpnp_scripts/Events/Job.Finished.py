"""Plays sound after assembly is finished."""

import time
import subprocess

time.sleep(1)
for _ in range(4):
    subprocess.Popen(["canberra-gtk-play", "-i", "complete"])
    time.sleep(0.5)
