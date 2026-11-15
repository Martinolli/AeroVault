# Gate 5 — Owner Acceptance Sign-off

**Status:** SIGNED — all Gate 5 handover items complete 2026-11-15; OneDrive migration, key rotation and UI smoke test verified
**Project:** AeroVault
**Owner:** J. B. Martinolli
**Security review:** `15_Gate5_Security_Review.md`, dated 2026-11-15
**Security result:** PASS — no open Critical or High findings after remediation. Overall Gate 5 is signed and complete; the residual risks below remain accepted.

## 1. Purpose

This document records the owner's acceptance of the residual Medium and Low risks in the Gate 5 security review, the owner's decision on the OneDrive exposure, and the conditions for go-live. It is intentionally separate from the technical review so the owner can accept or require remediation item by item.

## 2. Owner decision summary

| Decision | Recommended choice | Owner selection |
| --- | --- | --- |
| OneDrive exposure of `.env` and `data/` | Move the AeroVault project out of OneDrive; keep the read-only library in OneDrive. | [x] Option A — move project (recommended) / [ ] Option B — keep and accept |
| ACL access by `CodexSandboxUsers` and `msg_...` | Remove the unnecessary ACEs if Manus/Codex tooling still works; otherwise accept temporarily. | [ ] Remediate / [x] Accept temporarily |
| Backup and restore | Complete and test a SQLite `backup()` plus LanceDB copy/restore before relying on the app for work records. | [ ] Completed / [x] Accept interim risk |
| Non-root containers | Accept for the current single-owner localhost deployment; schedule hardening before LAN or long-term multi-user use. | [x] Accept / [ ] Remediate now |
| Remaining Low items | Accept for the current threat model and revisit before LAN, multi-user or hosted use. | [x] Accept all / [ ] Specify exceptions |

**Owner's recorded instructions:** move the project to `C:\Users\Aspire5 15 i7 4G2050\AeroVault`; keep the library under OneDrive; generate a new OpenAI API key, confirm it works and revoke the old key; commit and push the reviewed work.

## 3. Residual risk acceptance

The owner acknowledges the following risks. “Accept” means the risk is accepted for the current single-owner, localhost-only deployment, not that it is eliminated. “Remediate” means the item must be closed before go-live.

| ID | Severity | Residual risk | Disposition |
| --- | --- | --- | --- |
| F-03 | Medium | `.env` and `data/aerovault.db` were inside OneDrive and were reparse points; the API key, password hash, chat history and compliance metadata may have been cloud-synced. | [x] Remediate by moving project / [ ] Accept with Option B |
| F-04 | Medium | Backend and frontend containers run as root. | [x] Accept for localhost / [ ] Remediate before go-live |
| F-05 | Medium | `.env` and the database ACLs allow `CodexSandboxUsers` read access; an orphan-looking `msg_...` account has modify access. | [ ] Remediate ACLs / [x] Accept temporarily |
| F-09 | Medium | No tested backup/restore procedure; a live SQLite file copy may be inconsistent. | [ ] Complete and test backup / [x] Accept interim risk |
| F-10 | Low | Authenticated upload/model errors can expose parser or exception details. | [x] Accept |
| F-11 | Low | The Vite frontend has no CSP/HSTS/frame-ancestors policy; API responses have security headers. | [x] Accept for localhost |
| F-12 | Low | No MFA, password change/recovery or persistent lockout. | [x] Accept for single owner |
| F-13 | Low | Login throttle is in-memory and resets when the backend restarts. | [x] Accept for localhost |
| F-14 | Low/Medium | PDF/DOCX parsing has size/page limits but no explicit DOCX decompression limit or parser sandbox. | [x] Accept for trusted documents |
| F-15 | Low | The OpenAI key is visible in the container environment to local Docker administrators. | [x] Accept for trusted owner |

The High findings F-01 (Pillow 11.3.0) and F-02 (Vite 5.4.21) are already fixed and re-audited clean; they do not require owner acceptance.

## 4. OneDrive decision

The project was originally under:

`C:\Users\Aspire5 15 i7 4G2050\OneDrive\Documentos\J_B_Martinolli\DOCUMENTOS REVISION\AeroVault`

The confirmed target is:

`C:\Users\Aspire5 15 i7 4G2050\AeroVault`

The library remains under OneDrive because it is read-only source material and is already the owner's working library. The project folder contains `.env`, the SQLite database, LanceDB, chat/compliance data and local tooling, so it must not remain cloud-synced.

The approved migration sequence is:

1. Stop the Docker stack and confirm no native ingestion/OCR writer is running.
2. Pause OneDrive during the copy to avoid concurrent sync changes.
3. Copy the whole `AeroVault` folder to `C:\Users\Aspire5 15 i7 4G2050\AeroVault`; verify before removing the old copy.
4. Start the stack from the new path and verify health, login, one citation and one export.
5. Confirm `.env` and `data/aerovault.db` no longer have the OneDrive `ReparsePoint` attribute.
6. Remove the old OneDrive copy contents only after verification; remove the empty legacy folder once Windows releases its lock.
7. Update hard-coded project paths in `README.md`, the project documents and the installed skill references.
8. The owner generated and installed a new OpenAI API key after the changes, confirmed it works, and revoked the old key because it may already have been uploaded to OneDrive.

If Option B had been selected, the owner would have accepted that the API key and work data may leave the PC through OneDrive, and would still rotate the key if it had already synced. Option A is selected instead.

## 5. Backup condition

The owner understands that metadata-only compliance history does not preserve procedure text, briefs, clauses or generated answers after the two-hour in-memory run expires. Before relying on AeroVault for critical work records, the owner will complete a tested `sqlite3.Connection.backup()` snapshot plus a LanceDB copy and restore test.

For the current deployment, the owner explicitly accepts the interim recovery risk and will keep the app in a non-critical role until that test is completed.

## 6. Owner acceptance statement

I, **J. B. Martinolli**, confirm that:

- I have read the Gate 5 security review and this sign-off.

- I understand that no Critical or High findings remain open after remediation.

- I accept the residual Medium and Low risks marked “Accept” above.

- I accept the temporary ACL exposure, the interim backup risk, the root-container risk and the Low items for the current single-owner, localhost-only deployment.

- I understand that accepted risks are not eliminated and will be revisited before LAN, multi-user or hosted use.

- I approve the OneDrive decision: move the project to `C:\Users\Aspire5 15 i7 4G2050\AeroVault` and keep the library under OneDrive.

- I authorize go-live on the owner's Windows PC after the OneDrive migration is verified. I will complete the backup/restore test before relying on AeroVault for critical work records.

- I will generate and install a new OpenAI API key after the changes.

**Owner signature:** Joao B. Martinolli
**Date:** November 15, 2026
**Recorded from:** owner confirmation in the Manus task, 2026-11-15

## 7. Migration verification

This section records the verification completed after the project was copied to the new path and tested.

| Check | Evidence | Result |
| --- | --- | --- |
| Target path exists | `C:\Users\Aspire5 15 i7 4G2050\AeroVault` | Pass |
| Project copied completely | 30,860 files and 4,767,140,974 bytes on both source and target; Robocopy reported 0 failed files | Pass |
| `.env` is not a OneDrive reparse point | Target attributes: `Archive` only; source had `Archive, ReparsePoint` | Pass |
| `data/aerovault.db` is not a OneDrive reparse point | Target attributes: `Archive` only; source had `Archive, ReparsePoint` | Pass |
| SQLite data preserved | 529 documents, 209,666 chunks, 177,668 pages; source and target counts identical. `quick_check` reports the same 100 pre-existing never-used pages on both copies; no table/row mismatch | Pass |
| Backend health | `/api/health` returned `{"status":"ok","app":"AeroVault","version":"0.1.0","env":"dev"}` from the new path | Pass |
| Protected API boundary | `/api/chats` returned 401 without a session; `/api/auth/me` returned `{"authenticated":false}` | Pass |
| Container mounts | Backend data mount resolves to `C:\Users\Aspire5 15 i7 4G2050\AeroVault\data`; library remains read-only from OneDrive | Pass |
| Login, citation and export smoke tests | Owner confirmed login, one citation and one export passed on 2026-11-15 | Pass |
| OpenAI key rotation | Owner generated a new key, recreated the backend, confirmed a real request works, and revoked the old key | Pass |
| Old OneDrive project removed | Owner deleted the old AeroVault folder from OneDrive online; the local legacy path has 0 items and no secrets/data | Pass |
| Path references updated | README, project plan, step log, ADR and installed skill updated to the new root | Pass |
| OneDrive resumed | OneDrive process restarted after the copy | Pass |

The local legacy path is an empty placeholder with no `.env`, database, index, chat or compliance data; the OneDrive online copy has been deleted. It is not a security exposure.

## 8. Reviewer note

This document records the owner's typed acceptance from the Manus task; it is not a handwritten signature. The technical evidence remains in `15_Gate5_Security_Review.md`. The reviewed local commit before migration was `213660c` (Gate 5 security review and remediations). The owner confirmed the final key rotation and UI smoke test on 2026-11-15; all handover items are complete.
