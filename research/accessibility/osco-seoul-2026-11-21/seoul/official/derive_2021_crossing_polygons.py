"""Retain closed, valid crosswalk polygons from the 2021 OA-15554 archive."""

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path

from pyproj import Transformer
from shapely import transform
from shapely.geometry import Point, shape
from shapely.validation import explain_validity


def unrepaired_open_rings(shp):
    with shp.open("rb") as source:
        source.seek(100)
        bad = set()
        seen = 0
        while header := source.read(8):
            number, words = struct.unpack(">2i", header)
            body = source.read(words * 2)
            seen += 1
            if len(body) != words * 2 or number != seen:
                raise ValueError("Unexpected SHP record sequence")
            kind, = struct.unpack_from("<i", body)
            if kind != 5:
                raise ValueError("Expected a 2D Polygon record")
            part_count, point_count = struct.unpack_from("<ii", body, 36)
            starts = struct.unpack_from(f"<{part_count}i", body, 44)
            points_offset = 44 + part_count * 4
            for start, end in zip(starts, (*starts[1:], point_count)):
                first = struct.unpack_from("<dd", body, points_offset + start * 16)
                last = struct.unpack_from("<dd", body, points_offset + (end - 1) * 16)
                if first != last:
                    bad.add(number - 1)
                    break
    return bad, seen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("source_shape", type=Path)
    parser.add_argument("bbox_geojson", type=Path, help="GDAL spatial-filter export with -preserve_fid")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    open_rings, source_rows = unrepaired_open_rings(args.source_shape)
    meters = Transformer.from_crs(4326, 5186, always_xy=True).transform
    center = Point(meters(127.0414554, 37.60192))
    candidates = json.loads(args.bbox_geojson.read_text())["features"]
    features, invalid = [], []
    for feature in candidates:
        if not isinstance(feature["id"], int):
            raise ValueError("Original FIDs must be integers")
        if feature["id"] in open_rings:
            invalid.append({"source_fid": feature["id"], "reason": "Original SHP ring is open"})
            continue
        geom = transform(shape(feature["geometry"]), meters, interleaved=False)
        if not geom.is_valid or geom.is_empty:
            invalid.append({"source_fid": feature["id"], "reason": explain_validity(geom)})
            continue
        gap = center.distance(geom)
        if gap <= 3000:
            feature["properties"].update(field_verified=False, routing_eligible=False,
                                         distance_to_reference_m=round(gap, 3), within_1000m=gap <= 1000)
            features.append(feature)
    archive = args.archive
    metadata = {
        "source_url": "https://data.seoul.go.kr/dataList/OA-15554/S/1/datasetView.do",
        "file_published_date": "2021-08-09", "retrieved_date_kst": "2026-11-21",
        "source_crs": "EPSG:5186", "export_crs": "EPSG:4326",
        "raw_archive": str(archive.relative_to(args.output)),
        "raw_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "raw_http_status": 200, "raw_bytes": archive.stat().st_size,
        "crosswalk_polygon_shp_count": source_rows, "within_query_bbox": len(candidates),
        "within_1000m": sum(f["properties"]["within_1000m"] for f in features),
        "within_3000m": len(features), "invalid_in_bbox_withheld": invalid,
        "field_verified": False, "routing_eligible": False,
    }
    path = args.output / "wolgok-2021-official-crossing-polygons.geojson.gz"
    data = {"type": "FeatureCollection", "source_metadata": metadata, "features": features}
    path.write_bytes(gzip.compress((json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
                                   compresslevel=6, mtime=0))
    (args.output / "oa15554-polygon-review.json").write_text(json.dumps({
        **metadata, "derived_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"polygons_1km": metadata["within_1000m"], "polygons_3km": len(features),
                      "invalid_bbox": len(invalid), "unclosed_bbox": sum("open" in r["reason"] for r in invalid)}))


if __name__ == "__main__":
    main()
