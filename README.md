# PnVision - Scripts for automatic PCB inspection

Copyright (c) 2026 [Antmicro](https://www.antmicro.com)

This tool was designed to capture images of individual PCB components and complete assembled boards using [OpenPnP](https://openpnp.github.io/) for documentation and reference purposes.

## Table of Contents

1. [Installation](#installation)
3. [Usage](#usage)
4. [License](#license)

## Installation

### PnVision scripts:
> [!IMPORTANT]
> All versions tagged have been tested on OpenPnP 2.6 and 2.7 press-play-walk-away fork.

Requirements:

* Python ≥ 3.10
* libzbar0

Optional:
* [kicad-make](https://github.com/antmicro/kicad-make) - can be used for position files generation

To install script, run following command (we suggest using `pipx`):

```bash
pipx install .
```
in the project repository.

You can now use:

```bash
pnvision --help
```

### OpenPnP scripts:
1. In OpenPnP presss `Scripts` then `Open Scripts Directory` and copy all the files and folders from `openpnp_scripts`.

![How to open scripts directory](img/scripts_directory.png)

## Usage

### OpenPnP scripts:
From the top toolbar, select `Scripts`, then click `perform_inspection.py` and follow the instructions displayed in the pop-up windows.

### PnVision scripts:
Available commands:

| Command | Description |
|---|---|
| `report` | Generate an HTML report from a scan |
| `stitch` | Stitch OpenPnP images into one board image |
| `code` | Read a QR code from an image |
| `bom` | List DNP designators from the BOM |
| `version` | Print the installed version |
| `collage` | Generate a component collage |
| `detect-cv` | Detect component placement |
| `deploy` | Deploy CI-generated data to OpenPnP |

### Examples
```bash
pnvision report [--template-dir TEMPLATE_DIR] INPUT_JSON
```
* TEMPLATE_DIR - Template directory with report.html, favicon.ico and logo.svg
* INPUT_JSON - Input report JSON file

```bash
pnvision code IMAGE_PATH
```
* IMAGE_PATH - The image file with QR or barcode


## License
This project is published under the [Apache-2.0](LICENSE) license.
