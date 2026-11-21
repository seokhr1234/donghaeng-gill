"""Extract Overture building records from one indexed shard over verified HTTPS ranges."""
import hashlib
import io
import json
import pathlib
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import pyarrow.compute as pc
import pyarrow.parquet as pq
from shapely import from_wkb
from shapely.geometry import box, mapping

SCOPE = (127.28, 36.59, 127.39, 36.67)
CORE = (127.315, 36.61, 127.35, 36.64)
RELEASE = "2026-11-18.0"
START = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
ROOT = pathlib.Path(".")
LOG = ROOT / "overture-building-range-requests.jsonl"

def overlap_filter(box_coords):
    west, south, east, north = box_coords
    return (
        (pc.field("bbox", "xmin") <= east) & (pc.field("bbox", "xmax") >= west)
        & (pc.field("bbox", "ymin") <= north) & (pc.field("bbox", "ymax") >= south)
    )

class RemoteRange(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position = url, size, 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        self.position = (0, self.position, self.size)[whence] + offset
        if self.position < 0:
            raise ValueError("negative file offset")
        return self.position

    def read(self, n=-1):
        if self.position >= self.size or n == 0:
            return b""
        pos = self.position
        end = min(self.size, pos + n) if n >= 0 else self.size
        if end - pos > 64 * 1024**2:
            raise ValueError("remote range exceeds guarded per-request limit")
        area = f"bytes={pos}-{end-1}"
        options = {"Range": area, "User-Agent": "Donghaeng public data research", "Accept-Encoding": "identity"}
        with urllib.request.urlopen(urllib.request.Request(self.url, headers=options), timeout=45) as reply:
            claimed = reply.headers.get("Content-Range")
            if reply.status != 206 or claimed != f"bytes {pos}-{end-1}/{self.size}":
                raise IOError(f"request {area}: received {reply.status} Content-Range {claimed!r}")
            raw = reply.read(end-pos+1)
            if len(raw) != end-pos:
                raise IOError(f"request {area}: byte count mismatch")
            metadata = {
                "source_url": self.url, "http_status": reply.status, "range": area,
                "content_range": claimed, "etag": reply.headers.get("ETag"),
                "last_modified": reply.headers.get("Last-Modified"),
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            }
        with LOG.open("a") as log:
            print(json.dumps(metadata, ensure_ascii=False), file=log)
        self.position = end
        return raw

index = pq.read_table(ROOT / "stac-collections.body")
matching = index.filter((pc.field("collection") == "building") & (pc.field("type") == "Feature") & overlap_filter(SCOPE))
assert matching.num_rows == 1, "expected one building shard intersecting this fixed study box"
asset = matching.column("assets")[0].as_py()["aws"]
url, size = asset["href"], asset["file:size"]
LOG.write_text("")
remote = RemoteRange(url, size)
parquet = pq.ParquetFile(remote, pre_buffer=False)
meta = parquet.metadata
geo_metadata = json.loads(parquet.schema_arrow.metadata[b"geo"])
position = {meta.schema.column(i).path: i for i in range(meta.num_columns)}
candidate_groups = []
for i in range(meta.num_row_groups):
    rowgroup = meta.row_group(i)
    stats = {k:rowgroup.column(position["bbox." + k]).statistics for k in ("xmin","ymin","xmax","ymax")}
    w,s,e,n = SCOPE
    if not all(st and st.has_min_max for st in stats.values()) or (
        stats["xmin"].min <= e and stats["xmax"].max >= w
        and stats["ymin"].min <= n and stats["ymax"].max >= s
    ):
        candidate_groups.append(i)
print("row groups", meta.num_row_groups, "matching", candidate_groups, flush=True)
tables = []
for i in candidate_groups:
    table = parquet.read_row_group(i, use_threads=False).filter(overlap_filter(SCOPE))
    tables.append(table)
    print("row group", i, "rows candidate", table.num_rows, flush=True)
import pyarrow as pa
subset = pa.concat_tables(tables)
study, core = box(*SCOPE), box(*CORE)
features, held, kept_idx = [], [], []
for i, row in enumerate(subset.to_pylist()):
    geom = from_wkb(row.pop("geometry"))
    if geom is None or geom.is_empty or geom.geom_type not in ("Polygon","MultiPolygon"):
        held.append({"id": row["id"], "reason": "non-building geometry"})
        continue
    if not geom.is_valid:
        held.append({"id": row["id"], "reason": "invalid geometry"})
        continue
    if not geom.intersects(study):
        continue
    kept_idx.append(i)
    row["intersects_core"] = geom.intersects(core)
    features.append({"type": "Feature", "id": row["id"], "geometry": mapping(geom), "properties":row})
assert len(features) == len({x["id"] for x in features})
def sources(items):
    return dict(Counter(s for f in items for s in set((t.get("dataset") for t in (f["properties"].get("sources") or []))) if s))
layers = {"type":"FeatureCollection","features":features}
(ROOT / "overture-buildings-study.geojson").write_text(json.dumps(layers,ensure_ascii=False,separators=(",",":"))+"\n")
pq.write_table(subset.take(kept_idx), ROOT / "overture-buildings-study.parquet", compression="zstd")
summary = {
    "release": RELEASE, "retrieved_at_kst": START, "completed_at_kst":datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
    "source_shard": url, "source_shard_bytes": size, "source_index":"https://stac.overturemaps.org/2026-11-18.0/collections.parquet",
    "geo_metadata": geo_metadata, "scope": SCOPE, "core": CORE,
    "source_row_groups": meta.num_row_groups, "searched_row_groups": candidate_groups,
    "candidate_bbox_records": subset.num_rows, "study_count": len(features),
    "core_count": sum(f["properties"]["intersects_core"] for f in features),
    "upstream_rows_study": sources(features),
    "upstream_rows_core": sources(f for f in features if f["properties"]["intersects_core"]),
    "held": held,
    "range_count": len(LOG.read_text().splitlines()),
}
for artifact in ("overture-buildings-study.geojson", "overture-buildings-study.parquet"):
    data=(ROOT / artifact).read_bytes()
    summary[artifact]={"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
(ROOT / "overture-buildings-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,default=str),flush=True)
