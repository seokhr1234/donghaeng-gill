"""Verify the Geofabrik research exports and per-area totals independently."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import shapely
from shapely.geometry import shape


def load(path):
    with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")) as source:
        return json.load(source)


def verify_asset(folder, asset):
    path = folder / asset["path"]
    assert path.stat().st_size == asset["bytes"]
    with path.open("rb") as data:
        assert hashlib.file_digest(data, "sha256").hexdigest() == asset["sha256"]
    return load(path)


def verify_features(data, bounds=None):
    ids = set()
    types = Counter()
    for item in data["features"]:
        ident = item["id"]
        p = item["properties"]
        assert ident == f"{p['osm_type']}/{p['osm_id']}"
        assert ident not in ids
        ids.add(ident)
        geometry = shape(item["geometry"])
        assert geometry.is_valid and not geometry.is_empty
        if bounds is not None:
            assert bounds.intersects(geometry)
        types[geometry.geom_type] += 1
        assert p["field_verified"] is False and p["routing_eligible"] is False
        if "source_node_refs" in p:
            coords = item["geometry"]["coordinates"]
            vertex_sequence = coords[0] if geometry.geom_type == "Polygon" else coords
            assert len(vertex_sequence) == len(p["source_node_refs"])
    return len(ids), types


def main(args):
    report = {"field_verified": False, "routing_eligible": False, "verified": {}}
    for name in ("osco", "seoul"):
        folder = args.root / name / "osm"
        summary = load(folder / "summary.json")
        local_report = {}
        for asset in summary["assets"]:
            values = verify_asset(folder, asset)
            if asset["path"].startswith("osm-invalid-"):
                assert len(values["features"]) == summary["invalid_geometries_inside_bbox"]
                continue
            layer = asset["path"][4:].split(".")[0]
            count, types = verify_features(values)
            expected = summary["counts"][layer]
            assert count == expected["bbox"] and dict(types) == expected["geometry_types"]
            for radius in (1000, 3000):
                assert sum(radius in row["properties"]["within_straight_line_m"] for row in values["features"]) == expected[f"within_{radius}m"]
            local_report[layer] = count
        report["verified"][name] = local_report
    directory = args.root / "seoul" / "osm"
    city = load(directory / "seoul-citywide-summary.json")
    boundaries = load(args.boundaries)["features"]
    city_outline = shape(next(r["geometry"] for r in boundaries if r["properties"]["osm_id"] == "relation/2297418"))
    assert city_outline.is_valid
    shapely.prepare(city_outline)
    counts = {}
    for asset in city["citywide_assets"]:
        values = verify_asset(directory, asset)
        layer = asset["path"].split("citywide-")[1].split(".")[0]
        count, types = verify_features(values, city_outline)
        assert count == city["layers"][layer] and dict(types) == city["geometry_types_by_layer"][layer]
        counts[layer] = count
        del values
    assert len(city["district_intersection_counts"]) == 25 and not city["no_matching_district"]
    report["verified"]["seoul-citywide"] = counts
    report["verified"]["seoul-districts"] = 25
    report["checks"] = ["gzip checksums", "unique IDs", "valid geometries", "matching source node/way vertex counts",
                        "per-radius extract counts", "city layer geometry counts", "city boundary intersection"]
    (args.root / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
parser.add_argument("boundaries", type=Path)
if __name__ == "__main__":
    main(parser.parse_args())
