"""Extract contemporary Seoul official crossings and reference older precision holdings."""
from collections import Counter, defaultdict
from csv import DictReader, DictWriter
from email.utils import parsedate_to_datetime
from hashlib import sha256
from math import hypot, isfinite
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo
import argparse
import json

from openpyxl import load_workbook
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform
from zipfile import ZipFile

CENTER = (127.0414554, 37.60192)
RANGES = (1000, 3000)
ROAD_NAMES = {"월곡로", "화랑로", "종암로", "오패산로"}
DISTRICTS = {"성북구", "동대문구", "강북구", "중랑구", "노원구"}
TO_METERS = Transformer.from_crs(4326, 5186, always_xy=True)
KST = ZoneInfo("Asia/Seoul")


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def csv_save(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def source_evidence(directory, number, publication, dataset_url, source_crs):
    path = directory / f"raw-{number}.bin"
    request = (directory / f"raw-{number}.url").read_text().strip()
    headers = (directory / f"raw-{number}.headers").read_text().splitlines()
    dates = [parsedate_to_datetime(header.split(":", 1)[1]).astimezone(KST).isoformat()
             for header in headers if header.lower().startswith("date:")]
    return {"id": number, "dataset_url": dataset_url, "download_url": request,
            "retrieved_at_kst_from_http_date": dates[-1] if dates else None,
            "http_status": 200, "published_file_date": publication,
            "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes()).hexdigest(),
            "coordinate_reference": source_crs, "field_verified": False, "routing_eligible": False}


def coordinates(row, bounds_only=False):
    try:
        lon, lat = float(row["경도"]), float(row["위도"])
    except (ValueError, TypeError, KeyError):
        return None
    if not all(map(isfinite, (lon, lat))) or not (126 <= lon <= 128 and 37 <= lat <= 38):
        return None
    return (lon, lat)


def collect_crossings(directory, records, source, center_x, center_y):
    with (directory / "raw-22906.bin").open(encoding="cp949", newline="") as f:
        reader = DictReader(f)
        data = list(reader)
    features = []
    bad = []
    by_area = defaultdict(Counter)
    for row in data:
        coords = coordinates(row)
        if coords is None:
            bad.append(row["연번"])
            continue
        x, y = TO_METERS.transform(*coords)
        gap = hypot(x-center_x, y-center_y)
        by_area["seoul"][row["시군구명"]] += 1
        for boundary in RANGES:
            if gap <= boundary:
                by_area[f"{boundary}m"][row["시군구명"]] += 1
        if gap <= max(RANGES):
            properties = dict(row, record_number=row["연번"], field_verified=False, routing_eligible=False,
                              distance_to_wolgok_station_m=round(gap, 2))
            managed = records.get((row["시군구명"], row["횡단보도관리번호"]), [])
            if len(managed) == 1:
                properties.update(cross_reference_OA_23081=managed[0])
            features.append({"type": "Feature", "id": row["연번"],
                             "geometry": {"type": "Point", "coordinates": list(coords)},
                             "properties": properties})
    write_json(directory / "wolgok-official-crossings-3km.geojson",
               {"type": "FeatureCollection", "features": features,
                "metadata": dict(source, scope_meter=3000, center_longitude_latitude=CENTER,
                                 display_crs="EPSG:4326", distance_calculation_crs="EPSG:5186")})
    for key, counts in by_area.items():
        csv_save(directory / f"crossing-counts-{key}.csv",
                 [{"district": district, "count": count} for district, count in sorted(counts.items())])
    merged_counts = {}
    for boundary in RANGES:
        selected = [f["properties"] for f in features if f["properties"]["distance_to_wolgok_station_m"] <= boundary]
        linked = [p for p in selected if p.get("cross_reference_OA_23081")]
        signal_matches = sum(p["보행등유무"] == {"유": "Y", "무": "N"}.get(p["cross_reference_OA_23081"]["보행등유무"])
                             for p in linked)
        merged_counts[f"{boundary}m"] = {"crosswalks": sum(by_area[f"{boundary}m"].values()),
                                        "unique_OA_23081_management_ids": len(linked),
                                        "cross_reference_signal_agreement": signal_matches,
                                        "data_record_dates": dict(Counter(p["데이터기준일자"] for p in selected))}
    return data, {"rows": len(data), "valid_in_broad_Seoul_bbox": len(data) - len(bad), "invalid_reference_row_ids": bad,
                  "seoul_gu_records": len(by_area["seoul"]), "district_counts": {k: dict(v) for k, v in by_area.items()},
                  "data_record_dates": dict(Counter(r["데이터기준일자"] for r in data)),
                  "radius_checks": merged_counts}


def workbook_sheet(directory, number, sheet_index):
    path = directory / f"raw-{number}.bin"
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Broken ZIP for {number}")
    with path.open("rb") as f:
        work = load_workbook(f, read_only=True, data_only=True)
        return list(work.worksheets[sheet_index].values)


def collect_xlsx(directory):
    crossings = workbook_sheet(directory, "23081", 0)
    by_identity = defaultdict(list)
    for row in crossings[1:]:
        info = dict(zip(crossings[0], row))
        by_identity[(info["자치구"], info["횡단보도관리번호"])].append(info)
    sheet = workbook_sheet(directory, "22240", 1)
    road_segment_rows = [dict(zip(sheet[0][:14], row[:14])) for row in sheet[1:] if isinstance(row[0], int)]
    def pack_sidewalk(row):
        return dict(row, field_verified=False, coordinate_source=None, routing_eligible=False)
    selected = [pack_sidewalk(row) for row in road_segment_rows if row["관리기관"] in DISTRICTS
                and row["노선명"] in ROAD_NAMES]
    csv_save(directory / "wolgok-official-sidewalk-reference-no-coordinates.csv", selected)
    return by_identity, {"intersection_workbook_rows": len(crossings) - 1,
                         "intersection_crs_officially_unconfirmed": True,
                         "repeated_management_ids_within_district": sum(len(r) > 1 for r in by_identity.values()),
                         "sidewalk_workbook_rows": len(road_segment_rows),
                         "wolgok_named_road_candidates": len(selected),
                         "named_road_counts": dict(Counter(r["노선명"] for r in selected)),
                         "candidate_width_present": sum(isinstance(r["폭(m)"], (int, float)) for r in selected)}


def compare_candidate_crs(crossings, official_xy):
    samples_ll, samples_xy = [], []
    for row in crossings:
        ll = coordinates(row)
        matches = official_xy.get((row["시군구명"], row["횡단보도관리번호"]), [])
        if len(matches) == 1 and ll and matches[0]["X좌표"] is not None and matches[0]["Y좌표"] is not None:
            samples_ll.append(ll)
            samples_xy.append((float(matches[0]["X좌표"]), float(matches[0]["Y좌표"])))
    comparison = {}
    for candidate in (5174, 5179, 5181, 5186):
        tr = Transformer.from_crs(4326, candidate, always_xy=True)
        x, y = tr.transform(*zip(*samples_ll))
        distances = sorted(hypot(a - b, c - d) for a, c, (b, d) in zip(x, y, samples_xy))
        comparison[f"EPSG:{candidate}"] = {
            "paired_median_m": round(median(distances), 3),
            "pairs_within_20_m": sum(d <= 20 for d in distances),
            "pairs_compared": len(distances),
        }
    return comparison


def existing_precision(repo, center_x, center_y):
    path = repo / "donghaeng-nav/dist/data/precision/precision-map.geojson"
    source = json.loads(path.read_text(encoding="utf8"))
    center = Point(center_x, center_y)
    counts, invalid = Counter(), Counter()
    by_radius = defaultdict(Counter)
    for feature in source["features"]:
        key = feature["properties"]["kind"]
        if key not in {"sidewalk", "building"}:
            continue
        geom = shape(feature["geometry"])
        counts[f"{key}:{geom.geom_type}"] += 1
        if not geom.is_valid:
            invalid[key] += 1
            continue
        meters = transform(TO_METERS.transform, geom)
        for radius in RANGES:
            if meters.distance(center) <= radius:
                by_radius[f"{radius}m"][key] += 1
    return {"file": str(path.relative_to(repo)), "sha256": sha256(path.read_bytes()).hexdigest(),
            "source_as_of": source["metadata"]["as_of"], "declared_source_crs": source["metadata"]["source_crs"],
            "crs_verification": source["metadata"]["crs_verification"]["status"],
            "source": source["metadata"]["source_url"], "existing_records_geometry": dict(counts),
            "valid_geometry_touching_circle": {k: dict(v) for k, v in by_radius.items()},
            "invalid_excluded": dict(invalid), "reacquired": False, "routing_eligible": False, "field_verified": False}


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("repository", type=Path)
    arg.add_argument("directory", type=Path)
    args = arg.parse_args()
    root = "https://data.seoul.go.kr/dataList/"
    dir = args.directory
    found = {
        "22906": source_evidence(dir, "22906", "2026-08-10", root + "OA-22906/S/1/datasetView.do",
                                 "Original longitude and latitude columns; WGS84 projection used to calculate local distance."),
        "23081": source_evidence(dir, "23081", "2026-09-07 (file dated 2026-08-24)",
                                 root + "OA-23081/F/1/datasetView.do", None),
        "22240": source_evidence(dir, "22240", "2026-09-15 (reference 2025-12-31)",
                                 root + "OA-22240/F/1/datasetView.do", None),
    }
    historical_request_path = args.repository / "research/accessibility/round2/acquired-2026-10-31/request-log.json"
    historical = json.loads(historical_request_path.read_text(encoding="utf8"))
    for row in found.values():
        matches = [r for r in historical if r.get("sha256") == row["sha256"] and f"OA-{row['id']}" in (r.get("request_body") or "")]
        row["matches_previous_raw_sha256"] = bool(matches)
        row["previous_retrieval_at_kst"] = matches[0]["requested_at_kst"] if matches else None
    center_x, center_y = TO_METERS.transform(*CENTER)
    official_xy, spreadsheet_report = collect_xlsx(dir)
    crosswalks, crosswalk_report = collect_crossings(dir, official_xy, found["22906"], center_x, center_y)
    report = {"sources": found, "scope": {"center_longitude_latitude": CENTER, "radii_meter": RANGES,
                                        "metric_crs": "EPSG:5186", "field_verified": False},
              "crosswalks": crosswalk_report, "spreadsheets": spreadsheet_report,
              "crossing_xy_crs_hypothesis_not_used_to_map": compare_candidate_crs(crosswalks, official_xy),
              "existing_precision": existing_precision(args.repository, center_x, center_y)}
    write_json(dir / "seoul-official-evidence.json", report)
    print(json.dumps({"crosswalks": crosswalk_report["radius_checks"], "spreadsheets": spreadsheet_report,
                      "existing_precision": report["existing_precision"]["valid_geometry_touching_circle"],
                      "crs_hypothesis": report["crossing_xy_crs_hypothesis_not_used_to_map"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
