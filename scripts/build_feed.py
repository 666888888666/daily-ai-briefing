#!/usr/bin/env python3
"""Build a normalized public candidate feed using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

USER_AGENT = "daily-ai-briefing/1.0 (+https://github.com/666888888666/daily-ai-briefing)"


def clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def parse_time(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def first_text(node: ET.Element, names: Iterable[str]) -> str:
    wanted = set(names)
    for child in node.iter():
        if child.tag.split("}")[-1] in wanted and child.text:
            return child.text
    return ""


def parse_xml(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    entries = [n for n in root.iter() if n.tag.split("}")[-1] in {"item", "entry"}]
    output = []
    for entry in entries:
        link = first_text(entry, ["link", "guid"])
        if not link:
            for child in entry.iter():
                if child.tag.split("}")[-1] == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        output.append({
            "title": first_text(entry, ["title"]),
            "url": link,
            "published_at": first_text(entry, ["pubDate", "published", "updated", "date"]),
            "raw_content": first_text(entry, ["description", "summary", "content", "encoded"]),
            "author": first_text(entry, ["author", "creator", "name"]),
        })
    return output


def walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        has_content = any(k in value for k in ("title", "text", "content", "summary", "description"))
        has_identity = any(k in value for k in ("url", "link", "id", "tweetId", "videoId"))
        if has_content and has_identity:
            yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def parse_json(payload: bytes) -> list[dict[str, Any]]:
    data = json.loads(payload.decode("utf-8-sig"))
    output = []
    for item in walk_json(data):
        title = item.get("title") or item.get("text") or item.get("summary") or item.get("content")
        url = item.get("url") or item.get("link")
        if not url and item.get("tweetId"):
            handle = item.get("username") or item.get("handle") or "i"
            url = f"https://x.com/{handle}/status/{item['tweetId']}"
        if not url and item.get("videoId"):
            url = f"https://www.youtube.com/watch?v={item['videoId']}"
        output.append({
            "title": title,
            "url": url or "",
            "published_at": item.get("published_at") or item.get("publishedAt") or item.get("created_at") or item.get("createdAt") or item.get("date"),
            "raw_content": item.get("content") or item.get("text") or item.get("summary") or item.get("description") or title,
            "author": item.get("author") or item.get("name") or item.get("username") or "",
        })
    return output


def normalize(item: dict[str, Any], source: dict[str, Any], fetched_at: str) -> dict[str, Any] | None:
    title, url = clean(item.get("title")), str(item.get("url") or "").strip()
    if not title or not url:
        return None
    published = parse_time(item.get("published_at"))
    key = f"{source['id']}|{url}|{title.lower()}"
    return {
        "candidate_id": hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
        "title": title,
        "source": source["name"],
        "source_id": source["id"],
        "source_priority": source["priority"],
        "source_type": source["source_type"],
        "company": "",
        "product": "",
        "url": url,
        "publish_time": published,
        "raw_content": clean(item.get("raw_content"))[:4000],
        "author": clean(item.get("author")),
        "language": "unknown",
        "country": "unknown",
        "topic": "unclassified",
        "fetch_time": fetched_at,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="sources/feeds.json")
    parser.add_argument("--output", default="feed/latest.json")
    parser.add_argument("--now", help="ISO-8601 UTC timestamp for reproducible runs")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    fetched_at = now.isoformat().replace("+00:00", "Z")
    cutoff = now - timedelta(hours=int(config.get("lookback_hours", 48)))
    candidates, health = [], []

    for source in config["sources"]:
        try:
            payload = fetch(source["url"], int(config.get("timeout_seconds", 25)))
            items = parse_json(payload) if source["format"] == "json" else parse_xml(payload)
            accepted = 0
            for item in items:
                candidate = normalize(item, source, fetched_at)
                if not candidate:
                    continue
                published = parse_time(candidate["publish_time"])
                if published and datetime.fromisoformat(published.replace("Z", "+00:00")) < cutoff:
                    continue
                candidates.append(candidate)
                accepted += 1
            health.append({"source_id": source["id"], "status": "ok", "items": accepted, "fetched_at": fetched_at})
        except Exception as exc:  # one broken source must not break the public feed
            health.append({"source_id": source["id"], "status": "error", "items": 0, "fetched_at": fetched_at, "error": f"{type(exc).__name__}: {exc}"[:300]})

    unique = {}
    for item in candidates:
        key = item["url"].split("#", 1)[0].rstrip("/").lower() or item["title"].lower()
        current = unique.get(key)
        if current is None or item["source_priority"] < current["source_priority"]:
            unique[key] = item
    ordered = sorted(unique.values(), key=lambda x: x.get("publish_time") or "", reverse=True)
    result = {
        "schema_version": "1.0",
        "generated_at": fetched_at,
        "timezone": "Asia/Shanghai",
        "window": {"lookback_hours": int(config.get("lookback_hours", 48)), "cutoff_utc": cutoff.isoformat().replace("+00:00", "Z")},
        "notice": "Candidate feed only. Every item must be verified before publication.",
        "source_health": health,
        "candidates": ordered,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(ordered)} candidates from {len(config['sources'])} sources to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
