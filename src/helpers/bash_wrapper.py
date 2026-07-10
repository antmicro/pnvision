import subprocess
from typing import Optional
from pathlib import Path


def bash(command: str, name: str = "", debug: bool = False, decorators: bool = True, cwd: Optional[Path] = None):
    if name == "":
        name = command
    if decorators:
        print(f"  > {name}...", end="", flush=True)
    stdout = subprocess.PIPE if debug else subprocess.DEVNULL
    try:
        subprocess.run(
            command, encoding="UTF-8", stdout=stdout, stderr=subprocess.PIPE, shell=True, check=True, cwd=cwd
        )
    except subprocess.CalledProcessError as e:
        if decorators:
            print("failed")
        print(f"Subprocess '{command}' returned an error:\n{e.stderr}")
        exit(1)
    if decorators:
        print(" ok")
