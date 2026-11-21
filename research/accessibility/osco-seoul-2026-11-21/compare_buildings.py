"""Compare original OSM and Overture outlines without merging the sources."""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

from shapely import transform
from shapely.geometry import shape
from shapely.strtree import STRtree
from pyproj import Transformer


TO_METERS = Transformer.from_crs(4326, 5186, always_xy=True).transform


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("osm", type=Path)
    parser.add_argument("overture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    osm, overture = map(load, (args.osm, args.overture))
    shapes, source_ids = [], {}
    for feature in osm["features"]:
        geom = shape(feature["geometry"])
        if geom.geom_type not in {"Polygon", "MultiPolygon"}:
            continue
        properties = feature["properties"]
        identity = properties["osm_type"][0] + str(properties["osm_id"])
        source_ids[identity] = (geom, str(properties["osm_version"]))
        shapes.append(transform(geom, TO_METERS, interleaved=False))
    tree = STRtree(shapes)
    totals, flags = Counter(), Counter()
    for feature in overture["features"]:
        properties = feature["properties"]
        source, = properties["sources"]
        dataset = source["dataset"]
        totals[dataset] += 1
        geom = shape(feature["geometry"])
        if dataset == "OpenStreetMap":
            identity, _, version = source["record_id"].partition("@")
            if identity in source_ids:
                outline, osm_version = source_ids[identity]
                flags["shared_osm_ids"] += 1
                if version == osm_version:
                    flags["shared_osm_versions"] += 1
                    flags["same_version_equal_geometry"] += geom.equals(outline)
        else:
            geom = transform(geom, TO_METERS, interleaved=False)
            best_iou = 0
            for index in tree.query(geom, predicate="intersects"):
                candidate = shapes[int(index)]
                overlap = geom.intersection(candidate).area
                if overlap:
                    best_iou = max(best_iou, overlap / (geom.area + candidate.area - overlap))
            flags["non_osm_overlap"] += best_iou > 0
            flags["non_osm_iou_ge_0_5"] += best_iou >= 0.5
            flags["non_osm_no_overlap"] += best_iou == 0
    result = {
        "osm_source": osm["source_metadata"]["source_as_of"], "osm_area_records": len(shapes),
        "overture_release": overture["source_metadata"]["source_release"],
        "overture_records_by_upstream": dict(totals), "counts": dict(flags),
        "comparison_epsg": 5186, "field_verified": False, "routing_eligible": False, "merged_records": 0,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
