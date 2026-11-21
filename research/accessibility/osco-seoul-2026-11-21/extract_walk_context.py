"""Extract registered pedestrian, rest, building and access geometry from an OSM PBF."""

import argparse
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import osmium
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.validation import explain_validity
from shapely.strtree import STRtree

WALK_HIGHWAYS = {"footway", "path", "pedestrian", "steps", "corridor", "elevator"}
PEDESTRIAN_VALUES = {"yes", "designated", "permissive", "official", "customers", "destination"}
REST_AMENITIES = {"bench", "shelter", "library", "public_bookcase"}
REST_LEISURES = {"park", "garden", "picnic_table", "playground", "recreation_ground"}
SUPPORT_AMENITIES = {"toilets", "drinking_water", "water_point", "community_centre", "social_facility"}
KEYS = ("highway", "foot", "sidewalk", "building", "building:part", "amenity", "bench", "shelter",
        "tourism", "leisure", "landuse", "natural", "public_transport", "railway", "entrance", "barrier",
        "kerb", "crossing", "tactile_paving", "wheelchair", "indoor", "ramp",
        "sidewalk:left", "sidewalk:right", "sidewalk:both")
ACCESS_TAGS = {"entrance", "barrier", "kerb", "crossing", "tactile_paving", "ramp"}
QUALITY_TAGS = ("access", "wheelchair", "incline", "width", "est_width", "surface", "smoothness", "kerb",
                "kerb:height", "tactile_paving", "crossing", "lit", "handrail", "bridge", "tunnel", "layer",
                "opening_hours", "level", "sidewalk", "sidewalk:left", "sidewalk:right", "sidewalk:both")
SCOPE_CONFIGS = {
    "osco": {
        "name": "청주오스코 / 오송역", "representative_point": (127.335363, 36.6267203),
        "anchor_source": "https://www.cbartgallery-osco.com/cbart-osco/contents.do?key=851",
        "bbox": (127.28, 36.59, 127.39, 36.67),
    },
    "wolgok": {
        "name": "서울 월곡역 생활권", "representative_point": (127.0414554, 37.60192),
        "anchor_source": "existing repository donghaeng-nav/dist/final-model.js",
        "bbox": (126.995, 37.568, 127.089, 37.637),
    },
}
OUTPUT_LAYERS = ("pedestrian", "road_context", "rest", "buildings", "access", "transit", "support")


def classify(tags, kind):
    highway = tags.get("highway")
    groups = set()
    if kind == "way" and highway and highway not in {"proposed", "construction"}:
        if highway not in {"bus_stop", "elevator", "crossing"}:
            groups.add("road_context")
        sidewalk = next((tags.get(k) for k in ("sidewalk", "sidewalk:left", "sidewalk:right", "sidewalk:both")
                         if tags.get(k) not in {None, "no", "none", "separate"}), None)
        if highway in WALK_HIGHWAYS or tags.get("foot") in PEDESTRIAN_VALUES or sidewalk:
            groups.add("pedestrian")
    if (kind in {"way", "relation"} and tags.get("area:highway") in WALK_HIGHWAYS
            or kind == "relation" and highway in WALK_HIGHWAYS):
        groups.add("pedestrian")
    if any(tags.get(k) not in {None, "", "no"} for k in ("building", "building:part")):
        groups.add("buildings")
    if (tags.get("amenity") in REST_AMENITIES or tags.get("leisure") in REST_LEISURES
            or tags.get("tourism") == "picnic_site" or tags.get("landuse") in {"recreation_ground", "village_green"}
            or any(tags.get(k) == "yes" for k in ("bench", "shelter"))):
        groups.add("rest")
    if (highway in {"crossing", "elevator", "steps"} or tags.get("railway") == "subway_entrance" or ACCESS_TAGS.intersection(tags)
            or kind == "node" and "wheelchair" in tags):
        groups.add("access")
    if (highway == "bus_stop" or "public_transport" in tags
            or tags.get("railway") in {"station", "halt", "tram_stop", "subway_entrance"}):
        groups.add("transit")
    if tags.get("amenity") in SUPPORT_AMENITIES or tags.get("emergency") == "defibrillator":
        groups.add("support")
    return groups


def inside_bounds(coordinates, bounds):
    west, south, east, north = bounds
    return west <= coordinates[0] <= east and south <= coordinates[1] <= north


def bounds_overlap(xs, ys, bounds):
    west, south, east, north = bounds
    return min(xs) <= east and max(xs) >= west and min(ys) <= north and max(ys) >= south


def encode(path, value, compressed=False):
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    path.write_bytes(gzip.compress(text, mtime=0) if compressed else text)
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def hash_file(path, method):
    with path.open("rb") as source:
        return hashlib.file_digest(source, method).hexdigest()



class SeoulCoverage:
    """Collect citywide reference layers and district counts alongside the Wolgok pilot."""

    SLICE_LAYERS = ("pedestrian", "rest", "buildings")

    def __init__(self, path, destination, publish):
        boundaries = json.loads(path.read_text(encoding="utf-8"))["features"]
        self.city_row = next(row for row in boundaries if row["properties"]["osm_id"] == "relation/2297418")
        self.city = shape(self.city_row["geometry"])
        self.names = [row["properties"]["name"] for row in boundaries if row is not self.city_row]
        districts = [shape(row["geometry"]) for row in boundaries if row is not self.city_row]
        if not self.city.is_valid or len(districts) != 25 or any(not district.is_valid for district in districts):
            raise ValueError("Invalid prior Seoul reference district boundaries")
        self.tree = STRtree(districts)
        shapely.prepare(self.city)
        self.groups = Counter()
        self.by_geometry = defaultdict(Counter)
        self.districts = defaultdict(Counter)
        self.held_invalid = 0
        self.unassigned = Counter()
        self.destination = destination
        destination.mkdir(parents=True, exist_ok=True)
        self.files = {}
        for group in self.SLICE_LAYERS if publish else ():
            temp = destination / f"seoul-citywide-{group}.geojson.gz.part"
            raw = open(temp, "wb")
            zipped = gzip.GzipFile(filename="", fileobj=raw, mode="wb", compresslevel=5, mtime=0)
            output = io.TextIOWrapper(zipped, encoding="utf-8")
            output.write('{"type":"FeatureCollection","features":[')
            self.files[group] = (temp, raw, output)

    def add(self, groups, feature, geom, valid):
        if not self.city.intersects(geom):
            return
        if not valid:
            self.held_invalid += 1
            return
        district_ids = self.tree.query(geom, predicate="intersects")
        for group in groups:
            index = self.groups[group]
            self.groups[group] += 1
            self.by_geometry[group][geom.geom_type] += 1
            for d in district_ids:
                self.districts[self.names[d]][group] += 1
            if not len(district_ids):
                self.unassigned[group] += 1
            if group in self.files:
                output = self.files[group][2]
                output.write(("," if index else "") + json.dumps(feature, ensure_ascii=False, separators=(",", ":"), allow_nan=False))

    def finish(self, meta):
        props = self.city_row["properties"]
        source = {**meta, "scope_id": "seoul-citywide", "scope_name": "서울시 경계 전체",
                  "boundary_source": props["source_url"], "boundary_source_as_of": props["source_as_of"],
                  "bounds_lon_lat": tuple(self.city.bounds),
                  "scope_selection": "Intersects preserved 26 administrative geometries. Cross-boundary objects may occur in multiple district counts. Source geometries stay whole."}
        source.pop("reference_point_source", None)
        source.pop("reference_point_lon_lat", None)
        source.pop("distance_definition", None)
        assets = []
        for group, (temp, raw, output) in self.files.items():
            output.write('],"source_metadata":' + json.dumps(source, ensure_ascii=False, separators=(",", ":")) + '}' + chr(10))
            output.close()
            raw.close()
            final = temp.with_suffix("")
            temp.rename(final)
            assets.append({"path": final.name, "bytes": final.stat().st_size, "sha256": hash_file(final, "sha256")})
        report = {"source_metadata": source, "layers": dict(self.groups),
                  "geometry_types_by_layer": self.by_geometry, "held_invalid_geometry_count": self.held_invalid,
                  "no_matching_district": self.unassigned,
                  "district_intersection_counts": {name: self.districts[name] for name in sorted(self.names)},
                  "citywide_assets": assets}
        target = self.destination / "seoul-citywide-summary.json"
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
        print("Seoul citywide counts", json.dumps(report["layers"], ensure_ascii=False), flush=True)


def extract(args):
    scope = SCOPE_CONFIGS[args.scope]
    bounds = scope["bbox"]
    window = box(*bounds)
    shapely.prepare(window)
    city = SeoulCoverage(args.seoul_boundaries, args.output, args.seoul_geojson) if args.seoul_boundaries else None
    scan_bounds = window.union(city.city.envelope).bounds if city else bounds
    transform = Transformer.from_crs(4326, 5186, always_xy=True)
    point = Point(*transform.transform(*scope["representative_point"]))
    location = osmium.FileProcessor(args.pbf).with_locations("sparse_mem_array")
    areas_metadata = {}
    class RelationMetadata(osmium.SimpleHandler):
        def relation(self, item):
            relation_tags = dict(item.tags)
            if relation_tags.get("type") in {"multipolygon", "boundary"} and classify(relation_tags, "relation"):
                areas_metadata[item.id] = (item.version, item.timestamp.isoformat(), relation_tags)

    area_keys = osmium.filter.KeyFilter("building", "building:part", "amenity", "leisure", "landuse", "tourism", "area:highway", "highway")
    location.with_areas(area_keys, RelationMetadata())
    location.with_filter(osmium.filter.EntityFilter(osmium.osm.NODE | osmium.osm.WAY | osmium.osm.AREA))
    location.with_filter(osmium.filter.KeyFilter(*KEYS, "area:highway"))
    geometry_factory = osmium.geom.GeoJSONFactory()
    records = defaultdict(dict)
    invalid = {}
    observed = Counter()
    source_as_of = location.header.get("osmosis_replication_timestamp")
    if not source_as_of:
        raise ValueError("Missing source snapshot timestamp in PBF header")
    print(f"Extracting {scope['name']} from {source_as_of}", flush=True)

    for obj in location:
        kind = obj.type_str()
        if kind == "a" and obj.from_way():
            continue
        if kind == "n" and (not obj.location.valid() or not inside_bounds((obj.location.lon, obj.location.lat), scan_bounds)):
            continue
        osm_type = {"n": "node", "w": "way", "a": "relation"}[kind]
        obj_id = obj.orig_id() if kind == "a" else obj.id
        if kind == "a":
            if obj_id not in areas_metadata:
                continue
            version, timestamp, tags = areas_metadata[obj_id]
        else:
            tags = dict(obj.tags)
        groups = classify(tags, osm_type)
        if not groups:
            continue
        ref = f"{osm_type}/{obj_id}"
        node_refs = None

        if kind == "n":
            geometry = Point(obj.location.lon, obj.location.lat)
        elif kind == "w":
            try:
                refs = [(n.ref, n.lon, n.lat) for n in obj.nodes]
            except osmium.InvalidLocationError:
                observed["ways_with_unresolved_node_in_national_extract"] += 1
                continue
            if len(refs) < 2:
                continue
            node_refs, xs, ys = zip(*refs)
            if not bounds_overlap(xs, ys, scan_bounds):
                continue
            coords = list(zip(xs, ys))
            may_be_area = (
                tags.get("area") == "yes" or "buildings" in groups or "area:highway" in tags
                or "rest" in groups and (
                    tags.get("leisure") in REST_LEISURES or tags.get("amenity") in {"library", "shelter"}
                    or tags.get("landuse") in {"recreation_ground", "village_green"} or tags.get("tourism") == "picnic_site"
                )
            )
            if tags.get("area") != "no" and may_be_area and len(coords) >= 4 and node_refs[0] == node_refs[-1]:
                geometry = Polygon(coords)
            else:
                geometry = LineString(coords)
        else:
            try:
                coords = [(n.lon, n.lat) for ring in obj.outer_rings() for n in ring]
                if not coords or not bounds_overlap(*zip(*coords), scan_bounds):
                    continue
                geometry = shape(json.loads(geometry_factory.create_multipolygon(obj)))
            except (osmium.InvalidLocationError, osmium.GeometryError):
                observed["areas_with_unresolved_geometry_in_national_extract"] += 1
                continue

        if geometry.is_empty:
            continue
        in_scope = window.intersects(geometry)
        if not in_scope and (not city or not city.city.intersects(geometry)):
            continue
        if kind != "a":
            version, timestamp = obj.version, obj.timestamp.isoformat()
        props = {"osm_id": obj_id, "osm_type": osm_type, "osm_version": version,
                 "osm_timestamp": timestamp, "source_url": f"https://www.openstreetmap.org/{ref}",
                 "tags": tags, "field_verified": False, "routing_eligible": False}
        if node_refs is not None and ("pedestrian" in groups or "road_context" in groups):
            props["source_node_refs"] = node_refs
        f = {"type": "Feature", "id": ref, "geometry": mapping(geometry), "properties": props}
        valid = geometry.is_valid
        if city:
            city.add(groups, f, geometry, valid)
        if not in_scope:
            continue
        if not valid:
            invalid[ref] = {**f, "properties": {**props, "layers": sorted(groups), "geometry_issue": explain_validity(geometry)}}
            continue
        metric = shapely.transform(geometry, transform.transform, interleaved=False)
        d = float(point.distance(metric))
        props["distance_to_osco_or_pilot_reference_m"] = round(d, 2)
        props["within_straight_line_m"] = [radius for radius in (1000, 3000) if d <= radius]
        for group in groups:
            if ref in records[group]:
                raise ValueError(f"Duplicate feature {ref} in {group}")
            records[group][ref] = f

    md5_digest = hash_file(args.pbf, "md5")
    expected_md5 = args.md5.read_text().split()[0] if args.md5 else None
    if expected_md5 and md5_digest != expected_md5:
        raise ValueError("Geofabrik published MD5 and PBF bytes disagree")
    sha256 = hash_file(args.pbf, "sha256")
    meta = {
        "scope_id": args.scope, "scope_name": scope["name"], "source": "OpenStreetMap / Geofabrik",
        "source_url": args.source_url, "source_as_of": source_as_of, "retrieved_at_kst": args.retrieved,
        "source_crs": "EPSG:4326", "distance_calculation_crs": "EPSG:5186", "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors", "license_url": "https://www.openstreetmap.org/copyright",
        "field_verified": False, "routing_eligible": False, "source_pbf_sha256": sha256,
        "source_pbf_bytes": args.pbf.stat().st_size, "source_pbf_md5": md5_digest,
        "publisher_md5_verified": md5_digest == expected_md5,
        "reference_point_source": scope["anchor_source"], "bounds_lon_lat": bounds,
        "reference_point_lon_lat": scope["representative_point"],
        "distance_definition": "Minimum straight-line planar distance from reference point to registered geometry in EPSG:5186; original geometry retained; 1/3 km circles are within bbox.",
        "coverage_limit": "Visible registration in a single OSM release. Geometry is not field surveying, and registered ways/areas may include closed, private, stairs or grade-separated passages.",
        "allowed_geometry_differences": "OSM IDs are counted once per layer, layers can overlap, tags preserved. No snapped connection, entrance point, or new slope.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    if city:
        city.finish(meta)
    assets = []
    counts = {}
    for group in OUTPUT_LAYERS:
        features = sorted(records[group].values(), key=lambda f: f["id"])
        for feature in features:
            assert shape(feature["geometry"]).is_valid
        counts[group] = {
            "bbox": len(features),
            "within_1000m": sum(1000 in f["properties"]["within_straight_line_m"] for f in features),
            "within_3000m": sum(3000 in f["properties"]["within_straight_line_m"] for f in features),
            "geometry_types": dict(Counter(f["geometry"]["type"] for f in features)),
            "coverage_tags": {k: sum(k in f["properties"]["tags"] for f in features) for k in QUALITY_TAGS},
        }
        assets.append(encode(args.output / f"osm-{group}.geojson.gz",
            {"type": "FeatureCollection", "source_metadata": meta, "features": features}, compressed=True))
    assets.append(encode(args.output / "osm-invalid-geometries.json.gz",
        {"source_metadata": meta, "features": sorted(invalid.values(), key=lambda f: f["id"])}, compressed=True))
    named = {}
    target_ids = {"node/368637868", "node/8213401393", "node/10196145723", "way/1423171859"} if args.scope == "osco" else set()
    for group in ("buildings", "transit", "access"):
        for ref, feature in records[group].items():
            p = feature["properties"]
            tags = p["tags"]
            name = tags.get("name:ko", tags.get("name", ""))
            if ref in target_ids or name.replace(" ", "") in {"청주오스코", "오송역", "오송역8번출구", "월곡역"} or (
                tags.get("entrance") and tags.get("ref") in {"8", "08"} and p["distance_to_osco_or_pilot_reference_m"] <= 1500
            ):
                named[ref] = {"name": name, "distance_m": p["distance_to_osco_or_pilot_reference_m"], "tags": tags,
                              "source_url": p["source_url"]}
    rest = list(records["rest"].values())
    rest_categories = {}
    for band in (0, 1000, 3000):
        frequencies = Counter()
        for feature in rest:
            p = feature["properties"]
            if band and band not in p["within_straight_line_m"]:
                continue
            tags = p["tags"]
            label = next((f"{key}={tags[key]}" for key in ("amenity", "leisure", "tourism", "landuse", "bench", "shelter")
                          if key in tags and (key not in {"bench", "shelter"} or tags[key] == "yes")), None)
            if label:
                frequencies[label] += 1
        rest_categories[str(band) if band else "bbox"] = dict(frequencies)
    summary = {"source_metadata": meta, "counts": counts, "rest_primary_categories": rest_categories,
               "invalid_geometries_inside_bbox": len(invalid), "national_scan_notes": dict(observed),
               "named_landmarks": named, "assets": assets}
    path = args.output / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: {area: stats[area] for area in ("bbox", "within_1000m", "within_3000m")}
                      for key, stats in counts.items()}, ensure_ascii=False), flush=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pbf", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--scope", choices=SCOPE_CONFIGS, required=True)
parser.add_argument("--source-url", required=True)
parser.add_argument("--retrieved", required=True, help="KST ISO-8601 time of completed download")
parser.add_argument("--md5", type=Path)
parser.add_argument("--seoul-boundaries", type=Path, help="Prior verified OSM Seoul/district boundary file")
parser.add_argument("--seoul-geojson", action="store_true", help="Write citywide building, pedestrian and rest layers")
if __name__ == "__main__":
    extract(parser.parse_args())
