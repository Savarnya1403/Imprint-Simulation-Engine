"""Corpus ingestion for the context layer.

The curated atlas is the inspectable core. This module lets the corpus grow
without pretending the additions are equally trustworthy: every chunk carries
its source, year, geography and confidence label.

Supported: .txt, .md, .csv, .json, .jsonl, .html/.htm, and .pdf when `pypdf`
is installed. A PDF without `pypdf` fails loudly instead of silently producing
garbage.

CLI:
    python -m app.ingest path/to/report.pdf --org NITI --year 2024 --dimension income
    python -m app.ingest --list
    python -m app.ingest --stats
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

DATA = Path(__file__).parent / "data"
CORPUS = DATA / "corpus"
CHUNKS = CORPUS / "chunks.jsonl"
REGISTRY = CORPUS / "sources.json"

DIMENSIONS = {
    "geography", "income", "consumption", "caste", "religion", "gender", "digital",
    "supply", "festival", "jobs", "education", "norms", "beauty", "status",
    "policy", "category", "document",
}
CONFIDENCE = {"high", "medium", "low", "modelled"}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s[:64] or "ingested"


def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", str(text or ""))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunks(text: str, size: int = 1400, overlap: int = 160) -> list[str]:
    text = _clean(text)
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out = []
    i = 0
    while i < len(text):
        end = min(len(text), i + size)
        if end < len(text):
            cut = max(text.rfind("\n\n", i + size // 2, end), text.rfind(". ", i + size // 2, end))
            if cut > i + 200:
                end = cut + 1
        out.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(i + 1, end - overlap)
    return [c for c in out if len(c) > 40]


def _strip_html(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?is)</(p|div|h[1-6]|li|tr)>", "\n", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"&nbsp;", " ", raw)
    raw = re.sub(r"&amp;", "&", raw)
    raw = re.sub(r"&lt;", "<", raw)
    raw = re.sub(r"&gt;", ">", raw)
    raw = re.sub(r"&quot;", '"', raw)
    raw = re.sub(r"&#39;", "'", raw)
    return _clean(raw)


def _read_pdf(path: Path) -> str:
    try:
        import pypdf  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "PDF ingestion needs pypdf. Install it with `pip install pypdf`, or convert the "
            "file to text first and pass --text-file."
        ) from exc
    reader = pypdf.PdfReader(str(path))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages)


def _csv_chunks(path: Path, max_rows: int = 120) -> list[str]:
    text = path.read_text(errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header = rows[0]
    out = []
    for start in range(1, len(rows), max_rows):
        block = rows[start:start + max_rows]
        lines = [" | ".join(header)] + [" | ".join(r) for r in block]
        out.append("\n".join(lines))
    return out


def _json_chunks(path: Path) -> list[str]:
    text = path.read_text(errors="replace")
    try:
        data = json.loads(text)
    except Exception:
        return [ln for ln in text.splitlines() if ln.strip()]
    records: list[Any]
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        for key in ("records", "items", "rows", "data", "results"):
            if isinstance(data.get(key), list):
                records = data[key]
                break
        else:
            records = [data]
    else:
        records = [data]
    out = []
    for rec in records[:400]:
        if isinstance(rec, dict):
            out.append("\n".join(f"{k}: {v}" for k, v in rec.items() if v not in (None, "")))
        else:
            out.append(str(rec))
    return [c for c in out if c.strip()]


def _load_registry() -> list[dict]:
    if REGISTRY.exists():
        try:
            data = json.loads(REGISTRY.read_text())
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and isinstance(data.get("sources"), list):
                return data["sources"]
        except Exception:
            pass
    return []


def _save_registry(rows: list[dict]) -> None:
    CORPUS.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps({"version": "2026.11", "sources": rows}, indent=1, ensure_ascii=False) + "\n")


def _read_existing_ids() -> set[str]:
    ids: set[str] = set()
    if not CHUNKS.exists():
        return ids
    for line in CHUNKS.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
            if rec.get("id"):
                ids.add(rec["id"])
        except Exception:
            continue
    return ids


def ingest_text(
    text: str,
    title: str,
    source_id: str | None = None,
    org: str = "Uploaded document",
    url: str = "",
    year: int | None = None,
    geo: str = "India",
    dimension: str = "document",
    tags: Iterable[str] | None = None,
    confidence: str = "medium",
    chunk_chars: int = 1400,
) -> dict:
    """Append one document to the corpus. Returns counts and the chunk ids."""
    text = _clean(text)
    if len(text) < 40:
        raise ValueError("Document is too short to ingest (need at least 40 characters).")
    dimension = dimension if dimension in DIMENSIONS else "document"
    confidence = confidence if confidence in CONFIDENCE else "medium"
    tag_list = sorted({str(t).strip().lower().replace(" ", "-") for t in (tags or []) if str(t).strip()})
    sid = source_id or f"doc-{_slug(title)}-{hashlib.sha1(text.encode()).hexdigest()[:6]}"
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    pieces = _chunks(text, size=max(300, min(6000, int(chunk_chars))))
    existing = _read_existing_ids()
    written = []
    CORPUS.mkdir(parents=True, exist_ok=True)
    with CHUNKS.open("a") as fh:
        for i, piece in enumerate(pieces):
            cid = f"{sid}-c{i:03d}"
            if cid in existing:
                continue
            rec = {
                "id": cid,
                "source_id": sid,
                "title": title if len(pieces) == 1 else f"{title} · part {i + 1}",
                "text": piece,
                "source": org,
                "url": url,
                "year": year,
                "geo": geo,
                "dimension": dimension,
                "tags": tag_list,
                "confidence": confidence,
                "chars": len(piece),
                "ingested_at": now,
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written.append(cid)

    rows = _load_registry()
    if not any(r.get("id") == sid for r in rows):
        rows.append({
            "id": sid, "org": org, "title": title, "year": year, "url": url,
            "type": "document", "geo": geo, "dimension": dimension,
            "confidence": confidence, "ingested_at": now, "chunks": len(written),
        })
    else:
        for r in rows:
            if r.get("id") == sid:
                r["chunks"] = int(r.get("chunks", 0)) + len(written)
    _save_registry(rows)
    _clear_caches()
    return {
        "source_id": sid,
        "title": title,
        "chunks_written": len(written),
        "chunks_total": len(pieces),
        "chars": len(text),
        "duplicate_chunks": max(0, len(pieces) - len(written)),
    }


def ingest_file(path: str | Path, **kwargs) -> dict:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(str(p))
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(p)
        extra: list[str] = []
    elif suffix in (".html", ".htm"):
        text = _strip_html(p.read_text(errors="replace"))
        extra = []
    elif suffix == ".csv":
        extra = _csv_chunks(p)
        text = "\n\n".join(extra)
    elif suffix in (".json",):
        extra = _json_chunks(p)
        text = "\n\n".join(extra)
    elif suffix in (".jsonl", ".ndjson"):
        extra = [ln for ln in p.read_text(errors="replace").splitlines() if ln.strip()]
        text = "\n\n".join(extra)
    elif suffix in (".txt", ".md", ".markdown", ".text", ""):
        text = p.read_text(errors="replace")
        extra = []
    else:
        raise ValueError(f"Unsupported file type: {suffix or '(none)'}. Use txt, md, csv, json, jsonl, html or pdf.")
    kwargs.setdefault("title", p.stem.replace("-", " ").replace("_", " ").title())
    if kwargs.get("year") is None:
        m = re.search(r"(19|20)\d{2}", p.name)
        if m:
            kwargs["year"] = int(m.group(0))
    out = ingest_text(text, **kwargs)
    out["file"] = str(p)
    out["format"] = suffix or "text"
    return out


def stats() -> dict:
    chunks = []
    if CHUNKS.exists():
        for line in CHUNKS.read_text(errors="replace").splitlines():
            try:
                chunks.append(json.loads(line))
            except Exception:
                continue
    registry = _load_registry()
    dims: dict[str, int] = {}
    for c in chunks:
        dims[c.get("dimension", "document")] = dims.get(c.get("dimension", "document"), 0) + 1
    return {
        "chunks": len(chunks),
        "sources": len(registry),
        "chars": sum(int(c.get("chars") or len(c.get("text", ""))) for c in chunks),
        "dimensions": dict(sorted(dims.items(), key=lambda kv: -kv[1])),
        "registry": registry,
        "path": str(CHUNKS),
        "note": (
            "Ingested chunks are retrievable context, not automatically verified facts. "
            "Their confidence label and source are shown wherever they are cited."
        ),
    }


def clear() -> dict:
    for p in (CHUNKS, REGISTRY):
        if p.exists():
            p.unlink()
    _clear_caches()
    return {"cleared": True}


def _clear_caches() -> None:
    try:
        from . import atlas
        for name in ("corpus_chunks", "all_nodes", "sources", "dimensions", "coverage", "audit", "stats_for_ui"):
            fn = getattr(atlas, name, None)
            if fn is not None and hasattr(fn, "cache_clear"):
                fn.cache_clear()
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ingest public documents into the Imprint context corpus.")
    ap.add_argument("files", nargs="*", help="Files to ingest")
    ap.add_argument("--title")
    ap.add_argument("--source-id")
    ap.add_argument("--org", default="Uploaded document")
    ap.add_argument("--url", default="")
    ap.add_argument("--year", type=int)
    ap.add_argument("--geo", default="India")
    ap.add_argument("--dimension", default="document", choices=sorted(DIMENSIONS))
    ap.add_argument("--tags", default="", help="Comma-separated tags")
    ap.add_argument("--confidence", default="medium", choices=sorted(CONFIDENCE))
    ap.add_argument("--text-file", help="Read plain text from this file instead of the positional path")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--clear", action="store_true", help="Delete the ingested corpus (not the curated atlas)")
    args = ap.parse_args(argv)

    if args.clear:
        print(json.dumps(clear(), indent=1))
        return 0
    if args.stats:
        print(json.dumps(stats(), indent=1, ensure_ascii=False))
        return 0
    if args.list:
        for r in _load_registry():
            print(f"{r.get('id','?'):40s} {r.get('year','')!s:5s} {r.get('org','')} · {r.get('chunks',0)} chunks")
        return 0

    kwargs: dict[str, Any] = dict(
        org=args.org, url=args.url, year=args.year, geo=args.geo,
        dimension=args.dimension, confidence=args.confidence,
        tags=[t for t in args.tags.split(",") if t.strip()],
        source_id=args.source_id,
    )
    if args.title:
        kwargs["title"] = args.title

    targets: list[str] = list(args.files)
    if args.text_file:
        targets.append(args.text_file)
    if not targets:
        ap.print_help()
        return 2
    total = 0
    for f in targets:
        try:
            res = ingest_file(f, **kwargs)
            total += res["chunks_written"]
            print(json.dumps(res, indent=1))
        except Exception as exc:
            print(f"failed: {f}: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(f"ingested {total} chunks into {CHUNKS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
