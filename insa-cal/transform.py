#!/usr/bin/env python3
"""Telecharge l'ICS INSA et reformate les SUMMARY en 'TYPE - Matiere - Salle'."""
import json
import os
import re
import urllib.request
from pathlib import Path

ICS_URL = os.environ.get(
    "ICS_URL",
    "https://ade-outils.insa-lyon.fr/ADE-Cal:~sbarthes!2025-2026:28dd2a01261b61d6cc12695b67e321eb190383b3",
)

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "mappings.json").read_text(encoding="utf-8"))
MATIERE = CFG.get("matiere", {})
FREE_RULES = [(re.compile(r["match"]), r["title"]) for r in CFG.get("free_form_rules", [])]
TYPES = {"CM", "TD", "TP", "EV", "EDT", "DS", "CC", "EX"}

INSA_RE = re.compile(
    r"::([A-Z]{2,5}[A-Z0-9]?)(?:-[A-Z0-9-]+)?:(CM|TD|TP|EV|EDT|DS|CC|EX)::"
)


def unfold(text: str) -> str:
    return re.sub(r"\r?\n[ \t]", "", text)


def fold(line: str) -> str:
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    chunks = [b[:75]]
    rest = b[75:]
    while rest:
        chunks.append(b" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(c.decode("utf-8", errors="ignore") for c in chunks)


def clean_location(loc: str) -> str:
    if not loc:
        return "?"
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    cleaned = []
    for raw in parts:
        x = re.sub(r"\s*\([^)]*\)\s*", " ", raw).strip()
        x = re.sub(r"\s+", " ", x)
        if " - " in x:
            segs = [s.strip() for s in x.split(" - ") if s.strip()]
            x = segs[1] if len(segs) >= 2 else segs[0]
        x = re.sub(r"^(Amphi|Salle|Labo|Room)\s+", "", x, flags=re.IGNORECASE)
        first = x.split()[0] if x.split() else x
        cleaned.append(first)
    seen, result = set(), []
    for p in cleaned:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return " / ".join(result) if result else "?"


def transform_summary(summary: str, location: str):
    m = INSA_RE.search(summary)
    salle = clean_location(location)
    if m:
        mat_code = m.group(1)
        typ = m.group(2)
        mat = MATIERE.get(mat_code, mat_code)
        return f"{typ} - {mat} - {salle}", True
    for pat, title in FREE_RULES:
        if pat.search(summary):
            return f"{title} - {salle}" if salle != "?" else title, True
    return summary, False


def transform_block(block):
    summary_idx = None
    location = ""
    for i, line in enumerate(block):
        if line.startswith("SUMMARY"):
            summary_idx = i
        elif line.startswith("LOCATION"):
            _, _, val = line.partition(":")
            location = val
    if summary_idx is None:
        return block
    _, _, old = block[summary_idx].partition(":")
    new, _ = transform_summary(old, location)
    block[summary_idx] = f"SUMMARY:{new}"
    return block


def main():
    raw = urllib.request.urlopen(ICS_URL, timeout=60).read().decode("utf-8", errors="replace")
    raw = unfold(raw)
    out, block, n = [], None, 0
    for line in raw.splitlines():
        if line.startswith("BEGIN:VEVENT"):
            block = [line]
            n += 1
        elif line.startswith("END:VEVENT") and block is not None:
            block.append(line)
            out.extend(transform_block(block))
            block = None
        elif block is not None:
            block.append(line)
        else:
            out.append(line)
    folded = "\r\n".join(fold(l) for l in out) + "\r\n"
    (ROOT / "calendar.ics").write_text(folded, encoding="utf-8")
    print(f"OK: {n} evenements ecrits.")


if __name__ == "__main__":
    main()
