"""Build the map supplement from the reviewed 2026-11-20 Seoul collection."""

import csv
import json
from collections import Counter
from html import unescape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research/accessibility/seoul-rest-2026-11-20/derived"
OUTPUT = ROOT / "donghaeng-nav/dist/data/accessibility/seoul/seoul-rest-update.json"
GANGBUK_NOTICE = "https://www.snsgangbuk.com/sub/notice.html?type=view&bsNo=3404&page=1"


def read_json(name):
    return json.loads((RESEARCH / name).read_text(encoding="utf-8"))


def read_rows(name):
    with (RESEARCH / name).open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def assert_ids(rows, count):
    if len(rows) != count or len(set(rows)) != count or not all(rows):
        raise ValueError("Reviewed facility counts or IDs have changed")


def main():
    osm = read_json("osm-rest.geojson")["features"]
    extraction = read_json("osm-extraction.json")
    libraries = read_json("seoul-public-libraries-2025.geojson")["features"]
    cold_shelters = read_rows("gangbuk-cold-shelters.csv")
    assert_ids([f["properties"]["osm_id"] for f in osm], 4720)
    assert_ids([f["properties"]["library_id"] for f in libraries], 214)
    assert_ids([r["연번"] for r in cold_shelters], 96)
    if any(f["properties"]["field_verified"] is not False for f in osm + libraries):
        raise ValueError("Map supplement must use unverified registered locations")
    kinds = Counter(f["properties"]["kind"] for f in osm)
    if dict(kinds) != extraction["counts"]:
        raise ValueError("OSM extract categories no longer match the review")
    osm_rows = []
    for feature in osm:
        p = feature["properties"]
        osm_rows.append({
            "id": p["osm_id"], "kind": p["kind"], "coordinate": feature["geometry"]["coordinates"],
            "district": p["district"], "edited": p["last_osm_edit"], "tags": p["osm_tags"],
        })
    library_rows = []
    for feature in libraries:
        p = feature["properties"]
        library_rows.append({
            "id": p["library_id"], "name": p["name"], "address": unescape(p["address"]), "district": p["district"],
            "hours": unescape(p["opening_hours_reported"]), "regularClosure": unescape(p["regular_closure_reported"]),
            "coordinate": feature["geometry"]["coordinates"],
        })
    cold_rows = [{
        "id": r["연번"], "neighborhood": r["행정동"], "name": r["쉼터명"], "address": r["소재지"],
        "kind": r["시설구분"], "hours": r["운영시간"],
        **({"hoursConflict": "구청 공지 본문은 토요일 09:00~17:00로 안내합니다. 방문 전 확인해 주세요."}
           if r["쉼터명"] == "강북웰빙스포츠센터" else {}),
    } for r in cold_shelters]
    data = {
        "version": 1,
        "routing_eligible": False,
        "field_verified": False,
        "retrievedDate": extraction["retrieved_date"],
        "osmSnapshot": extraction["source_as_of"],
        "osmSnapshotLabel": "2026-11-20 06:22 KST",
        "libraryYear": 2025,
        "librarySource": "https://www.libsta.go.kr/libsta/statistics/public/stat",
        "coldShelterPeriod": ["2026-11-15", "2027-03-15"],
        "coldShelterSource": GANGBUK_NOTICE,
        "osm": osm_rows,
        "libraries": library_rows,
        "coldShelters": cold_rows,
    }
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
