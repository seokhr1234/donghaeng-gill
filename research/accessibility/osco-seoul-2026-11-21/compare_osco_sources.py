"""Compare OSM walking and crossing geometry with Cheongju's public GIS."""

import argparse
import gzip
import json
from pathlib import Path

from pyproj import Transformer
from shapely import transform, union_all
from shapely.geometry import box, shape
from shapely.strtree import STRtree


TO_METERS = Transformer.from_crs(4326, 5186, always_xy=True).transform
CORE = box(127.315, 36.61, 127.35, 36.64)


def load_layer(path, predicate=lambda _: True):
    with (gzip.open(path, "rt", encoding="utf-8") if path.suffix == ".gz" else path.open(encoding="utf-8")) as f:
        features = json.load(f)["features"]
    clipped = []
    for feature in features:
        if not predicate(feature["properties"]):
            continue
        geom = shape(feature["geometry"])
        if not geom.is_valid:
            raise ValueError(f"Unexpected invalid geometry in {path}")
        geom = geom.intersection(CORE)
        if not geom.is_empty:
            clipped.append(transform(geom, TO_METERS, interleaved=False))
    return clipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("osm", type=Path)
    parser.add_argument("municipal", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    sidewalks = load_layer(args.municipal / "GT_A003_A.geojson")
    crossings = load_layer(args.municipal / "GT_A004_A.geojson")
    lines = load_layer(args.osm / "osm-pedestrian.geojson.gz", lambda p:
                       p["tags"].get("highway") == "footway" and p["tags"].get("footway") == "sidewalk")
    crossing_lines = load_layer(args.osm / "osm-pedestrian.geojson.gz", lambda p:
                                p["tags"].get("footway") == "crossing")
    crossing_nodes = load_layer(args.osm / "osm-access.geojson.gz", lambda p:
                                p["tags"].get("highway") == "crossing")
    sidewalk_union = union_all(sidewalks)
    threshold = sidewalk_union.buffer(5)
    crossing_index = STRtree(crossings)
    points_and_lines = crossing_lines + crossing_nodes
    results = {
        "bbox_lonlat": list(CORE.bounds),
        "input_crs": "EPSG:4326", "distance_analysis_crs": "EPSG:5186",
        "official_sidewalk_geometries": len(sidewalks),
        "osm_explicit_sidewalk_geometries": len(lines),
        "osm_explicit_sidewalk_length_m": round(sum(line.length for line in lines), 1),
        "osm_sidewalk_length_m_within_5m_of_official_geometry": round(
            sum(line.intersection(threshold).length for line in lines), 1),
        "official_crossing_geometries": len(crossings),
        "osm_crossing_lines": len(crossing_lines),
        "osm_crossing_nodes": len(crossing_nodes),
        "osm_crossing_candidates_within_10m_of_official_geometry": sum(
            bool(len(crossing_index.query(g, predicate="dwithin", distance=10))) for g in points_and_lines),
        "field_verified": False, "routing_eligible": False,
        "notes": [
            "Calculated only inside the same station–OSCO rectangle.",
            "Distances show source proximity. No objects were merged or converted into verified network links.",
        ],
    }
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
