# 5 — Wireframes (Draft)

**Version:** 0.1
**Date:** 2026-11-13
**Status:** For owner review at Gate 1

---

## 1. Design principles

- **Citation first:** every answer shows where it came from; the source is always one click away.
- **Library-aware:** the collection filter is always visible; the assistant never mixes sources silently.
- **Calm and professional:** light theme, aviation blue accents, generous spacing, readable typography.
- **Local and private:** no external navigation, no sharing controls, clear "local only" status.
- **Fast path:** the most common action — ask a question and open the cited page — takes two clicks.

## 2. Global layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  AeroVault        [Collection: All ▾]      [Model: GPT-5 ●]      [User ▾]   │
├───────────────┬──────────────────────────────────────────────┬───────────────┤
│  LIBRARY      │  MAIN WORKSPACE                              │  SOURCES      │
│  ▸ Aircraft   │                                              │  1. Book ...  │
│  ▸ HF & Risk  │  Chat history / document view                │     p. 142    │
│  ▸ ISO/SAE    │                                              │     snippet   │
│               │                                              │  [Open page]  │
│  Recent chats │  ┌────────────────────────────────────────┐  │  2. ...       │
│  • ...        │  │ User: question ...                     │  │               │
│               │  ├────────────────────────────────────────┤  │  [PDF view]   │
│  Search...    │  │ Assistant: answer with [1] [2] ...     │  │               │
│               │  └────────────────────────────────────────┘  │               │
│  [Settings]   │  [Quick ▾] [Deep] [Compare] [Summarize]      │               │
│               │  ┌────────────────────────────────────────┐  │               │
│               │  │ Ask about your library...         [↑]  │  │               │
│               │  └────────────────────────────────────────┘  │               │
└───────────────┴──────────────────────────────────────────────┴───────────────┘
```

## 3. Screens

### 3.1 Login

- Centered card on a plain background; AeroVault wordmark.
- Single password field with show/hide toggle.
- "Unlock" button; error message for wrong password; lockout message after repeated failures.
- Footer: "Runs locally on this computer. No library content leaves this machine except configured model calls."

### 3.2 Chat (primary screen)

- **Conversation area:** user and assistant messages; assistant messages show inline citation chips `[1]`, `[2]` that highlight the matching source in the right panel.
- **Composer:** multiline input, send button, mode selector (Quick answer / Deep analysis / Compare sources / Summarize section).
- **Suggested prompts:** Occurrence analysis, Risk assessment (5×5), Compliance/gap check, Report draft.
- **States:** thinking indicator with retrieval steps ("Searching 3 collections… 12 passages found… reranking…"), low-confidence banner ("Not found in the library — here is what was searched"), error banner with retry.
- **Answer footer:** model used, tokens, latency, "Copy", "Export", "Save to notes".

### 3.3 Sources panel

- Ordered list of retrieved passages: document title, collection, page, relevance score, short snippet.
- "Open page" opens the PDF viewer at that page with the passage highlighted.
- Toggle: "Show all retrieved passages" vs "Only cited passages".
- If a passage comes from OCR, show an "OCR" badge and confidence indicator.

### 3.4 PDF viewer

- Page image with text highlight overlay; previous/next page; zoom; page number box.
- Header: document title, edition, page X of Y; "Open original file" link.
- Sidebar: document metadata and chunk outline.

### 3.5 Library

- Table view: Title, Collection, Type, Pages, Edition, Size, Index status (Indexed / OCR needed / Error / Queued).
- Filters: collection, type, status; search by filename or title.
- Bulk actions: re-index selected, export metadata CSV.
- Empty state: "Build index" button with progress dialog.

### 3.6 Document detail

- Metadata card: title, author/issuer, edition/year, collection, file path, checksum, page count.
- Index card: chunks, embeddings model, last indexed, "Re-index" button.
- Preview: first page thumbnail and extracted text sample.
- Actions: open original, open in chat with this document as filter.

### 3.7 Settings

- **Model:** provider (OpenAI / Azure OpenAI / Ollama), model name, API key status (masked; "Replace key" opens a local form), test connection.
- **Retrieval:** top-k, rerank on/off, hybrid weight, max context tokens.
- **Library:** index location, rebuild index, add collection folder, OCR settings (language, DPI).
- **Data & privacy:** backup now, restore, export query log, clear query log.
- **Account:** change password, logout, session timeout.
- **About:** version, licenses, diagnostics.

### 3.8 First-run wizard

1. Set password.
2. Add library folder(s).
3. Scan and show inventory summary (files, formats, estimated pages).
4. Build index with progress and ETA.
5. Test question and sample citation.
6. Done — open chat.

## 4. Key flows

### 4.1 Ask a question

1. Select collection filter (default All).
2. Type question or choose a template.
3. Retrieval runs; sources panel fills.
4. Answer streams with citations.
5. Click a citation → PDF viewer opens at the page with highlight.
6. Export answer (Markdown/Word/PDF) if needed.

### 4.2 Occurrence analysis workflow

1. Choose "Occurrence analysis".
2. Form: event description, aircraft type, phase of flight, consequences, available evidence.
3. Assistant produces: factual summary, hazard identification, risk assessment (severity × likelihood), defences/bow-tie elements, recommendations — each with citations.
4. Export as a structured report.

### 4.3 Add or update a document

1. Drop a file into the watched folder or use "Add document".
2. System detects checksum change, queues parsing/OCR.
3. Library shows progress and status.
4. Re-index completes; search includes the new content.

## 5. Visual style

| Element | Choice |
|---------|--------|
| Theme | Light, with optional dark mode later |
| Primary color | Aviation blue `#0B3D91`, accent `#1E5AA8` |
| Background | `#F7F9FC`, cards white |
| Typography | Inter or system UI; 14–16 px body |
| Corners | 8 px radius; subtle shadows |
| Icons | Outline style, consistent set |
| Status colors | Green indexed, amber OCR/queued, red error |

## 6. Out of scope for the MVP

- Multi-user roles and sharing links.
- Mobile layout.
- In-document annotations.
- Public internet exposure.
