from pathlib import Path
import csv


def read_bom(bom: Path) -> tuple[set[str], set[str]]:
    if not bom.exists():
        raise FileNotFoundError(bom)

    all_designators = set()
    dnp_designators = set()

    with bom.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            refs = [r.strip() for r in row["Reference Designators"].split(",")]

            all_designators.update(refs)

            if row["DNP"].strip():
                dnp_designators.update(refs)

    return all_designators, dnp_designators


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python read_bom.py <bom_path>")

    all_designators, dnp_designators = read_bom(Path(sys.argv[1]))

    if all_designators:
        print(f"Designator{'s' if len(all_designators) > 1 else ''}: {all_designators}\n\n")
    if dnp_designators:
        print(f"DNP designator{'s' if len(dnp_designators) > 1 else ''}: {dnp_designators}")
