from pathlib import Path
import csv


def read_bom(bom: Path) -> list[str]:
    if not bom.exists():
        raise FileNotFoundError(bom)

    all_designators = []
    dnp_designators = []

    with bom.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            refs = [r.strip() for r in row["Reference Designators"].split(",")]

            all_designators.append(refs)

            if row["DNP"].strip():
                dnp_designators.append(refs)

    # if len(dnp_designators) == 1:
    #     print(f"DNP designator: {dnp_designators}")
    # elif len(dnp_designators) > 1:
    #     print(f"DNP designators: {dnp_designators}")

    return all_designators, dnp_designators


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python read_bom.py <bom_path>")

    all_designators, dnp_designators = read_bom(Path(sys.argv[1]))
    print("all designators: ")
    print(all_designators)
    print("dmp_designators: ")
    print(all_designators)
