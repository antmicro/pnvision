from pathlib import Path
import csv


def read_bom(bom: Path) -> list[str]:
    if not bom.exists():
        raise FileNotFoundError(bom)

    dnp_designators = []

    with bom.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["DNP"].strip():
                dnp_designators.append(row["Reference Designators"].strip())

    if len(dnp_designators) == 1:
        print(f"DNP designator: {dnp_designators}")
    elif len(dnp_designators) > 1:
        print(f"DNP designators: {dnp_designators}")

    return dnp_designators


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python read_bom.py <bom_path>")

    read_bom(Path(sys.argv[1]))
