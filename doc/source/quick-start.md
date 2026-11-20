# Quick start

## Help

To show available commands and information on how to use PnVision, run:

```bash
pnvision --help
```

To get help about a specific subcommand, call:

```bash
kmake {subcommand} --help
```

## Output generation

To use most of the commands you have to first generate a PCB scan with [OpenPnP](https://openpnp.github.io/).

Follow this guide to generate a sample output from the `example/` directory.

```bash
cd example/
```

### Report

To generate a report, run:

```bash
pnvision report report.json
```

The newly created `report` directory will contain a report generated from the scan.

### Stitch

To generate a full board image, run:

```bash
pnvision stitch board/
```

You should see a `full_board.png` file in the `board/` directory.

### Code

To read a QR code or a barcode from the image, use:

```bash
pnvision code full_board.png
```

### Version

To print the PnVision version that will be saved to `report.json`, use:

```bash
pnvision version
```

### Detect-cv

To compare the data in `report.json` with the state of placements in the `components/` directory using open-cv, use:

bash
```
pnvision detect-cv report.json components/
```
