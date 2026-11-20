"""Generate review tables and compare this collection with the installed map."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape

from extract_osm import DISTRICTS, write_json


COOLING_URL = "https://data.seoul.go.kr/dataList/OA-21065/S/1/datasetView.do"
SOURCE_FIELDS = (
    "시설년도", "시설구분1", "시설구분2", "쉼터명칭", "도로명주소",
    "기본운영_요일", "기본운영_시작시간", "기본운영_종료시간",
    "연장운영_운영여부", "연장운영_요일", "연장운영_시작시간", "연장운영_종료시간",
    "추가운영_운영여부", "추가운영_요일", "추가운영_시작시간", "추가운영_종료시간",
    "비고", "경도", "위도", "X좌표(EPSG:5186)", "Y좌표(EPSG:5186)",
)
HOUR = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00")
DAY = frozenset("월화수목금토일")
DISTRICT_PATTERN = re.compile(r"^서울(?:특별시|시)?\s+(\S+구)(?:\s|$)")


def csv_write(path, rows, columns):
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_complete_schedule(row, prefix):
    days = row[f"{prefix}_요일"].split(",")
    start, end = (row[f"{prefix}_{key}"] for key in ("시작시간", "종료시간"))
    return all(day in DAY for day in days) and HOUR.fullmatch(start) and HOUR.fullmatch(end) and start != end


def cooling_data(raw, collected_date, boundaries, destination, previous_cooling):
    with raw.open(encoding="cp949", newline="") as original:
        reader = csv.DictReader(original)
        if not set(SOURCE_FIELDS) <= set(reader.fieldnames or []):
            raise ValueError("Unexpected Seoul cooling shelter CSV columns")
        original_rows = list(reader)
    city = boundaries["서울특별시"]
    to_wgs84 = Transformer.from_crs(5186, 4326, always_xy=True)
    counter = Counter()
    districts = Counter()
    csv_rows = []
    features = []
    for row in original_rows:
        if None in row or any(row[col] is None for col in SOURCE_FIELDS):
            raise ValueError("Malformed Seoul cooling shelter CSV row")
        lon, lat = (float(row[col]) for col in ("경도", "위도"))
        projected_lon, projected_lat = to_wgs84.transform(
            float(row["X좌표(EPSG:5186)"]), float(row["Y좌표(EPSG:5186)"]),
        )
        if max(abs(projected_lon - lon), abs(projected_lat - lat)) > 0.00005:
            counter["xy_gps_difference_above_0_00005_degrees"] += 1
        else:
            counter["xy_matches_gps_within_0_00005_degrees"] += 1
        point = Point(lon, lat)
        if not city.covers(point):
            counter["outside_osm_city_boundary"] += 1
        district_match = DISTRICT_PATTERN.match(row["도로명주소"]) or DISTRICT_PATTERN.match(row.get("지번주소", ""))
        osm_districts = [name for name in DISTRICTS if boundaries[name].covers(point)]
        district = district_match[1] if district_match and district_match[1] in DISTRICTS else None
        district_basis = "official_address" if district else None
        if district is None and len(osm_districts) == 1:
            counter["district_from_coordinate"] += 1
            district, = osm_districts
            district_basis = "osm_boundary"
        if district is None:
            counter["district_unassigned"] += 1
        elif district not in osm_districts:
            counter["address_district_differs_from_osm"] += 1
        districts[district] += 1
        if all(row[col] for col in ("기본운영_요일", "기본운영_시작시간", "기본운영_종료시간")):
            counter["basic_hours_present"] += 1
        complete = bool(is_complete_schedule(row, "기본운영"))
        if complete:
            counter["basic_hours_complete"] += 1
        for prefix in ("연장운영", "추가운영"):
            if row[f"{prefix}_운영여부"] == "Y":
                counter[f"{prefix}_Y"] += 1
                if is_complete_schedule(row, prefix):
                    counter[f"{prefix}_Y_complete"] += 1
        identity = json.dumps([row["쉼터명칭"], row["도로명주소"], lon, lat], ensure_ascii=False)
        record_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
        properties = {
            "record_id": "seoul-cooling:" + record_id,
            "district": district,
            "district_basis": district_basis,
            "osm_coordinate_district": osm_districts[0] if len(osm_districts) == 1 else None,
            "coordinate_role": "official_facility_reference",
            "source_crs": "EPSG:4326",
            "source_xy_crs": "EPSG:5186",
            "source_url": COOLING_URL,
            "retrieved_date": collected_date,
            "basic_hours_complete": complete,
            "season_currently_confirmed": False,
            "field_verified": False,
            "app_official_hours_conflict": None,
        }
        previous = previous_cooling.get((row["쉼터명칭"], row["도로명주소"], lon, lat))
        fields = {key: row[key] for key in SOURCE_FIELDS}
        if previous:
            counter["same_facility_identity_in_app"] += 1
            if all(previous["official_fields"].get(key) == value for key, value in fields.items()):
                counter["same_exported_official_fields_in_app"] += 1
            properties["app_official_hours_conflict"] = previous.get("official_hours_conflict", False)
            if properties["app_official_hours_conflict"]:
                counter["app_official_hours_conflict"] += 1
        csv_rows.append({**properties, **fields})
        features.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {**properties, "official_fields": fields},
        })
    if len({row["record_id"] for row in csv_rows}) != len(csv_rows):
        raise ValueError("Duplicate facility reference in city CSV")
    csv_write(destination / "seoul-cooling-shelters.csv", csv_rows, list(csv_rows[0]))
    write_json(destination / "seoul-cooling-shelters.geojson", {
        "type": "FeatureCollection", "attribution": "서울특별시 열린데이터광장 (OA-21065)", "features": features,
    })
    return districts, {"rows": len(csv_rows), "checks": dict(counter), "retrieved_date": collected_date}


def osm_data(destination, previous_osm):
    dataset = json.loads((destination / "osm-rest.geojson").read_text(encoding="utf-8"))
    counts = Counter()
    details = Counter()
    rows = []
    current = {}
    district_by_id = {}
    for feature in dataset["features"]:
        data = feature["properties"]
        osm_id = data["osm_id"]
        if osm_id in current:
            raise ValueError(f"Duplicate OSM element {osm_id}")
        current[osm_id] = data
        district_by_id[osm_id] = data["district"]
        counts[data["district"], data["kind"]] += 1
        details[data["kind"], "hours_tag"] += bool(data["opening_hours"])
        details[data["kind"], "restricted_access_tag"] += data["access"] in {"private", "residents", "customers", "no"}
        lon, lat = feature["geometry"]["coordinates"]
        rows.append({
            **{key: value for key, value in data.items() if key != "osm_tags"},
            "longitude": lon, "latitude": lat,
            "osm_tags": json.dumps(data["osm_tags"], ensure_ascii=False, sort_keys=True),
        })
    csv_write(destination / "osm-rest.csv", rows, list(rows[0]))
    # The old shelter layer only selected gazebo and picnic_shelter.
    comparable = {
        osm_id: p for osm_id, p in current.items()
        if p["kind"] != "shelter" or p["shelter_type"] in {"gazebo", "picnic_shelter"}
    }
    shared = previous_osm.keys() & comparable.keys()
    changed = {
        osm_id for osm_id in shared
        if previous_osm[osm_id]["osm_tags"] != comparable[osm_id]["osm_tags"]
    }
    comparison_rows = []
    for status, ids in (
        ("current_only", comparable.keys() - previous_osm.keys()),
        ("previous_only", previous_osm.keys() - comparable.keys()),
        ("mapped_tags_changed", changed),
    ):
        for osm_id in sorted(ids):
            comparison_rows.append({
                "osm_id": osm_id, "change": status,
                "previous_kind": previous_osm.get(osm_id, {}).get("kind"),
                "current_kind": current.get(osm_id, {}).get("kind"),
                "current_district": district_by_id.get(osm_id),
                "source_url": f"https://www.openstreetmap.org/{osm_id}",
            })
    csv_write(destination / "osm-comparison.csv", comparison_rows,
              ["osm_id", "change", "previous_kind", "current_kind", "current_district", "source_url"])
    return counts, {
        "rows": len(rows),
        "counts": {kind: sum(p["kind"] == kind for p in current.values()) for kind in ("bench", "seating", "shelter")},
        "details": {kind: {k: details[kind, k] for k in ("hours_tag", "restricted_access_tag")}
                    for kind in ("bench", "seating", "shelter")},
        "comparison": {
            "basis": "OSM object ID, old shelter scope restricted to gazebo and picnic_shelter",
            "previous_ids": len(previous_osm), "current_comparable_ids": len(comparable),
            "shared": len(shared), "current_only": len(comparable) - len(shared),
            "previous_only": len(previous_osm) - len(shared), "mapped_tags_changed": len(changed),
        },
    }


def official_local_data(features, destination):
    seat_sources = {
        "강남구 벤치 설치 현황": ("gangnam_bench_installation_address", "강남구"),
        "서울특별시 스마트서울맵 · 구로구 안양천명소 주요시설물": ("guro_mapped_bench_installation", "구로구"),
        "성동구 스마트 성동지도": ("seongdong_smart_rest", "성동구"),
    }
    rows = []
    for feature in features:
        data = feature["properties"]
        source = data.get("source", "")
        if source.startswith("전국도시공원정보표준데이터 · 서울특별시 "):
            category, district = "park_seating_inventory", source.split()[-1]
        elif source in seat_sources:
            category, district = seat_sources[source]
        else:
            continue
        if data["kind"] not in {"bench", "seating", "shelter"}:
            continue
        lon, lat = feature["geometry"]["coordinates"]
        rows.append({
            "record_id": data["id"], "category": category, "district": district,
            "name": data["name"], "address": data.get("address"),
            "facility_type": data.get("official_facility_type", data.get("facility_type")),
            "original_facility_description": data.get("original_facility_description"),
            "original_installation_count": data.get("original_installation_count"),
            "longitude": lon, "latitude": lat, "coordinate_crs": "EPSG:4326",
            "coordinate_role": data["coordinate_role"], "coordinate_source_url": data.get("coordinate_source_url"),
            "source": source, "source_url": data["source_url"], "source_as_of": data.get("source_as_of"),
            "retrieved_date": data["retrieved_date"], "license": data["license"],
            "field_verified": False, "notice": data["notice"],
        })
    csv_write(destination / "official-local-rest.csv", rows, list(rows[0]))
    return dict(Counter(row["category"] for row in rows))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cooling_csv", type=Path)
    parser.add_argument("previous_map", type=Path)
    parser.add_argument("derived", type=Path)
    parser.add_argument("--cooling-retrieved-date", required=True)
    args = parser.parse_args()
    previous_osm = {}
    previous_cooling = {}
    existing = json.loads(args.previous_map.read_text(encoding="utf-8"))["features"]
    for feature in existing:
        data = feature["properties"]
        if data.get("osm_id") and data.get("kind") in {"bench", "seating", "shelter"} and data.get("osm_tags"):
            previous_osm[data["osm_id"]] = data
        if data.get("source_url") == COOLING_URL:
            fields = data["official_fields"]
            lon, lat = feature["geometry"]["coordinates"]
            previous_cooling[(fields["쉼터명칭"], fields["도로명주소"], lon, lat)] = data
    boundaries = {
        feature["properties"]["name"]: shape(feature["geometry"])
        for feature in json.loads((args.derived / "osm-boundaries.geojson").read_text(encoding="utf-8"))["features"]
    }
    cooling, cooling_summary = cooling_data(
        args.cooling_csv, args.cooling_retrieved_date, boundaries, args.derived, previous_cooling
    )
    osm, osm_summary = osm_data(args.derived, previous_osm)
    local_summary = official_local_data(existing, args.derived)
    districts = []
    for district in [*sorted(DISTRICTS), None]:
        row = {
            "district": district or "미배정", "cooling_shelters": cooling[district],
            **{f"osm_{kind}": osm[district, kind] for kind in ("bench", "seating", "shelter")},
        }
        if district or any(value for key, value in row.items() if key != "district"):
            districts.append(row)
    csv_write(args.derived / "district-counts.csv", districts, list(districts[0]))
    write_json(args.derived / "summary.json", {
        "districts": sum(bool(cooling[district]) for district in DISTRICTS),
        "cooling_shelters": cooling_summary, "osm": osm_summary,
        "official_local_rest": local_summary,
        "field_verified": False,
    })


if __name__ == "__main__":
    main()
