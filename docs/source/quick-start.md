# Quick start

## Help

To get available commands and help how to use `PnVision`, run:

```bash
pnvision --help
```

To get help about specific subcommand, call:

```bash
kmake {subcommand} --help
```

## Output generation

To use most of the comments you have to first generate a pcb scan with [OpenPnP](https://openpnp.github.io/).

Follow this guide to generate a sample output from the 'example/' directory.

```bash
cd example/
```

### report

To generate report, run:

```bash
pnvision report report.json
```

The newly created `report` directory will contain report generated from scan.

### stitch

To generate a full board image, run:

```bash
pnvision stitch board/
```

You should see full_board.png in `board/` directory

### code

To read a qr or barcode from the image use:

```bash
pnvision code full_board.png
```

### version

To get version that will be saved to report.json use:

```bash
pnvision version
```

### detect-cv
To compare the data in report.json with the state of placements in `components/` directory using open-cv use:

bash
```
pnvision detect-cv report.json components/
```
