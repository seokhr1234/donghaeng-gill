"""Extract Seoul rest facilities and district boundaries from a Geofabrik PBF."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import osmium
from shapely import make_valid, prepare
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree


SEOUL_RELATION = 2297418
DISTRICTS = frozenset(
    "강남구 강동구 강북구 강서구 관악구 광진구 구로구 금천구 노원구 도봉구 동대문구 동작구 "
    "마포구 서대문구 서초구 성동구 성북구 송파구 양천구 영등포구 용산구 은평구 종로구 중구 중랑구".split()
)


def category(tags):
    if tags.get("amenity") == "bench":
        return "bench"
    if tags.get("amenity") == "shelter":
        return "shelter"
    if tags.get("leisure") == "picnic_table" or tags.get("bench") == "yes":
        return "seating"
    return None


class RelationIndex(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.boundaries = {}
        self.rest_areas = {}
        self.member_ways = set()

    def relation(self, relation):
        tags = dict(relation.tags)
        name = tags.get("name:ko", tags.get("name"))
        if relation.id == SEOUL_RELATION or (
            tags.get("boundary") == "administrative" and tags.get("admin_level") == "6" and name in DISTRICTS
        ):
            group = self.boundaries
        elif tags.get("type") == "multipolygon" and category(tags):
            group = self.rest_areas
        else:
            return
        members = [
            (member.role or "outer", member.ref)
            for member in relation.members
            if member.type == "w" and member.role in ("outer", "inner", "")
        ]
        group[relation.id] = (tags, name, members, relation.timestamp.isoformat())
        self.member_ways.update(ref for _, ref in members)


def area_geometry(members, ways):
    rings = defaultdict(list)
    for role, ref in members:
        if ref not in ways:
            return None
        rings[role].append(ways[ref])
    outer = list(polygonize(unary_union(rings["outer"])))
    if not outer:
        return None
    inner = list(polygonize(unary_union(rings["inner"])))
    geom = unary_union(outer).difference(unary_union(inner))
    return geom if geom.is_valid else make_valid(geom)


class RestObjects(osmium.SimpleHandler):
    def __init__(self, member_ways):
        super().__init__()
        self.member_ways = member_ways
        self.ways = {}
        self.objects = []
        self.skipped = Counter()

    def node(self, node):
        location = node.location
        if not location.valid() or not in_search_bounds(location.lon, location.lat):
            return
        tags = dict(node.tags)
        if category(tags):
            self.objects.append(
                ("node", node.id, tags, node.timestamp.isoformat(), Point(location.lon, location.lat))
            )

    def way(self, way):
        member = way.id in self.member_ways
        tags = dict(way.tags)
        if not member and not category(tags):
            return
        try:
            coordinates = [(node.lon, node.lat) for node in way.nodes]
        except osmium.InvalidLocationError:
            self.skipped["way_missing_member_location_in_national_extract"] += 1
            return
        if len(coordinates) < 2:
            return
        line = LineString(coordinates)
        if member:
            self.ways[way.id] = line
        if category(tags) and any(in_search_bounds(*point) for point in coordinates):
            geom = line
            if len(coordinates) > 3 and line.is_ring and tags.get("area") != "no":
                geom = Polygon(coordinates)
            self.objects.append(("way", way.id, tags, way.timestamp.isoformat(), geom))


def in_search_bounds(lon, lat):
    return 126.70 <= lon <= 127.25 and 37.39 <= lat <= 37.74


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def write_collection(path, features):
    write_json(path, {
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors (ODbL 1.0). Data distributed by Geofabrik.",
        "features": features,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pbf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--retrieved-date", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    header = osmium.io.Reader(str(args.pbf)).header()
    snapshot = header.get("osmosis_replication_timestamp")
    if not snapshot:
        raise ValueError("PBF replication timestamp missing")
    relations = RelationIndex()
    relations.apply_file(str(args.pbf))
    objects = RestObjects(relations.member_ways)
    node_filter = osmium.filter.TagFilter(
        ("amenity", "bench"), ("amenity", "shelter"), ("leisure", "picnic_table"), ("bench", "yes")
    )
    node_filter.enable_for(osmium.osm.NODE)
    objects.apply_file(str(args.pbf), locations=True, idx="sparse_mem_array", filters=[node_filter])

    city = area_geometry(relations.boundaries[SEOUL_RELATION][2], objects.ways)
    if city is None or city.is_empty or not city.is_valid:
        raise ValueError("Invalid Seoul administrative boundary")
    prepare(city)
    districts = {}
    boundaries = []
    for osm_id, (_, name, members, edited) in relations.boundaries.items():
        geom = city if osm_id == SEOUL_RELATION else area_geometry(members, objects.ways)
        if geom is None or geom.is_empty:
            continue
        if osm_id != SEOUL_RELATION:
            if city.intersection(geom).area < geom.area * 0.8:
                continue
            if name in districts:
                raise ValueError(f"Duplicate district relation for {name}")
            districts[name] = geom
        boundaries.append({
            "type": "Feature", "geometry": mapping(geom),
            "properties": {
                "name": name, "osm_id": f"relation/{osm_id}", "last_osm_edit": edited,
                "source_url": f"https://www.openstreetmap.org/relation/{osm_id}",
                "source_as_of": snapshot, "retrieved_date": args.retrieved_date,
            },
        })
    if set(districts) != DISTRICTS:
        raise ValueError(f"Missing districts: {sorted(DISTRICTS - set(districts))}")

    for osm_id, (tags, _, members, edited) in relations.rest_areas.items():
        geom = area_geometry(members, objects.ways)
        if geom is not None and not geom.is_empty:
            objects.objects.append(("relation", osm_id, tags, edited, geom))

    names = list(districts)
    district_index = STRtree(list(districts.values()))
    features = []
    for element, osm_id, tags, edited, geom in objects.objects:
        if not city.intersects(geom):
            continue
        if any(tags.get(key) == "yes" for key in ("disused", "abandoned", "construction")):
            objects.skipped["inactive_tag_inside_seoul"] += 1
            continue
        geom = geom if geom.is_valid else make_valid(geom)
        if geom.is_empty:
            objects.skipped["empty_inside_seoul"] += 1
            continue
        in_city_geometry = city.intersection(geom)
        ref_point = in_city_geometry.representative_point()
        matches = district_index.query(ref_point, predicate="intersects")
        district = names[matches[0]] if len(matches) == 1 else None
        ref = f"{element}/{osm_id}"
        features.append({
            "type": "Feature",
            "geometry": mapping(ref_point),
            "properties": {
                "osm_id": ref, "kind": category(tags), "district": district,
                "name": tags.get("name:ko", tags.get("name")),
                "osm_tags": tags, "last_osm_edit": edited,
                "access": tags.get("access"), "opening_hours": tags.get("opening_hours"),
                "shelter_type": tags.get("shelter_type"),
                "coordinate_role": "mapped_node" if element == "node" else "mapped_geometry_representative_point",
                "source_as_of": snapshot, "retrieved_date": args.retrieved_date,
                "source_crs": "EPSG:4326", "field_verified": False,
                "source_url": f"https://www.openstreetmap.org/{ref}",
                "license": "ODbL-1.0",
            },
        })
    sorted_features = sorted(features, key=lambda f: f["properties"]["osm_id"])
    write_collection(args.output / "osm-rest.geojson", sorted_features)
    write_collection(args.output / "osm-boundaries.geojson", boundaries)
    write_json(args.output / "osm-extraction.json", {
        "source_as_of": snapshot, "retrieved_date": args.retrieved_date,
        "counts": dict(Counter(f["properties"]["kind"] for f in sorted_features)),
        "districts": sorted(districts), "skipped": dict(objects.skipped),
    })


if __name__ == "__main__":
    main()
