"""Verify the Zenodo sidewalk measurements and count samples by a supplied Seoul district layer."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import zipfile

from shapely.geometry import Point, shape


def digest(path, algo):
    with path.open("rb") as src:
        return hashlib.file_digest(src, algo).hexdigest()


def summarize(values):
    return {
        "minimum": min(values),
        "maximum": max(values),
        "median": statistics.median(values),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--boundaries", type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory
    record = json.loads((directory / "zenodo-current.json").read_text())
    assert record["id"] == 22908353 and record["metadata"]["license"]["id"] == "cc-zero"
    published = {row["key"]: row for row in record["files"]}
    artifacts = {}
    for name in ("summary_attributes.csv", "ground_truth_protocol.zip"):
        path = directory / name
        listing = published[name]
        assert path.stat().st_size == listing["size"]
        md5 = digest(path, "md5")
        assert listing["checksum"] == f"md5:{md5}"
        artifacts[name] = {
            "bytes": path.stat().st_size,
            "publisher_md5": md5,
            "sha256": digest(path, "sha256"),
            "download": listing["links"]["self"],
        }
    protocol = directory / "ground_truth_protocol.zip"
    with zipfile.ZipFile(protocol) as archive:
        assert archive.testzip() is None
        description = archive.read("docs/ground_truth_protocol.md").decode()
        assert description.count("recorded in degrees") == 2
    with (directory / "summary_attributes.csv").open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames
        rows = list(reader)
    column_units = {"width": "m", "running_slope": "degree", "cross_slope": "degree"}
    assert len(rows) == 514 and all(len(row) == len(columns) for row in rows)
    unique_images = {row["filename"] for row in rows}
    assert len(unique_images) == len(rows)
    coordinates = {(float(row["longitude"]), float(row["latitude"])) for row in rows}
    assert len(coordinates) == 513
    boundary_collection = json.loads(args.boundaries.read_text())
    districts = {
        f["properties"]["name"]: shape(f["geometry"])
        for f in boundary_collection["features"]
        if f["properties"]["name"] != "서울특별시"
    }
    assert len(districts) == 25
    groups = defaultdict(list)
    for row in rows:
        point = Point(float(row["longitude"]), float(row["latitude"]))
        matches = [district for district, g in districts.items() if g.covers(point)]
        if len(matches) != 1:
            raise ValueError(f"Expected one district for {row['filename']}, got {matches}")
        groups[matches[0]].append(row)
    district_counts = {}
    for name in sorted(districts):
        subset = groups[name]
        result = {
            "image_rows": len(subset),
            "unique_coordinates": len({(row["longitude"], row["latitude"]) for row in subset}),
        }
        if subset:
            result["longitude_bounds"] = [
                min(float(r["longitude"]) for r in subset), max(float(r["longitude"]) for r in subset)]
            result["latitude_bounds"] = [
                min(float(r["latitude"]) for r in subset), max(float(r["latitude"]) for r in subset)]
        district_counts[name] = result
    measurements = {}
    for key, unit in column_units.items():
        items = [float(row[key]) for row in rows if row[key]]
        assert all(math.isfinite(item) for item in items)
        measurements[key] = {"unit": unit, "rows": len(items), **summarize(items)}
    output = {
        "record_url": record["links"]["self_html"],
        "doi": record["metadata"]["doi"],
        "license": "CC0-1.0",
        "record_published": record["metadata"]["publication_date"],
        "survey_dates": ["2026-07-07", "2026-07-08", "2026-07-10", "2026-07-11"],
        "survey_dates_source": "https://arxiv.org/html/2609.17882v1#S4.T2",
        "source_spatial_columns": ["longitude", "latitude"],
        "source_coordinate_reference_system": "not formally declared in the CSV or protocol",
        "spatial_check_assumption": "Inputs treated as longitude-latitude coordinates for district comparison. This does not establish survey datum.",
        "district_boundary_source": str(args.boundaries),
        "district_boundary_sha256": digest(args.boundaries, "sha256"),
        "district_boundary_attribution": boundary_collection.get("attribution"),
        "district_counts": district_counts,
        "rows": len(rows),
        "unique_coordinates": len(coordinates),
        "unique_images": len(unique_images),
        "coverage_type": "point samples paired with field images",
        "csv_columns": columns,
        "replication_field_verified": False,
        "original_slope_measurement_type": "field measured",
        "routing_eligible": False,
        "measurement_summary": measurements,
        "damage_grade_counts": dict(sorted(Counter(row["damage"] for row in rows).items())),
        "acquired_files": artifacts,
        "imagery_downloaded": False,
    }
    (directory / "verified-measurements.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
