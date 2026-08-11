from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from scholar import search_papers as search_scholar
import os
import json
from retriever import retrieve_context
from llm import generate_answer_stream, rewrite_query_for_search
from pdf_ingest import extract_text, chunk_text, extract_metadata
from db import add_papers, add_pdf_chunks, list_pdfs, delete_pdf, get_similar_papers, get_library_stats, get_network_data

app = FastAPI()
app.mount("/files", StaticFiles(directory="uploads"), name="files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ask")
def ask(question: str):
    context = retrieve_context(question)

    if not context["sources"]:
        search_query = rewrite_query_for_search(question)
        print("REWRITTEN QUERY:", search_query)
        new_papers = search_scholar(search_query, limit=10)
        print("PAPERS FOUND:", len(new_papers))
        if new_papers:
            add_papers(new_papers)
            context = retrieve_context(question)
        print("SOURCES AFTER FALLBACK:", len(context["sources"]))

    def event_stream():
        yield "SOURCES::" + json.dumps(context["sources"]) + "\n"
        for token in generate_answer_stream(context["context"], question):
            yield token

    return StreamingResponse(event_stream(), media_type="text/plain")

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)

    pdf_path = os.path.join("uploads", file.filename)

    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    text, used_ocr = extract_text(pdf_path)
    chunks = chunk_text(text)
    pdf_metadata = extract_metadata(pdf_path)
    add_pdf_chunks(chunks, file.filename, pdf_metadata)

    return {
        "message": "PDF uploaded successfully",
        "chunks": len(chunks),
        "used_ocr": used_ocr
    }

@app.get("/pdfs")
def get_pdfs():
    return {"pdfs": list_pdfs()}

@app.get("/similar")
def similar_papers(title: str):
    return {"recommendations": get_similar_papers(title)}

@app.get("/stats")
def stats():
    return get_library_stats()

@app.get("/network")
def network():
    return get_network_data()

@app.delete("/pdfs/{filename}")
def remove_pdf(filename: str):
    delete_pdf(filename)

    file_path = os.path.join("uploads", filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    return {"message": f"{filename} deleted"}