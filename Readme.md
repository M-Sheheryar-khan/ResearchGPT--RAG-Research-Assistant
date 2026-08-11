# 🔬 ResearchGPT — Local RAG Research Assistant

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688) ![VectorDB](https://img.shields.io/badge/VectorDB-Chroma-orange) ![React](https://img.shields.io/badge/React-18.x-61DAFB) ![LLM](https://img.shields.io/badge/LLM-Qwen3%20via%20Ollama-black) ![Status](https://img.shields.io/badge/Status-Development%20Ready-brightgreen)

## 📖 Project Overview

ResearchGPT is a fully local, privacy-first research assistant that lets you upload PDFs, ask questions in natural language, and get synthesized, cited answers pulled from your own paper library — or automatically fetched from the web if your library doesn't have enough to answer with.

It runs entirely on local infrastructure: local embeddings, a local LLM via Ollama, and a local vector database. No OpenAI key, no cloud dependency, no per-token cost. When your local library can't answer a question, it automatically rewrites your query, searches OpenAlex (240M+ scholarly works) for relevant papers, ingests them on the fly, and re-answers — all inside a single request.

## 🎯 Key Features

### 📚 Smart Retrieval-Augmented Generation
- **Local-first search**: Every question first searches your own uploaded papers via semantic similarity in ChromaDB.
- **Automatic web fallback**: If local results fall below a relevance threshold, the system rewrites your question into a concise academic search query and pulls fresh papers from the OpenAlex API — no manual searching required.
- **Distance-based filtering**: Retrieved chunks are filtered by embedding distance to keep low-relevance noise out of the context window.
- **Deduplication**: Multiple chunks from the same paper are merged into a single cited source.

### 📄 Resilient PDF Ingestion
- **Text extraction**: Uses `pypdf` for standard text-based PDFs.
- **OCR fallback**: Automatically detects scanned/image-based PDFs (via a minimum text-length heuristic) and falls back to Tesseract OCR, so scanned papers are searchable too.
- **Metadata extraction**: Pulls author and publication year directly from PDF metadata.
- **Chunking with overlap**: Splits documents into overlapping word-based chunks to preserve context across chunk boundaries.

### 🧠 Local LLM Generation
- **Ollama-powered**: Runs entirely on a local Qwen3 model — no external API calls for generation.
- **Streaming responses**: Answers stream token-by-token to the frontend via a lightweight SSE-style protocol.
- **Grounded citations**: The model is explicitly instructed to cite every factual claim (`[1]`, `[2]`, etc.), never invent unsupported information, and clearly state when context is insufficient.
- **Multi-paper synthesis**: When multiple papers are retrieved, the model explicitly notes where they agree or disagree.

### 🕸️ Library Intelligence
- **Similar papers**: Recommends related papers using cosine similarity between document embeddings.
- **Citation network graph**: Builds a force-directed graph of your entire library based on pairwise embedding similarity, rendered interactively in the frontend.
- **Library stats dashboard**: Live breakdown of your library by publication year and top recurring keywords.

### 💻 Interactive Frontend
- **Streaming markdown answers**: Renders formatted, cited answers in real time as they generate.
- **Force-directed citation graph**: Visual, clickable map of how papers in your library relate to one another (`react-force-graph-2d`).
- **Stats charts**: Year and keyword distributions via `recharts`.
- **Drag-and-drop PDF upload**: With live OCR-used indicator and chunk count feedback.

## 🛠️ Technologies Used

### Backend
- **Python 3.10+**
- **FastAPI** — async API with streaming responses
- **ChromaDB** — persistent local vector database
- **Sentence-Transformers** (`all-MiniLM-L6-v2`) — local embedding generation
- **Ollama** (`qwen3:4b`) — local LLM inference and streaming generation
- **pypdf / pytesseract / pdf2image** — PDF text extraction and OCR fallback
- **NumPy** — similarity matrix computation for the citation network
- **OpenAlex API** — keyless, free access to 240M+ scholarly works for the auto-fetch fallback

### Frontend
- **React** (Vite)
- **react-force-graph-2d** — interactive citation network visualization
- **Recharts** — library statistics charts
- **react-markdown + remark-gfm** — streamed markdown rendering
- **Axios** — API communication

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed locally, with the `qwen3:4b` model pulled:
```bash
  ollama pull qwen3:4b
```
- Tesseract OCR installed on your system (for scanned PDF support)

### Backend Setup

```bash
git clone https://github.com/M-Sheheryar-khan/ResearchGPT--RAG-Research-Assistant.git
   cd ResearchGPT--RAG-Research-Assistant

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt

uvicorn api:app --reload
```

The backend runs at `http://127.0.0.1:8000`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open your browser to `http://localhost:5173`.

## 🗂️ Project Structure

```
ResearchGPT/
├── api.py              # FastAPI routes: /ask, /upload, /pdfs, /similar, /stats, /network
├── llm.py               # Ollama integration: streaming answer generation, query rewriting
├── retriever.py          # Context retrieval, distance filtering, dedup, prompt assembly
├── db.py                # ChromaDB operations: upserts, similarity search, stats, network graph
├── scholar.py            # OpenAlex API client and abstract reconstruction
├── pdf_ingest.py           # Text extraction, metadata extraction, chunking
├── ocr.py                # Tesseract OCR fallback for scanned PDFs
├── embeddings.py           # Sentence-Transformers embedding wrapper
├── ingest.py             # CLI utility to bulk-seed the library from a topic
├── requirements.txt
├── uploads/              # Uploaded PDFs (gitignored)
├── vector_database/         # Persistent ChromaDB store (gitignored)
└── frontend/
    ├── src/
    │   ├── App.jsx         # Main UI: chat, upload, stats, citation graph
    │   ├── App.css
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```


## 🔬 Technical Implementation Details

### Retrieval & Fallback Flow

1. A question hits `/ask` and is embedded, then searched against the local ChromaDB collection.
2. Results are filtered by a maximum embedding distance threshold to exclude weak matches.
3. If no results pass the threshold, the question is rewritten by the LLM into a short academic-style search query.
4. That query is sent to OpenAlex; returned papers are embedded and upserted into the vector database.
5. Retrieval is re-run against the now-updated library, and the answer is generated from the fresh context.

### Citation Network Construction

Papers are grouped by title, and their chunk-level embeddings are averaged into a single per-paper vector. Cosine similarity is computed pairwise across all papers in the library:

```
similarity(i, j) = (v_i · v_j) / (‖v_i‖ ‖v_j‖)
```

For each paper, the top-*k* most similar papers above a similarity threshold become graph edges, deduplicated across both directions, and rendered as a force-directed graph in the frontend.

### OCR Fallback Heuristic

After standard text extraction via `pypdf`, if the extracted text falls below a minimum character threshold, the PDF is assumed to be scanned/image-based. Each page is rendered to an image and passed through Tesseract OCR, and the reconstructed text replaces the empty extraction.

## 🤝 Contributing

1. Fork the repository
2. Create your branch: `git checkout -b feature/cool-new-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/cool-new-feature`
5. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
