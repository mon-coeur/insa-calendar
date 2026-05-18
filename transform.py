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
DEFAULT_LOC = CFG.get("matiere_default_location", {})
HIDE_IF_OVERLAP = CFG.get("hide_if_overlap", {})
FREE_RULES = [(re.compile(r["match"]), r["title"]) for r in CFG.get("free_form_rules", [])]

INSA_RE = re.compile(
    r"::([A-Z]{2,5}[A-Z0-9]?)(?:-[A-Z0-9-]+)?:(CM|TD|TP|EV|EDT|DS|CC|EX)::"
)


def unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text)


def fold(line):
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    chunks = [b[:75]]
    rest = b[75:]
    while rest:
        chunks.append(b" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(c.decode("utf-8", errors="ignore") for c in chunks)


def clean_location(loc):
    if not loc:
        return ""
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
        if first:
            cleaned.append(first)
    seen, result = set(), []
    for p in cleaned:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return " / ".join(result)


def join_parts(*parts):
    return " - ".join(p for p in parts if p)


def extract_dtstart(block):
    for line in block:
        if line.startswith("DTSTART"):
            _, _, val = line.partition(":")
            return val.strip()
    return None


def extract_mat_code(block):
    for line in block:
        if line.startswith("SUMMARY"):
            _, _, s = line.partition(":")
            m = INSA_RE.search(s)
            if m:
                return m.group(1)
    return None


def transform_summary(summary, location):
    m = INSA_RE.search(summary)
    salle = clean_location(location)
    if m:
        mat_code = m.group(1)
        typ = m.group(2)
        mat = MATIERE.get(mat_code, mat_code)
        if not salle:
            salle = DEFAULT_LOC.get(mat_code, "")
        return join_parts(typ, mat, salle), True
    for pat, title in FREE_RULES:
        if pat.search(summary):
            return join_parts(title, salle), True
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

    # Pass 1 : parse en blocs
    pre, blocks, post = [], [], []
    cur = None
    seen_first_event = False
    for line in raw.splitlines():
        if line.startswith("BEGIN:VEVENT"):
            cur = [line]
            seen_first_event = True
        elif line.startswith("END:VEVENT") and cur is not None:
            cur.append(line)
            blocks.append(cur)
            cur = None
        elif cur is not None:
            cur.append(line)
        elif not seen_first_event:
            pre.append(line)
        else:
            post.append(line)

    # Pass 2 : index dtstart -> set des codes matiere
    slot_codes = {}
    for b in blocks:
        ds = extract_dtstart(b)
        code = extract_mat_code(b)
        if ds and code:
            slot_codes.setdefault(ds, set()).add(code)

    # Pass 3 : filtrer puis transformer
    out_blocks = []
    n_drop = 0
    for b in blocks:
        code = extract_mat_code(b)
        ds = extract_dtstart(b)
        if code in HIDE_IF_OVERLAP and ds:
            rule = HIDE_IF_OVERLAP[code]
            others = slot_codes.get(ds, set()) - {code}
            if "*" in rule:
                drop = bool(others)
            else:
                drop = bool(set(rule) & others)
            if drop:
                n_drop += 1
                continue
        out_blocks.append(transform_block(b))

    # Reassemble
    out = list(pre)
    for b in out_blocks:
        out.extend(b)
    out.extend(post)
    folded = "\r\n".join(fold(l) for l in out) + "\r\n"
    (ROOT / "calendar.ics").write_text(folded, encoding="utf-8")
    print(f"OK: {len(out_blocks)} evenements ecrits ({n_drop} doublons supprimes).")


if __name__ == "__main__":
    main()
