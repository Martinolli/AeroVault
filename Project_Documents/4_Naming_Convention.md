# 4 — Naming Convention (Draft)

**Version:** 0.1 (for owner approval)
**Date:** 2026-11-13
**Scope:** Files in the three initial collections — Aircraft Theory, Aviation HF and Risk Management, Quality ISO SAE

---

## 1. Goals

- Make filenames predictable, sortable and searchable.
- Preserve the original title, author and edition — never invent metadata.
- Keep acronyms and proper names intact (HFACS, ICAO, EASA, DO-178C, ARP4754A).
- Avoid characters that break Windows paths or Markdown links.
- Make duplicate detection reliable.

## 2. Proposed pattern

```
<Author or Issuer> - <Title> (<Year or Edition>) [<Document type>].<ext>
```

Fields that are unknown are omitted. Examples:

| Current name | Proposed name |
|---|---|
| `Book Human Error by James Reason(1).pdf` | `James Reason - Human Error (1990) [Book].pdf` |
| `airworthiness_aircraft_certifiaction.pdf` | `Airworthiness - Aircraft Certification [Guidance].pdf` |
| `0_RobustQMS_Guidance_top_20150414_eng.pdf` | `RobustQMS - Guidance (2015-04-14) [Guidance].pdf` |
| `2016_aug_progress.pdf` | `2016-08 - Progress Report [Report].pdf` |

## 3. Conservative Phase 1 rules (automatic, safe)

Phase 1 changes only what can be derived from the filename itself:

1. Remove the leading `Book ` prefix (353 files).
2. Replace underscores with single spaces.
3. Collapse repeated spaces into one.
4. Trim leading and trailing spaces.
5. Remove duplicate `(1)`, `(2)` suffixes **only after the file has been hash-verified as an exact duplicate** and quarantined.
6. Preserve the original letter case of words and acronyms.
7. Keep the extension unchanged.
8. Do not rename files that already follow the pattern.
9. Never rename across collections.

Phase 1 does **not** attempt to guess authors, years or editions. That is Phase 2, where metadata is extracted from the first pages (or confirmed by the owner) and a second dry-run list is produced.

## 4. Phase 2 (metadata enrichment, optional)

- Extract title, author, edition and year from the first 2–3 pages.
- Show a review table; the owner confirms or edits each entry.
- Apply only approved changes.
- Record every rename in `rename_log.csv` (old path, new path, date, reason).

## 5. Safety rules

- A dry-run CSV (`rename_proposal.csv`) is always produced first and reviewed by the owner.
- Files are renamed with `os.replace` within the same folder; no file content is modified.
- A rollback file maps every old name to its new name.
- If a target name already exists, append ` (2)` rather than overwrite.
- Invalid characters `<>:"/\|?*` are removed; names are capped at 180 characters.
- The rename operation is logged in the Step Log.

## 6. Decision requested

Approve Phase 1 (automatic safe normalization) and the pattern for Phase 2, or propose changes before implementation.
