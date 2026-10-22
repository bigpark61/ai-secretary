import argparse
import csv
from pathlib import Path

from app.models import DataRecordCreate
from app.repository import FirestoreRepository, create_firestore_client


DEFAULT_CSV = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "manufacturing_analysis_300_enhanced.csv"
)


def read_records(csv_path: Path) -> list[dict]:
    records = []
    with csv_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {
            "RecordID",
            "ProductionVolume",
            "DefectRate",
            "EnergyConsumption",
            "EnergyEfficiency",
            "DowntimePercentage",
            "MaintenanceHours",
            "EnergyPerUnit",
        }
        if not required_columns.issubset(reader.fieldnames or []):
            missing = sorted(required_columns.difference(reader.fieldnames or []))
            raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")

        for row in reader:
            source_id = int(row["RecordID"])
            record = DataRecordCreate(
                id=f"csv-{source_id}",
                source_record_id=source_id,
                production_volume=float(row["ProductionVolume"]),
                defect_rate=float(row["DefectRate"]),
                energy_consumption=float(row["EnergyConsumption"]),
                energy_efficiency=float(row["EnergyEfficiency"]),
                downtime_percentage=float(row["DowntimePercentage"]),
                maintenance_hours=float(row["MaintenanceHours"]),
                energy_per_unit=float(row["EnergyPerUnit"]),
            )
            records.append(record.model_dump(exclude_none=True))
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the provided manufacturing CSV into Firestore."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file path (default: {DEFAULT_CSV})",
    )
    args = parser.parse_args()
    if not args.csv.is_file():
        raise FileNotFoundError(f"CSV file not found: {args.csv}")

    records = read_records(args.csv)
    repository = FirestoreRepository(create_firestore_client())
    imported = repository.upsert_data(records)
    print(f"Imported or updated {imported} records in Firestore collection 'data'.")


if __name__ == "__main__":
    main()
