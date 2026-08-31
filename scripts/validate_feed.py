#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

path = Path(sys.argv[1] if len(sys.argv) > 1 else "feed/latest.json")
data = json.loads(path.read_text(encoding="utf-8"))
required = {"schema_version", "generated_at", "timezone", "window", "source_health", "candidates"}
missing = required - data.keys()
if missing:
    raise SystemExit(f"missing top-level fields: {sorted(missing)}")
ids = set()
for index, item in enumerate(data["candidates"]):
    for field in ("candidate_id", "title", "source", "source_priority", "source_type", "url", "fetch_time"):
        if field not in item:
            raise SystemExit(f"candidate {index} missing {field}")
    if item["candidate_id"] in ids:
        raise SystemExit(f"duplicate candidate_id: {item['candidate_id']}")
    ids.add(item["candidate_id"])
    if urlparse(item["url"]).scheme not in {"http", "https"}:
        raise SystemExit(f"invalid candidate URL: {item['url']}")
print(f"valid feed: {len(data['candidates'])} candidates")
