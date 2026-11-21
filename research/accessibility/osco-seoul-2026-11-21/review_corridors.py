"""Review connectivity between reference points on retained OSM nodes."""

import argparse
import gzip
import heapq
import json
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Geod


GEOD = Geod(ellps="WGS84")
DEDICATED = {"footway", "pedestrian", "path"}
LOCAL_STREETS = {"living_street", "residential", "unclassified", "service"}
RESTRICTED = {"no", "private", "customers", "residents"}
BLOCKING_BARRIERS = {"wall", "fence", "stile", "turnstile"}


def distance(a, b):
    return GEOD.inv(a[0], a[1], b[0], b[1])[2]


def eligible(tags, include_local_streets):
    allowed = DEDICATED | LOCAL_STREETS if include_local_streets else DEDICATED
    return (
        tags.get("highway") in allowed
        and tags.get("area") != "yes"
        and tags.get("foot") not in RESTRICTED
        and tags.get("access") not in RESTRICTED
        and tags.get("wheelchair") != "no"
        and tags.get("indoor") in {None, "no"}
        and tags.get("layer") in {None, "0"}
        and tags.get("level") in {None, "0"}
        and tags.get("bridge") in {None, "no"}
        and tags.get("tunnel") in {None, "no"}
        and tags.get("location") in {None, "surface", "outdoor", "overground"}
    )


def make_graph(objects, include_local_streets):
    nodes = {node["id"]: node for node in objects["nodes"]}
    graph = defaultdict(list)
    tags_by_way = {}
    for way in objects["ways"]:
        tags = way["tags"]
        if not eligible(tags, include_local_streets):
            continue
        tags_by_way[way["id"]] = tags
        for a, b in zip(way["nodes"], way["nodes"][1:]):
            if a not in nodes or b not in nodes:
                continue
            x, y = nodes[a], nodes[b]
            if any(node["tags"].get("barrier") in BLOCKING_BARRIERS
                   or node["tags"].get("access") in RESTRICTED for node in (x, y)):
                continue
            length = distance(x["coordinates"], y["coordinates"])
            if length <= 0:
                continue
            if tags.get("oneway:foot") != "-1":
                graph[a].append((b, length, way["id"]))
                graph.setdefault(b, [])
            if tags.get("oneway:foot") not in {"yes", "1", "true"}:
                graph[b].append((a, length, way["id"]))
                graph.setdefault(a, [])
    return nodes, graph, tags_by_way


def match_anchor(anchor, nodes, graph):
    if not graph:
        return None
    known_node = anchor.get("osm_node")
    reference = anchor["coordinates"]
    if known_node in graph:
        return {"node": known_node, "gap_m": round(distance(reference, nodes[known_node]["coordinates"]), 1),
                "basis": "registered_osm_node"}
    gap, node_id = min((distance(reference, nodes[node_id]["coordinates"]), node_id) for node_id in graph)
    return {"node": node_id, "gap_m": round(gap, 1), "basis": "nearest_registered_node"}


def find_path(graph, start, end):
    if start == end:
        return None
    heap, lengths, parents = [(0, start)], {start: 0}, {}
    while heap:
        total, node = heapq.heappop(heap)
        if total != lengths[node]:
            continue
        if node == end:
            break
        for neighbor, gap, way in graph[node]:
            candidate = total + gap
            if candidate < lengths.get(neighbor, float("inf")):
                lengths[neighbor] = candidate
                parents[neighbor] = (node, way)
                heapq.heappush(heap, (candidate, neighbor))
    if end not in parents:
        return None
    node, nodes, ways = end, [end], []
    while node != start:
        node, way = parents[node]
        nodes.append(node)
        ways.append(way)
    return nodes[::-1], ways[::-1], lengths[end]


def review(objects, pairs):
    report = []
    features = []
    for include_streets in (False, True):
        nodes, graph, tags_by_way = make_graph(objects, include_streets)
        profile = "dedicated_and_local_streets" if include_streets else "dedicated_paths_only"
        for pair in pairs:
            start = match_anchor(pair["from"], nodes, graph)
            end = match_anchor(pair["to"], nodes, graph)
            path = (find_path(graph, start["node"], end["node"]) if start and end
                    and max(start["gap_m"], end["gap_m"]) <= 150 else None)
            entry = {"id": pair["id"], "from": pair["from"], "to": pair["to"],
                     "registered_start": start, "registered_end": end, "profile": profile,
                     "status": "registered_path_for_review" if path else "path_unresolved",
                     "field_verified": False, "routing_eligible": False}
            if path:
                path_nodes, path_ways, length = path
                ways = set(path_ways)
                entry.update(
                    length_m=round(length, 1), matched_way_count=len(ways),
                    highway_types=dict(Counter(tags_by_way[w]["highway"] for w in ways)),
                    ways_with_registered_width=sum("width" in tags_by_way[w] for w in ways),
                    ways_with_registered_incline=sum("incline" in tags_by_way[w] for w in ways),
                    crossed_osm_node_ids=[n for n in path_nodes if nodes[n]["tags"].get("highway") == "crossing"],
                    osm_way_ids=sorted(ways),
                )
                features.append({
                    "type": "Feature", "geometry": {"type": "LineString",
                                                     "coordinates": [nodes[n]["coordinates"] for n in path_nodes]},
                    "properties": {"corridor": pair["id"], "profile": profile, "length_m": round(length, 1),
                                   "field_verified": False, "routing_eligible": False},
                })
            report.append(entry)
    anchors = {p["id"]: p for pair in pairs for p in (pair["from"], pair["to"])}
    for anchor in anchors.values():
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": anchor["coordinates"]},
                         "properties": {**anchor, "field_verified": False, "routing_eligible": False}})
    return report, features


def load_objects(source):
    if not source.is_dir():
        with (gzip.open(source, "rt", encoding="utf-8") if source.suffix == ".gz"
              else source.open(encoding="utf-8")) as f:
            return json.load(f)
    nodes, ways = {}, {}
    for layer in ("road_context", "pedestrian", "access"):
        with gzip.open(source / f"osm-{layer}.geojson.gz", "rt", encoding="utf-8") as f:
            features = json.load(f)["features"]
        for feature in features:
            typ, ident = feature["id"].split("/")
            ident = int(ident)
            props, geometry = feature["properties"], feature["geometry"]
            if typ == "node" and geometry["type"] == "Point":
                nodes[ident] = {"id": ident, "coordinates": geometry["coordinates"], "tags": props["tags"]}
            if layer == "access" or typ != "way" or geometry["type"] != "LineString":
                continue
            refs, coordinates = props["source_node_refs"], geometry["coordinates"]
            if len(refs) != len(coordinates):
                raise ValueError(f"Node order does not match retained geometry for way/{ident}")
            for ref, point in zip(refs, coordinates):
                item = nodes.setdefault(int(ref), {"id": int(ref), "coordinates": point, "tags": {}})
                if item["coordinates"] != point:
                    raise ValueError(f"Conflicting original coordinates for node/{ref}")
            ways[ident] = {"id": ident, "nodes": list(map(int, refs)), "tags": props["tags"]}
    summary = json.loads((source / "summary.json").read_text(encoding="utf-8"))
    return {"nodes": list(nodes.values()), "ways": list(ways.values()),
            "source_metadata": summary.get("source_metadata", summary.get("source"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("osm_objects", type=Path)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    objects = load_objects(args.osm_objects)
    pairs = json.loads(args.pairs.read_text(encoding="utf-8"))
    report, features = review(objects, pairs)
    args.output.mkdir(exist_ok=True, parents=True)
    (args.output / "corridor-review.json").write_text(json.dumps({
        "source": objects.get("source_metadata", objects.get("metadata")),
        "source_crs": "EPSG:4326", "field_verified": False, "routing_eligible": False,
        "reference_point_connection_limit_m": 150, "records": report,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "corridor-review.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "attribution": "© OpenStreetMap contributors (ODbL 1.0)",
        "features": features,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
