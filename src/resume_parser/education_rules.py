#!/usr/bin/env python3
"""Centralized education/degree matching rules loaded from JSON."""

import json
import re
from functools import lru_cache
from pathlib import Path


_NON_DEGREE_ROLE_RE = re.compile(
    r"\b("
    r"resident\s+assistant|"
    r"vice\s+president|"
    r"president|"
    r"economics\s+tutor|"
    r"research\s+assistant"
    r")\b",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=1)
def _load_degree_terms() -> list[str]:
    contract_path = Path(__file__).resolve().parent / "contracts" / "education-degree-types.json"
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    out: list[str] = []
    for values in data.values():
        out.extend(values or [])
    # longest first to prefer specific phrases
    normalized = sorted({_normalize(v) for v in out if _normalize(v)}, key=len, reverse=True)
    return normalized


@lru_cache(maxsize=1)
def _abbreviation_regexes() -> list[re.Pattern]:
    out: list[re.Pattern] = []
    for term in _load_degree_terms():
        compact = term.replace(" ", "")
        if compact.isalpha() and 2 <= len(compact) <= 6:
            # Example: "bs" -> r"\bb\.?\s*s\.?\b"
            parts = [re.escape(ch) + r"\.?\s*" for ch in compact]
            pat = r"\b" + "".join(parts).rstrip(r"\s*") + r"\.?\b"
            out.append(re.compile(pat, re.IGNORECASE))
    return out


def has_legitimate_degree(role: str) -> bool:
    role = role or ""
    norm_role = f" {_normalize(role)} "
    if not norm_role.strip():
        return False
    for term in _load_degree_terms():
        if f" {term} " in norm_role:
            return True
    for rx in _abbreviation_regexes():
        if rx.search(role):
            return True
    return False


def is_non_degree_role(role: str) -> bool:
    return bool(_NON_DEGREE_ROLE_RE.search(role or ""))

