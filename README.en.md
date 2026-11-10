<div align="center">

<img src="web/whale.png" width="150" alt="Whale-chan · Xiaoxi">

# Mochi Reader

**Turn difficult reading into something you understand.**

A whale-girl reading companion with source citations, study cards, and quick comprehension checks.

Python · FastAPI · BM25 RAG · SQLite · Chrome MV3 · Vanilla JavaScript

[简体中文](README.md) · [Quick start](#quick-start) · [Browser extension](#browser-extension) · [Characters](docs/characters.md) · [Architecture](docs/architecture.md)

</div>

> v0.1. Try the explicitly labeled extractive demo without an API key. Configure DeepSeek to enable model-generated explanations. The current interface and assistant prompts are primarily in Chinese.

## Features

- **Read your material.** Paste an article, or actively capture a page or selection through the browser side panel.
- **Ask with evidence.** English tokens and Chinese bigrams feed a BM25 retriever. Answers refer to source fragments you can inspect.
- **Keep what you learn.** Generate up to 3 study cards and 3 multiple-choice questions, then export Markdown.
- **Choose a companion style.** Whale Girl · Xiaoxi is the default; gentle Mochi and a technical mentor are also available. Personas change the voice, while evidence and citation rules stay the same.
- **Run locally.** SQLite document storage, no frontend dependencies or build step, and server-side API configuration.

The whale-girl concept draws on community fan creations, including blue-and-white colors, a whale tail, and a fondness for rice. “Xiaoxi” is this project's nickname, not a community-standard name or an official DeepSeek persona. There is no official affiliation, Live2D runtime, or voice interaction. See the [character notes](docs/characters.md) for inspiration and asset details.

## A 30-second demo

With the server running:

1. Open the workspace and choose the sample article.
2. Ask the whale girl a question or select the key-points action; open a cited source.
3. Generate study cards and answer one quiz question.
4. Export your reading notes as Markdown.

Without a key, responses are source extracts and deterministic exercises. This demonstrates the workflow, not the quality of a live language model.

## Quick start

Requires Python 3.11+. Download the repository and open a terminal in its root directory.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

If activation scripts are disabled, use the environment's interpreter directly:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). Keep the server running when using either the web app or extension.

### Enable DeepSeek

No key is required for demo mode. For live generation, create `.env` in the repository root:

```dotenv
DEEPSEEK_API_KEY=your-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

Restart the server and check its mode in the connection settings. `.env` is excluded from Git. Model names can change; consult the [official model documentation](https://api-docs.deepseek.com/quick_start/pricing/). Compatible providers may require their own model name and base URL.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | Empty | Empty selects demo mode; a key selects live mode |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | HTTPS API base; loopback HTTP services are also accepted |
| `DEEPSEEK_MODEL` | `deepseek-flash` | Provider model name |
| `MOCHI_DB_PATH` | `data/mochi.sqlite3` | Local database path |
| `MOCHI_CORS_ORIGINS` | `http://127.0.0.1:8765,http://localhost:8765` | Comma-separated allowed web origins |

## Browser extension

Requires Chrome 116+. Other Chromium browsers depend on their own side-panel API support. This is a development extension, not a Chrome Web Store listing.

1. Start the local server.
2. Run `python scripts/package_extension.py` from the repository root. It copies the shared UI and creates `dist/mochi-reader-extension.zip`.
3. Open `chrome://extensions` or `edge://extensions` and enable Developer mode.
4. Choose **Load unpacked**, then select the repository's **`extension` directory**. Alternatively, unzip the generated archive and load that directory.
5. Open a regular webpage and click the extension's toolbar icon.
6. Open the import dialog, choose the current page / selection action, review the text, and import it.

The extension uses `activeTab`, `scripting`, and `sidePanel`, with host access limited to the local backend. It has no `<all_urls>` permission. Browser settings, store pages, and other protected pages cannot be captured; paste text instead. After changing `web/`, rerun the packaging script and reload the extension.

## Data flow

Documents and their source metadata are stored in local SQLite. The backend does not persist chat history or study cards as a long-term knowledge base. There is no telemetry. API keys remain in the Python backend.

**Live mode sends your question and relevant source fragments to the configured model provider.** Local storage does not mean model processing is local. The import flow explains this before material is submitted.

Delete documents from the workspace. The database location is controlled by `MOCHI_DB_PATH`.

## Engineering scope

```text
Explicit import → source chunks → English tokens / Chinese bigrams
    → BM25 retrieval → constrained generation → citation checks
    → study cards / quiz → Markdown export
```

The repository includes a lexical retrieval baseline, stable fragment IDs, input validation, structured study-output validation, provider error handling, SSE answer increments, a native browser side panel, and reproducible local checks.

See the Chinese-language [architecture notes](docs/architecture.md), [project research](docs/research.md), and [job-search guide](docs/job-search.md) for design choices, interview topics, and an experimental roadmap.

## Tests and evaluation

Run inside the virtual environment:

```bash
python -m pytest tests -q
python -m evals.run
python scripts/package_extension.py
```

Tests do not require a live API key. The fixed retrieval evaluation measures its own examples; it is not a measure of live-model answer accuracy or factuality. No live-provider quality result is claimed.

## Current limits

- Retrieval is **lexical BM25**, without embeddings, a vector index, or a reranker. Synonyms, cross-language questions, and very short queries may fail to retrieve useful evidence.
- Citation checks establish valid source references, not factual entailment or truth. Inspect the original material.
- Chat streams answer increments through SSE. Study generation returns after validation and uses the first 6 body-prioritized fragments, which limits long-document coverage. See the architecture notes for selection rules.
- This is a personal loopback application. It does not provide multi-user accounts or tenant isolation.
- Live generation requires your own working API key and is billed by your provider.

## License

Code: [MIT](LICENSE) © 2026 Pasukalu. The Mochi SVG is original to this project. Whale-girl community inspiration and asset details are documented separately in the [character notes](docs/characters.md).
