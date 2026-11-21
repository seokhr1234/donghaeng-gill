"""Verify stored public GIS downloads against their manifests and derived layers."""

import gzip
import json
import tarfile
from collections import Counter
from hashlib import sha256
from pathlib import Path

from shapely.geometry import shape


ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes())


def assert_hash(content, record, expected_key="sha256"):
    assert sha256(content).hexdigest() == record[expected_key]


def verify_geometries(collection):
    metadata = collection.get("source_metadata", collection.get("metadata", {}))
    for feature in collection["features"]:
        for key in ("field_verified", "routing_eligible"):
            assert feature["properties"].get(key, metadata.get(key)) is False
        geom = shape(feature["geometry"])
        assert geom.is_valid and not geom.is_empty


def verify_municipal(folder):
    summary = load(folder / "municipal-review-summary.json")
    count = 0
    with tarfile.open(folder / "wfs-originals.tar.gz") as archive:
        names = [name for name in archive.getnames() if name.endswith("/request.json")]
        assert len(names) == summary["raw_request_count"] == 49
        for name in names:
            request = json.load(archive.extractfile(name))
            if not request.get("sha256"):
                continue
            sibling = str(Path(name).parent / Path(request["response_path"]).name)
            body = archive.extractfile(sibling).read()
            assert len(body) == request["bytes"]
            assert_hash(body, request)
            count += 1
    assert count == 46
    geometries = 0
    for layer in summary["layer_statistics"]:
        source = folder / layer["path"]
        assert_hash(source.read_bytes(), layer)
        records = load(source)
        assert len(records["features"]) == layer["study_geo_intersects_valid"]
        verify_geometries(records)
        geometries += len(records["features"])
    assert geometries == summary["valid_distinct_objects_by_layer_study_sum"] == 11145
    return geometries, count


def verify_smap(folder):
    summary = load(folder / "smap-building-summary.json")
    assert len(summary["requests"]) == 16
    with tarfile.open(folder / "wfs-originals.tar.gz") as archive:
        source_ids = set()
        for request in summary["requests"]:
            body = archive.extractfile("raw/" + request["path"]).read()
            assert len(body) == request["bytes"]
            assert_hash(body, request)
            if request["path"].endswith(".json"):
                features = json.loads(body)["features"]
                identifiers = {f["properties"]["objectid"] for f in features}
                assert len(identifiers) == len(features) and not identifiers.intersection(source_ids)
                source_ids.update(identifiers)
    assert len(source_ids) == summary["counts"]["bbox_unique_raw"] == 70879
    path = folder / "wolgok-smap-buildings.geojson.gz"
    assert_hash(path.read_bytes(), summary, "derived_sha256")
    collection = load(path)
    records = collection["features"]
    assert len(records) == len({f["id"] for f in records}) == 56179
    assert sum(f["properties"]["within_1000m"] for f in records) == 4678
    verify_geometries(collection)
    return summary["counts"]


def main():
    official = ROOT / "seoul/official"
    municipal, hashed = verify_municipal(ROOT / "osco/municipal")
    smap = verify_smap(official / "smap-local")
    old = load(official / "oa15554-polygon-review.json")
    assert_hash((official / old["raw_archive"]).read_bytes(), old, "raw_sha256")
    polygon_file = official / "wolgok-2021-official-crossing-polygons.geojson.gz"
    assert_hash(polygon_file.read_bytes(), old, "derived_sha256")
    polygons = load(polygon_file)
    verify_geometries(polygons)
    assert len(polygons["features"]) == 2767 and len(old["invalid_in_bbox_withheld"]) == 24
    for source in load(official / "seoul-official-evidence.json")["sources"].values():
        assert_hash((official / "raw" / f"raw-{source['id']}.bin").read_bytes(), source)
    crossings = load(official / "wolgok-official-crossings-3km.geojson.gz")
    verify_geometries(crossings)
    assert len(crossings["features"]) == 2942
    buildings = load(ROOT / "osco/buildings/overture-buildings-study.geojson.gz")
    verify_geometries(buildings)
    upstream = Counter(f["properties"]["sources"][0]["dataset"] for f in buildings["features"])
    assert upstream == {"OpenStreetMap": 4544, "doi:10.5281/zenodo.8174931": 7359}
    report = {
        "field_verified": False, "routing_eligible": False,
        "osco_municipal_geometries": municipal, "osco_municipal_original_bodies_hashed": hashed,
        "osco_overture_building_records": sum(upstream.values()), "seoul_smap": smap,
        "wolgok_2026_crossing_points_3km": len(crossings["features"]),
        "wolgok_2021_crossing_polygons_3km": len(polygons["features"]),
    }
    (ROOT / "official-source-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
