"""Collection definitions: relative paths inside the library root.

Paths are matched case-insensitively against POSIX-style relative paths.
"""

from __future__ import annotations

COLLECTIONS: dict[str, str] = {
    "Aircraft Theory": "BOOKS/Aircraft Theory(1)",
    "Aviation HF": "BOOKS/Aviation Human Factors and Risk Management(1)",
    "Quality ISO SAE": "QUALITY ISO SAE",
}

# Managed official-source folders (normally under data/regulatory_library).
# They are scanned only with the explicit --regulatory flag so the owner's
# large FAA/EASA/ICAO folders are not pulled into the core pack by accident.
REGULATORY_COLLECTIONS: dict[str, str] = {
    "FAA": "faa",
    "EASA": "easa",
    "ICAO": "icao",
    "AQAP": "aqap",
    "NASA": "nasa",
}

# Directory names never scanned (quarantine, the app itself, data folders).
EXCLUDE_PARTS: set[str] = {"AeroVault", "_QUARANTINE", ".git", "node_modules"}


def classify_path(rel_path: str, regulatory: bool = False) -> str | None:
    """Return the collection name for a library-relative path, or None."""
    rel = rel_path.replace("\\", "/").lower()
    best: tuple[int, str] | None = None
    mapping = {**COLLECTIONS, **REGULATORY_COLLECTIONS} if regulatory else COLLECTIONS
    for name, prefix in mapping.items():
        p = prefix.lower()
        if rel == p or rel.startswith(p + "/"):
            length = len(p)
            if best is None or length > best[0]:
                best = (length, name)
    return best[1] if best else None
