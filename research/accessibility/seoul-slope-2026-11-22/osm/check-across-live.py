from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

url = "https://api.openstreetmap.org/api/0.6"
features = json.loads(gzip.decompress(Path("osm-seoul-incline-tagged.geojson.gz").read_bytes()))["features"]
features = [f for f in features if "incline:across" in f["properties"]["slope_like_tags"]]
ids = ",".join(f["id"].split("/")[1] for f in features)
read = lambda endpoint: urlopen(Request(endpoint, headers={"User-Agent": "Donghaenggil data audit (OSM published inclines)", "Accept": "application/json"}), timeout=15)
with read(url + "/ways.json?ways=" + ids) as result:
    byte = result.read()
    ways = json.loads(byte)["elements"]
    ways_status = result.status
sets = Counter(way["changeset"] for way in ways)
assoc = []
for cs, count in sets.most_common():
    try:
        with read(url + f"/changeset/{cs}.json") as result:
            resp = result.read()
            if len(resp) > 500000:
                continue
            meta = json.loads(resp)["changeset"]
            tags = meta.get("tags", {})
            assoc.append({"id": cs, "count": count, "created_at": meta["created_at"], "source": tags.get("source"),
                          "comment": tags.get("comment"), "source_url": tags.get("source:url"),
                          "created_by": tags.get("created_by"), "http_status": result.status, "sha256": hashlib.sha256(resp).hexdigest()})
    except OSError as e:
        assoc.append({"id": cs, "count": count, "error": type(e).__name__})
    time.sleep(.3)
raw_by_id = {f["id"]: f["properties"]["slope_like_tags"] for f in features}
details = []
for w in ways:
    tags = w["tags"]
    key = f"way/{w['id']}"
    details.append({
        "osm_id": key, "version": w["version"], "registered_incline": tags.get("incline"), "registered_incline_across": tags.get("incline:across"),
        "slope_tag_agreement": all(tags.get(k) == v for k, v in raw_by_id[key].items()),
        "source": tags.get("source"), "source_incline": tags.get("source:incline"), "survey_date": tags.get("survey:date"),
        "source_url": "https://www.openstreetmap.org/" + key, "changeset": w["changeset"],
    })
summary = {
    "retrieved_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
    "live_ways_status": ways_status, "live_ways_sha256": hashlib.sha256(byte).hexdigest(),
    "checked_ways": len(ways), "all_slope_tag_agreement": all(row["slope_tag_agreement"] for row in details),
    "changeset_results": assoc, "public_way_records": details, "field_verified": False,
}
Path("osm-across-live-provenance.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "public_way_records"}, ensure_ascii=False))
