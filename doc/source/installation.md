# Installation

## Requirements

PnVision is designed to work with `KiCad 9+`.
PnVision requires: `python3` installed.

## Installation (Debian)

1. Install requirements

    ```bash
    sudo apt install kicad python3 python3-opencv libzbar0 pipx
    pipx ensurepath
    ```

2. Clone and install `PnVision` repository:

    ```bash
    pipx install 'git+https://github.com/antmicro/pnvision.git'
    ```


## Basic usage

To show available functionalities run:

```bash
pnvision --help
```
