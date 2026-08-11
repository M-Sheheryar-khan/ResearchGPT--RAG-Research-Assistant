from db import search_papers

def retrieve_context(query, k=15, source_type=None, max_distance=0.8):
    where = {"type": source_type} if source_type else None
    results = search_papers(query, k, where=where)
    results = [r for r in results if r["distance"] <= max_distance]

    if not results:
        return{
            "query": query,
            "context": "",
            "sources": []
        }

    context = ""
    seen_titles = set()
    deduped_sources = []

    for i, paper in enumerate(results):
        meta = paper["metadata"]
        title = meta.get("title")

        context += f"""
PAPER {i+1}
TITLE: {title}
YEAR: {meta.get('year')}
AUTHORS: {meta.get('authors')}
JOURNAL:{meta.get("journal")}
KEYWORDS:{meta.get("keywords")}
CONTENT:
{paper['document'][:1500]}

---
"""

        if title not in seen_titles:
            seen_titles.add(title)
            deduped_sources.append(paper)

    return {
        "query": query,
        "context": context,
        "sources": deduped_sources
    }