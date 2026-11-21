"""Read the public S-MAP road-address building layer for the Wolgok pilot."""

import argparse
import gzip
import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pyproj import Transformer
from shapely import transform
from shapely.geometry import Point, mapping, shape
from shapely.validation import explain_validity


VIEW = "https://smap.seoul.go.kr/"
ENDPOINT = "https://smap.seoul.go.kr/smap/imageProxy.do"
LAYER = "seoul:tl_spbd_buld"
LONGITUDE_LATITUDE = [127.0414554, 37.60192]
BBOX = "200660.724,552816.828,206660.724,558816.828,EPSG:5186"
PAGE_SIZE = 5000
CRS = "urn:ogc:def:crs:EPSG::5186"
WGS84 = Transformer.from_crs(5186, 4326, always_xy=True).transform
KST = ZoneInfo("Asia/Seoul")


def get(output, filename, **specific):
    parameters = {
        "svc": "2D", "param": "/geoserver/wfs", "service": "WFS", "version": "2.0.0",
        "request": "GetFeature", "typeNames": LAYER, "bbox": BBOX, **specific,
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(url, timeout=40) as response:
        body = response.read()
        info = {"http_status": response.status, "http_date": response.headers.get("Date")}
    (output / filename).write_bytes(body)
    info.update(path=filename, url=url, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                retrieved_at_kst=datetime.now(KST).isoformat())
    (output / (filename + ".request.json")).write_text(json.dumps(info, indent=2) + "\n")
    return body, info


def acquire(raw):
    hit_body, hit_request = get(raw, "hits.xml", resultType="hits")
    match_count = int(ET.fromstring(hit_body).attrib["numberMatched"])
    if not 1 <= match_count <= 100000:
        raise ValueError(f"Unexpected number of S-MAP building records: {match_count}")
    starts = range(0, match_count, PAGE_SIZE)
    def page(start):
        expected = min(PAGE_SIZE, match_count - start)
        raw_body, request = get(raw, f"page-{start:05d}.json", startIndex=str(start), count=str(expected),
                                sortBy="objectid", outputFormat="application/json", srsName="EPSG:5186",
                                propertyName="objectid,geom,und_flo_co,gro_flo_co,sig_cd,buld_nm,buld_sttus,bdtyp_cd")
        data = json.loads(raw_body)
        if (data["type"] != "FeatureCollection" or data["numberMatched"] != match_count or
                data["crs"]["properties"]["name"] != CRS or data["numberReturned"] != expected or
                len(data["features"]) != expected):
            raise ValueError(f"Inconsistent WFS page at {start}")
        return data["features"], request
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = list(pool.map(page, starts))
    features = [feature for data, _ in pages for feature in data]
    identifiers = [item["properties"]["objectid"] for item in features]
    if len(set(identifiers)) != match_count or identifiers != sorted(identifiers):
        raise ValueError("WFS paging did not return every unique object ID in order")
    return features, [hit_request, *(request for _, request in pages)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raw = args.output / "raw"
    raw.mkdir(parents=True, exist_ok=False)
    input_features, requests = acquire(raw)
    center = Point(Transformer.from_crs(4326, 5186, always_xy=True).transform(*LONGITUDE_LATITUDE))
    invalid, features = [], []
    for feature in input_features:
        geom = shape(feature["geometry"])
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            invalid.append({"id": feature["id"], "reason": explain_validity(geom)})
            continue
        distance = center.distance(geom)
        if distance <= 3000:
            original = feature["properties"]
            features.append({
                "type": "Feature", "id": feature["id"],
                "geometry": mapping(transform(geom, WGS84, interleaved=False)),
                "properties": {**original, "distance_to_reference_m": round(distance, 3),
                               "within_1000m": distance <= 1000, "field_verified": False,
                               "routing_eligible": False},
            })
    counts = {
        "bbox_unique_raw": len(input_features), "invalid_withheld": len(invalid),
        "within_3000m": len(features), "within_1000m": sum(f["properties"]["within_1000m"] for f in features),
    }
    metadata = {
        "source": "서울특별시 S-MAP 도로명주소 건물", "source_url": VIEW, "layer": LAYER,
        "source_snapshot_date": None, "source_crs": "EPSG:5186", "export_crs": "EPSG:4326",
        "bbox_source": BBOX, "center_lonlat": LONGITUDE_LATITUDE, "counts": counts,
        "scope": "WFS bbox results minus invalid geometry, then distance from each full outline to the pilot reference",
        "field_verified": False, "routing_eligible": False, "reuse_status": "로컬 조사 자료",
    }
    collection = {"type": "FeatureCollection", "source_metadata": metadata, "features": features}
    output = args.output / "wolgok-smap-buildings.geojson.gz"
    body = (json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    output.write_bytes(gzip.compress(body, compresslevel=6, mtime=0))
    report = {**metadata, "requests": requests, "invalid_objects": invalid,
              "derived_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (args.output / "smap-building-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
