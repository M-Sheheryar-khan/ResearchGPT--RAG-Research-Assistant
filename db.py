import chromadb
import numpy as np
from embeddings import create_embedding

client = chromadb.PersistentClient(path="vector_database")
collection = client.get_or_create_collection(name="papers")

def search_papers(query, k=5, where=None):
    query_embedding = create_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    if not results["documents"][0]:
        return []

    papers = []

    for i in range(len(results["documents"][0])):
        papers.append({
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })

    return papers

def add_papers(papers):
    documents = []
    embeddings = []
    metadatas = []
    ids = []

    for paper in papers:
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")

        text = (title + "\n\n" + abstract).strip()
        embedding = create_embedding(text)

        documents.append(text)
        embeddings.append(embedding)

        metadatas.append({
            "title": title,
            "abstract": abstract,
            "year": paper.get("year"),
            "authors": paper.get("authors"),
            "journal": paper.get("journal"),
            "url": paper.get("url"),
            "doi": paper.get("doi"),
            "citations": paper.get("citations"),
            "keywords": paper.get("keywords")
        })
        paper_id = paper.get("paperId") or paper.get("title", "")
        ids.append(paper_id)
    
    collection.upsert(
        documents = documents,
        embeddings = embeddings,
        metadatas=  metadatas,
        ids = ids
    )

    return len(papers)

def add_pdf_chunks(chunks, filename, pdf_metadata=None):
    documents = []
    embeddings = []
    metadatas = []
    ids = []

    pdf_metadata = pdf_metadata or {}

    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        embeddings.append(create_embedding(chunk))
        metadatas.append({
            "title": filename,
            "type": "pdf",
            "chunk": i,
            "url": f"http://127.0.0.1:8000/files/{filename}",
            "authors": pdf_metadata.get("author", "Unknown"),
            "year": pdf_metadata.get("year", "Unknown")
        })
        ids.append(f"{filename}_{i}")

    collection.upsert(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

def list_pdfs():
    results = collection.get(
        where={"type": "pdf"},
        include=["metadatas"]
    )

    seen = {}

    for meta in results["metadatas"]:
        title = meta.get("title")
        if title not in seen:
            seen[title] = {
                "title": title,
                "authors": meta.get("authors", "Unknown"),
                "year": meta.get("year", "Unknown"),
                "url": meta.get("url")
            }

    return list(seen.values())

def delete_pdf(filename):
    collection.delete(where={"title": filename})

def get_similar_papers(title, k=4):
    result = collection.get(
        where={"title": title},
        include=["embeddings", "metadatas"],
        limit=1
    )

    if result["embeddings"] is None or len(result["embeddings"]) == 0:
        return []

    reference_embedding = result["embeddings"][0]

    similar = collection.query(
        query_embeddings=[reference_embedding],
        n_results=k + 5,
        include=["metadatas", "distances"]
    )

    seen_titles = {title}
    recommendations = []

    for i in range(len(similar["metadatas"][0])):
        meta = similar["metadatas"][0][i]
        candidate_title = meta.get("title")

        if candidate_title in seen_titles:
            continue

        seen_titles.add(candidate_title)
        recommendations.append({
            "title": candidate_title,
            "authors": meta.get("authors", "Unknown"),
            "year": meta.get("year", "Unknown"),
            "url": meta.get("url"),
            "distance": similar["distances"][0][i]
        })

        if len(recommendations) >= k:
            break

    return recommendations

def get_library_stats():
    results = collection.get(include=["metadatas"])

    year_counts = {}
    keyword_counts = {}
    type_counts = {"paper": 0, "pdf": 0}
    seen_titles = set()

    for meta in results["metadatas"]:
        title = meta.get("title")

        if title in seen_titles:
            continue
        seen_titles.add(title)

        doc_type = meta.get("type", "paper")
        type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        year = meta.get("year")
        if year and year != "Unknown" and str(year).isdigit():
            year_counts[year] = year_counts.get(year, 0) + 1

        keywords = meta.get("keywords")
        if keywords:
            if isinstance(keywords, str):
                keyword_list = [k.strip() for k in keywords.split(",")]
            elif isinstance(keywords, list):
                keyword_list = keywords
            else:
                keyword_list = []

            for kw in keyword_list:
                if kw:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    years_sorted = sorted(year_counts.items(), key=lambda x: x[0])
    top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_documents": len(seen_titles),
        "papers": type_counts.get("paper", 0),
        "pdfs": type_counts.get("pdf", 0),
        "by_year": [{"year": y, "count": c} for y, c in years_sorted],
        "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords]
    }

def get_network_data(similarity_threshold=0.5, max_edges_per_node=4):
    results = collection.get(include=["embeddings", "metadatas"])

    grouped = {}

    for i, meta in enumerate(results["metadatas"]):
        title = meta.get("title")
        if not title:
            continue

        if title not in grouped:
            grouped[title] = {
                "embeddings": [],
                "type": meta.get("type", "paper"),
                "year": meta.get("year", "Unknown")
            }

        grouped[title]["embeddings"].append(results["embeddings"][i])

    titles = list(grouped.keys())

    if len(titles) < 2:
        return {"nodes": [], "links": []}

    vectors = []
    for title in titles:
        embs = np.array(grouped[title]["embeddings"])
        avg = embs.mean(axis=0)
        vectors.append(avg)

    vectors = np.array(vectors)

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    normalized = vectors / norms

    similarity_matrix = np.dot(normalized, normalized.T)

    nodes = []
    for title in titles:
        nodes.append({
            "id": title,
            "type": grouped[title]["type"],
            "year": grouped[title]["year"]
        })

    links = []
    for i in range(len(titles)):
        scores = []
        for j in range(len(titles)):
            if i == j:
                continue
            score = similarity_matrix[i][j]
            if score >= similarity_threshold:
                scores.append((j, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_matches = scores[:max_edges_per_node]

        for j, score in top_matches:
            pair = tuple(sorted([titles[i], titles[j]]))
            links.append({
                "source": pair[0],
                "target": pair[1],
                "value": float(score)
            })

    seen_links = set()
    unique_links = []
    for link in links:
        key = (link["source"], link["target"])
        if key not in seen_links:
            seen_links.add(key)
            unique_links.append(link)

    return {"nodes": nodes, "links": unique_links}