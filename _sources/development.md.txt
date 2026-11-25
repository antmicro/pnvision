# Development

## Repository structure

`PnVision` repository structure:

```bash
.
├── doc
│   ├── Makefile
│   ├── requirements.txt
│   └── source
│       ├── conf.py
│       ├── ...
│       └── usage.md
├── example
├── img
├── openpnp_scripts
│   ├── Events
│   │   └── Feeder.AfterFeed.py
│   ├── perform_inspection.py
│   └── secondary_scripts
│       ├── capture_board.py
│       ├── capture_components.py
│       ├── ...
│       └── capture_qr_code.py
├── pyproject.toml
├── README.md
└── src
    └── pnvision
        ├── commands
        │   ├── deploy.py
        │   ...
        │   └── version.py
        │       ├── helpers
        │       ├── bash_wrapper.py
        │       └── __init__.py
        ├── __init__.py
        ├── pnvision.py
        ├── template
        │   ├── favicon.ico
        │   ├── logo.svg
        │   └── report.html
        └── collage_template
            ├── favicon.ico
            ├── logo.svg
            └── report.html
```

## Commands

Commands are stored in the `commands` directory.
Keep the entry command concise and easy to follow for the user.

## New command example

Add your typer entry to `pnvision.py` using the following format:

```python
@app.command(help="Help message.")
def new_command(
    artifacts_directory: Annotated[
        Path,
        typer.Argument(help="Argument help message."),
    ],
) -> None:
    from .commands.new_command import command

    new_command(directory=artifacts_directory)
```

## OpenPnP scripts

Ideally, OpenPnP scripts should have one function only. Shared functions should be in the `helpers.py` script.

### Importing the scripts

```bash
import sys

scriptsDir = str(scripting.getScriptsDirectory())

if scriptsDir not in sys.path:
    sys.path.insert(0, scriptsDir)

from script2 import myFunction
result = myFunction(machine)
print "Result:", result
```
