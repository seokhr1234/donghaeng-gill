"""Keep only public library-level fields from the retrieved NLSS query."""
import argparse
import csv
from datetime import date
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

from shapely.geometry import Point, shape


SOURCE_URL = "https://www.libsta.go.kr/libsta/statistics/public/stat"
API_URL = "https://www.libsta.go.kr/libsta/statistics/stat/getlibraryexcelstatinfo"
PARAMETERS = {
    "lib_gubun": "LIBTYPE000002",
    "stat_gubun": "DEFAULT",
    "start_year": "2025",
    "end_year": "2025",
    "local_code": "11",
    "local_code_detail": "",
    "sub_location": "",
    "foundation": "",
    "search_lib_name": "",
    "stat_gubuns": "",
    "eval_stat_codes": "",
}
FIELDS = {
    "library_id": "LIB_ID_CODE",
    "name": "LIB_NAME",
    "district": "SIGUGUN",
    "library_type": "LIB_GUBUN_NM",
    "founding_body": "FOUND_NM",
    "address": "ADDR",
    "website": "LIB_URL",
    "public_phone": "PHONE",
    "opening_hours_reported": "OPENING_TIME",
    "regular_closure_reported": "LIB_CLOSED",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("boundaries", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--retrieved-date", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    data = args.input.read_bytes()
    raw = json.loads(data)
    boundaries = {
        feature["properties"]["name"]: shape(feature["geometry"])
        for feature in json.loads(args.boundaries.read_text(encoding="utf-8"))["features"]
    }
    assert raw["result"] == "success" and raw["END_YEAR"] == PARAMETERS["end_year"]
    summary = Counter()
    districts = Counter()
    coordinate_frequency = Counter()
    rows = []
    features = []
    point_inside_reported = 0
    for entry in raw["lib_code_list"]:
        assert entry["LOCAL_CODE"] == "11" and entry["SIGUGUN"] in boundaries
        row = {key: (entry.get(field) or "").strip() for key, field in FIELDS.items()}
        coords = tuple(float(entry[key]) for key in ("GEO_X", "GEO_Y"))
        assert -180 <= coords[0] <= 180 and -90 <= coords[1] <= 90
        coordinate_frequency[coords] += 1
        point = Point(coords)
        summary["inside_osm_city_boundary"] += boundaries["서울특별시"].covers(point)
        district_match = boundaries[row["district"]].covers(point)
        point_inside_reported += district_match
        summary["with_registered_opening_hours"] += bool(row["opening_hours_reported"])
        summary["with_registered_holidays"] += bool(row["regular_closure_reported"])
        districts[row["district"]] += 1
        row.update({
            "coordinate_role": "library_reference_point",
            "coordinate_reference": "GEO_X/GEO_Y lon/lat, CRS not explicitly stated in response",
            "coordinate_in_reported_osm_district": bool(district_match),
            "source_as_of": raw["END_YEAR"],
            "retrieved_date": args.retrieved_date.isoformat(),
            "source_url": SOURCE_URL,
            "field_verified": False,
        })
        rows.append({**row, "longitude": coords[0], "latitude": coords[1]})
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": coords},
            "properties": row,
        })
    assert len({row["library_id"] for row in rows}) == len(rows)
    assert len(districts) == len(boundaries) - 1 == 25
    args.destination.mkdir(parents=True, exist_ok=True)
    with (args.destination / "seoul-public-libraries-2025.csv").open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    collection = {"type": "FeatureCollection", "attribution": "문화체육관광부 국가도서관통계시스템", "features": features}
    (args.destination / "seoul-public-libraries-2025.geojson").write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = {
        "provider": "문화체육관광부 국가도서관통계시스템",
        "source_url": SOURCE_URL,
        "request": {"method": "GET", "url": API_URL + "?" + urlencode(PARAMETERS), "query": PARAMETERS},
        "source_as_of": raw["END_YEAR"],
        "retrieved_date": args.retrieved_date.isoformat(),
        "sha256_original": hashlib.sha256(data).hexdigest(),
        "bytes_original": len(data),
        "rows": len(rows),
        "districts": dict(sorted(districts.items())),
        "checks": {
            **summary,
            "valid_lon_lat": len(rows),
            "inside_reported_osm_district": point_inside_reported,
            "coordinate_pairs_shared_by_multiple_records": sum(n > 1 for n in coordinate_frequency.values()),
        },
        "license": "Specific redistribution license not found on the queried page",
        "raw_preserved_in_project": False,
        "field_verified": False,
    }
    (args.destination / "seoul-public-libraries-2025-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
