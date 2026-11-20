# Installation

## Requirements

PnVision is designed to work with `KiCad 9+`.
It requires `python3` to be installed.

## Installation (Debian)

1. Install the requirements:

    ```bash
    sudo apt install kicad python3 python3-opencv libzbar0 pipx
    pipx ensurepath
    ```

2. Clone and install the `PnVision` repository:

    ```bash
    pipx install 'git+https://github.com/antmicro/pnvision.git'
    ```

## Basic usage

To show available commands, run:

```bash
pnvision --help
```
