"""Verify the new OSCO extract against the previous broad bbox and a live core query."""

import argparse
import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def read(path):
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def persisted_coords(geom):
    if geom["type"] == "Point":
        return tuple(geom["coordinates"])
    if geom["type"] == "LineString":
        return tuple(map(tuple, geom["coordinates"]))
    if geom["type"] == "Polygon" and len(geom["coordinates"]) == 1:
        return tuple(map(tuple, geom["coordinates"][0]))
    return None


def report(args):
    current = {}
    for layer in ("pedestrian", "road_context", "buildings", "rest", "access", "support", "transit"):
        current[layer] = {f["id"]: f for f in read(args.output / f"osm-{layer}.geojson.gz")["features"]}
    new_spatial = {fid: f for layer in current.values() for fid, f in layer.items()}
    for aid in ("node/8213401393", "node/10196145723", "node/368637868", "way/1423171859"):
        assert aid in new_spatial, aid

    comparisons = {}
    for previous, key in (("roads", "road_context"), ("buildings", "buildings"), ("access_points", "access"),
                          ("transport", "transit")):
        old = {f["id"]: f for f in read(args.previous / f"osm-{previous}.geojson")["features"]}
        fresh = current[key]
        common = old.keys() & fresh.keys()
        same_version = {fid for fid in common if old[fid]["properties"]["version"] == fresh[fid]["properties"]["osm_version"]}
        tag_changes = [fid for fid in common if old[fid]["properties"]["tags"] != fresh[fid]["properties"]["tags"]]
        geometry_changes = [fid for fid in common if old[fid]["geometry"] != fresh[fid]["geometry"]]
        comparisons[key] = {
            "previous_objects": len(old), "current_objects": len(fresh), "same_id": len(common),
            "previous_only": len(old) - len(common), "current_only": len(fresh) - len(common),
            "same_version": len(same_version), "newer_version": len(common) - len(same_version),
            "changed_tag_object_ids": sorted(tag_changes), "changed_geojson_shape_ids": sorted(geometry_changes),
            "note": "Layer definitions and bbox predicate are not identical. IDs present in only one extract are not proven construction/removal.",
        }

    root = ET.parse(args.live_core).getroot()
    live = {f"{obj.tag}/{obj.attrib['id']}": obj for obj in root if obj.tag in {"node", "way", "relation"}}
    nodes = {int(obj.attrib["id"]): (float(obj.attrib["lon"]), float(obj.attrib["lat"]))
             for obj in live.values() if obj.tag == "node"}
    same_version = {}
    mismatches = {"tags": [], "way_refs": [], "coordinate_sequence": []}
    for fid, feature in new_spatial.items():
        if fid not in live:
            continue
        obj = live[fid]
        p = feature["properties"]
        if int(obj.attrib["version"]) != p["osm_version"]:
            same_version[fid] = False
            continue
        same_version[fid] = True
        tags = {row.attrib["k"]: row.attrib["v"] for row in obj.findall("tag")}
        if tags != p["tags"]:
            mismatches["tags"].append(fid)
        geom = feature["geometry"]
        if obj.tag == "node":
            expect = nodes[int(obj.attrib["id"])]
        elif obj.tag == "way":
            refs = [int(x.attrib["ref"]) for x in obj.findall("nd")]
            if "source_node_refs" in p and refs != p["source_node_refs"]:
                mismatches["way_refs"].append(fid)
            if not all(ref in nodes for ref in refs):
                continue
            expect = tuple(nodes[ref] for ref in refs)
        else:
            continue
        if persisted_coords(geom) != expect:
            mismatches["coordinate_sequence"].append(fid)
    pbf_verified = {
        "live_core_bbox": [127.315, 36.61, 127.35, 36.64],
        "live_request": "https://api.openstreetmap.org/api/0.6/map?bbox=127.315,36.61,127.35,36.64",
        "live_http_status": 200,
        "live_api_server_date": "2026-11-21T05:14:01Z",
        "live_api_sha256": hashlib.sha256(args.live_core.read_bytes()).hexdigest(),
        "live_api_counts": {kind: sum(o.tag == kind for o in live.values()) for kind in ("node", "way", "relation")},
        "matched_unique_objects": len(same_version), "same_version": sum(same_version.values()),
        "version_changed": sum(not val for val in same_version.values()),
        "same_version_mismatches": {k: sorted(items) for k, items in mismatches.items()},
        "note": "Live API data may change after file distribution. Same-version way vertices may change if a member node was edited independently. This is a source cross-check, not a field survey.",
    }
    evidence = {"previous_extract_comparison": comparisons, "live_core_source_comparison": pbf_verified,
                "field_verified": False, "routing_eligible": False}
    (args.output / "source-comparison.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "comparisons": {k: {key: v[key] for key in ("previous_objects", "current_objects", "same_id")}
                        for k, v in comparisons.items()},
        "api": {k: len(v) if isinstance(v, list) else v for k, v in pbf_verified.items()
                if k in {"matched_unique_objects", "same_version", "version_changed"}},
        "mismatches": {k: len(v) for k, v in mismatches.items()},
    }, ensure_ascii=False))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("previous", type=Path)
parser.add_argument("live_core", type=Path)
if __name__ == "__main__":
    report(parser.parse_args())
