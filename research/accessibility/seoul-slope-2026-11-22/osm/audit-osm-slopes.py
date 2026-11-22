"""Audit Seoul OSM slope tags and archived reference-routing coverage."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import numpy as np
import osmium
import shapely
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.strtree import STRtree

DIRECTION = {"up", "down"}
CATEGORIES = ("missing", "numeric_percent", "numeric_bare", "numeric_degrees", "direction_only", "other")
NUMERICAL = {"numeric_percent", "numeric_bare", "numeric_degrees"}
INCLINE_KEYS = (
    "incline", "incline:forward", "incline:backward", "incline:across", "incline:percent", "sidewalk:incline",
    "sidewalk:left:incline", "sidewalk:right:incline", "sidewalk:both:incline",
    "ramp:incline", "ramp:wheelchair:incline", "crossfall", "cross_slope",
)
WALK_HIGHWAYS = {"footway", "path", "pedestrian", "steps", "corridor", "elevator"}
PEDESTRIAN_VALUES = {"yes", "designated", "permissive", "official", "customers", "destination"}
TOKEN = re.compile(r"^([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*(%|°|deg)?$", re.I)


def classify(raw):
    if raw is None:
        return ("missing", None)
    s = raw.strip().lower()
    m = TOKEN.fullmatch(s)
    if m:
        n = float(m[1])
        if not math.isfinite(n):
            return ("other", None)
        if m[2] in {"°", "deg"}:
            if abs(n) >= 90:
                return ("other", None)
            return ("numeric_degrees", math.tan(math.radians(n)) * 100)
        return ("numeric_percent" if m[2] else "numeric_bare", n)
    return ("direction_only" if s in DIRECTION else "other", None)


def grade_tags(tags):
    return {k: v for k, v in tags.items() if "incline" in k.split(":") or k in {"crossfall", "cross_slope"}}


def published(a):
    return {**{k: a.get(k, 0) for k in CATEGORIES},
            "total": sum(a[k] for k in CATEGORIES), "numeric_total": sum(a[k] for k in NUMERICAL)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Boundaries:
    def __init__(self, path):
        self.source = json.loads(path.read_bytes())
        city, *districts = sorted(self.source["features"],
                                  key=lambda f: f["properties"]["osm_id"] != "relation/2297418")
        self.city = shape(city["geometry"])
        self.names = [f["properties"]["name"] for f in districts]
        self.dist = [shape(f["geometry"]) for f in districts]
        assert self.city.is_valid and len(self.names) == 25 and all(g.is_valid for g in self.dist)
        self.tree = STRtree(self.dist)
        self.bounds = self.city.bounds
        self.boundary_metadata = {
            "input_sha256": digest(path.read_bytes()), "city_relation": city["properties"]["osm_id"],
            "boundary_source_as_of": city["properties"]["source_as_of"], "boundary_source": city["properties"]["source_url"],
            "boundary_rule": "Exact geometry intersects published Seoul polygon. District crossing can count in multiple districts.",
        }
        shapely.prepare(self.city)

    def districts(self, geometry):
        return sorted(self.names[i] for i in self.tree.query(geometry, predicate="intersects"))


class Totals:
    def __init__(self):
        self.layers, self.districts, self.way_tags = defaultdict(Counter), defaultdict(lambda: defaultdict(Counter)), defaultdict(Counter)
        self.tag_key_values, self.raw = defaultdict(Counter), defaultdict(Counter)
        self.zeros, self.very_large = defaultdict(Counter), defaultdict(Counter)

    def add(self, layer, tags, districts):
        raw = tags.get("incline")
        key, pct = classify(raw)
        self.layers[layer][key] += 1
        for name in districts:
            self.districts[layer][name][key] += 1
        if raw is not None:
            self.raw[layer][raw] += 1
        for k, v in grade_tags(tags).items():
            self.tag_key_values[layer][k] += 1
        if pct == 0:
            self.zeros[layer][tags.get("highway", "(없음)")] += 1
        elif pct is not None and abs(pct) > 100:
            self.very_large[layer][raw] += 1
        if "highway" in tags:
            self.way_tags[layer][tags["highway"], key] += 1

    def result(self, names):
        return {"counts": {layer: published(c) for layer, c in sorted(self.layers.items())},
                "district_counts": {layer: {n: published(d[n]) for n in sorted(names)} for layer, d in sorted(self.districts.items())},
                "raw_incline_distribution": {layer: dict(sorted(c.items())) for layer, c in sorted(self.raw.items())},
                "grade_like_key_occurrence": {layer: dict(sorted(c.items())) for layer, c in sorted(self.tag_key_values.items())},
                "explicit_zero_by_highway": {layer: dict(sorted(c.items())) for layer, c in sorted(self.zeros.items())},
                "magnitudes_above_100_percent": {layer: dict(sorted(c.items())) for layer, c in sorted(self.very_large.items())},
                "numbers_by_highway": {layer: {highway: published(Counter({category: c[highway, category] for category in CATEGORIES}))
                                               for highway in sorted({highway for highway, _ in c})}
                                        for layer, c in sorted(self.way_tags.items())}}


def prior_scope(path, boundaries):
    data = json.loads(gzip.decompress(path.read_bytes()))
    t = Totals()
    for f in data["features"]:
        g = shape(f["geometry"])
        assert g.is_valid and boundaries.city.intersects(g)
        districts, tags = boundaries.districts(g), f["properties"]["tags"]
        t.add("archived_pedestrian_objects", tags, districts)
        if g.geom_type == "LineString":
            t.add("archived_pedestrian_lines", tags, districts)
    return {**t.result(boundaries.names), "input_sha256": digest(path.read_bytes()), "source_metadata": data["source_metadata"]}


def runtime(path):
    m = json.loads((path / "manifest.json").read_bytes())
    ways_packed = (path / "assets/ways.json.gz").read_bytes()
    graph_packed = (path / "assets/graph.bin.gz").read_bytes()
    assert digest(ways_packed) == m["assets"]["ways.json.gz"]["sha256"]
    assert digest(graph_packed) == m["assets"]["graph.bin.gz"]["sha256"]
    ways = json.loads(gzip.decompress(ways_packed))
    graph = gzip.decompress(graph_packed)
    assert digest(graph) == m["assets"]["graph.bin.gz"]["raw_sha256"]
    assert len(ways) == m["ways"]

    def array(key, kind):
        spec = m["layout"][key]
        return np.frombuffer(graph, dtype=kind, count=spec["length"], offset=spec["offset"])

    totals = Counter(classify(w[4])[0] for w in ways)
    lengths, indices, finite = array("lengths", "<f8"), array("wayIndex", "<u4"), np.isfinite(array("slopes", "<f4"))
    directions = np.asarray([classify(w[4])[0] == "direction_only" for w in ways], dtype=bool)[indices]
    assert m["metadata"]["registered_numeric_incline_segments"] == int(finite.sum())
    adopted_ways = set(indices[finite])
    return {"manifest": {k: m[k] for k in ("dataset_version", "nodes", "segments", "ways", "bounds", "metadata")},
            "way_registration": published(totals), "distinct_numeric_ways_used_by_active_segments": len(adopted_ways),
            "segments_with_active_numeric_grade": int(finite.sum()), "segments_direction_only": int(directions.sum()),
            "segments_without_active_numeric_grade": int((~finite).sum()),
            "active_segment_count_percent": 100 * int(finite.sum()) / len(finite),
            "numeric_grade_segment_length_m": round(float(lengths[finite].sum()), 2),
            "unmeasured_or_unregistered_grade_segment_length_m": round(float(lengths[~finite].sum()), 2),
            "active_segment_length_percent": 100 * float(lengths[finite].sum()) / float(lengths.sum()),
            "note": "Existing city-walk routing asset covers a broader rectangular OSM extract. Numeric grades are adopted registration constraints, not physical measurements."}


def pbf_scope(pbf, md5_receipt, boundaries):
    t, shapes, omitted = Totals(), [], Counter()
    fs = osmium.FileProcessor(pbf).with_locations("flex_mem")
    header = fs.header.get("osmosis_replication_timestamp")
    assert header, "missing Geofabrik extract timestamp"
    fs.with_filter(osmium.filter.EntityFilter(osmium.osm.NODE | osmium.osm.WAY))
    fs.with_filter(osmium.filter.KeyFilter("highway", *INCLINE_KEYS))
    west, south, east, north = boundaries.bounds
    for obj in fs:
        tags = dict(obj.tags)
        raw = grade_tags(tags)
        h = tags.get("highway")
        layers = []
        if obj.is_node():
            if not raw or not obj.location.valid():
                continue
            lon, lat = obj.location.lon, obj.location.lat
            if not (west <= lon <= east and south <= lat <= north):
                continue
            g = Point(lon, lat)
            layers.append("grade_tagged_nodes")
        else:
            road = h and h not in {"proposed", "construction", "bus_stop", "elevator", "crossing"}
            visibly_walk = h in WALK_HIGHWAYS or (h and (
                tags.get("foot") in PEDESTRIAN_VALUES or any(tags.get(k) not in {None, "no", "none", "separate"}
                     for k in ("sidewalk", "sidewalk:left", "sidewalk:right", "sidewalk:both"))))
            if not (road or visibly_walk or raw):
                continue
            try:
                pts = [(n.lon, n.lat) for n in obj.nodes]
            except osmium.InvalidLocationError:
                omitted["unresolved_ways_in_national_file"] += 1
                continue
            if len(pts) < 2:
                continue
            xs, ys = zip(*pts)
            if max(xs) < west or min(xs) > east or max(ys) < south or min(ys) > north:
                continue
            area = tags.get("area") == "yes" or (tags.get("area") != "no" and "area:highway" in tags)
            if area and len(pts) >= 4 and pts[0] == pts[-1]:
                g = Polygon(pts)
            else:
                g = LineString(pts)
            if road:
                layers.append("highway_way_geometries")
                if g.geom_type == "LineString" and not area:
                    layers.append("highway_lines")
            if visibly_walk and g.geom_type == "LineString" and not area:
                layers.append("pedestrian_context_lines")
                if h in WALK_HIGHWAYS:
                    layers.append("dedicated_pedestrian_highway_lines")
                    if h != "steps":
                        layers.append("dedicated_pedestrian_without_steps")
            if raw:
                layers.append("grade_tagged_ways")
                if not road and not visibly_walk:
                    layers.append("grade_tagged_non_highway_ways")
        if not boundaries.city.intersects(g):
            continue
        if not g.is_valid:
            omitted["invalid_intersecting_geometries"] += 1
            continue
        districts = boundaries.districts(g)
        for layer in layers:
            t.add(layer, tags, districts)
        if raw:
            ident = f"{'node' if obj.is_node() else 'way'}/{obj.id}"
            category, pct = classify(raw.get("incline"))
            shapes.append({"type": "Feature", "id": ident, "geometry": mapping(g), "properties": {
                "source_url": f"https://www.openstreetmap.org/{ident}", "osm_version": obj.version,
                "object_last_edit_utc": obj.timestamp.isoformat(), "district_intersections": districts,
                "highway": h, "name": tags.get("name"), "slope_like_tags": raw, "incline_category": category,
                "parsed_tag_percent": pct, "field_verified": False, "routing_eligible": False}})
    with pbf.open("rb") as f:
        file_sha = hashlib.file_digest(f, "sha256").hexdigest()
    with pbf.open("rb") as f:
        md5 = hashlib.file_digest(f, "md5").hexdigest()
    assert md5 == md5_receipt.read_text().split()[0]
    latest_metadata = {
        "source_url": f"https://download.geofabrik.de/asia/{pbf.name}", "source_as_of": header,
        "source_as_of_kst": datetime.fromisoformat(header.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
        "retrieved_at_kst": datetime.fromtimestamp(pbf.stat().st_mtime, tz=ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "bytes": pbf.stat().st_size, "pbf_sha256": file_sha, "publisher_md5_verified": True, "pbf_md5": md5,
        "source_crs": "EPSG:4326", "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
        "field_verified": False, "routing_eligible": False,
    }
    return {**t.result(boundaries.names), "metadata": latest_metadata,
            "omitted": dict(omitted), "published_grade_tagged_geometries": len(shapes)}, shapes


def publish_districts(path, t):
    cats = ["total", "numeric_total", *CATEGORIES]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["layer", "district", *cats], lineterminator="\n")
        w.writeheader()
        for layer, data in t["district_counts"].items():
            for district, values in data.items():
                w.writerow({"layer": layer, "district": district, **values})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("pbf", type=Path)
    parser.add_argument("md5_receipt", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    previous_source = args.repo / "research/accessibility/osco-seoul-2026-11-21/seoul/osm"
    boundary_file = args.repo / "research/accessibility/seoul-rest-2026-11-20/derived/osm-boundaries.geojson"
    bounds = Boundaries(boundary_file)
    previous = prior_scope(previous_source / "seoul-citywide-pedestrian.geojson.gz", bounds)
    active = runtime(args.repo / "donghaeng-nav/services/city-walk")
    live, shapes = pbf_scope(args.pbf, args.md5_receipt, bounds)
    args.out.mkdir(parents=True, exist_ok=True)
    shape_path = args.out / "osm-seoul-incline-tagged.geojson.gz"
    fc = {"type": "FeatureCollection", "source_metadata": live["metadata"],
          "boundary": bounds.boundary_metadata, "features": sorted(shapes, key=lambda f: f["id"])}
    text = (json.dumps(fc, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode()
    shape_path.write_bytes(gzip.compress(text, mtime=0))
    district_path = args.out / "osm-seoul-incline-districts.csv"
    publish_districts(district_path, live)
    summary = {
        "field_verified": False, "routing_eligible": False, "new_slope_values_promoted": 0,
        "boundary": bounds.boundary_metadata,
        "classification_note": "Primary counts use exact 'incline'. Bare numeric tags and degree tags are reported separately. Up/down have no magnitude. No tag is unknown, never promoted to zero. Position, tag and status retain OSM registration provenance only.",
        "latest_pbf": live, "previous_saved_citywide_pedestrian": previous, "active_city_walk": active,
        "outputs": {p.name: {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())} for p in (shape_path, district_path)},
    }
    (args.out / "osm-seoul-incline-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source": live["metadata"], "latest": live["counts"], "archive": previous["counts"],
                      "active": {k: v for k, v in active.items() if k != "manifest"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
