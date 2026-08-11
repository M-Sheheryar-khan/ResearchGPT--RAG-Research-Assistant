import requests

def rebuild_abstract(inv_index):
    if not inv_index:
        return ""

    words = []

    for word, positions in inv_index.items():
        for pos in positions:
            words.append((pos, word))

    words.sort()

    return " ".join(word for _, word in words)


def search_papers(query, limit=5):
    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per_page": limit
    }

    response = requests.get(url, params=params)
    print("OPENALEX STATUS:", response.status_code)
    print("OPENALEX RAW:", response.text[:500])
    data = response.json()

    papers = []

    for item in data.get("results", []):

        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}

        papers.append({
            "paperId": item.get("id"),
            "title": item.get("title"),
            "abstract": rebuild_abstract(item.get("abstract_inverted_index")),
            "year": item.get("publication_year"),
            "authors": ", ".join(
                author["author"]["display_name"]
                for author in item.get("authorships", [])
                if author.get("author")
            ) or "Unknown",

            "journal": source.get("display_name"),

            "doi": item.get("doi"),

            "url": item.get("primary_location", {}).get("landing_page_url") or item.get("id"),

            "citations": item.get("cited_by_count", 0),

            "keywords": ", ".join(
                concept.get("display_name", "")
                for concept in item.get("concepts", [])[:6]
                if concept.get("display_name")
            )          
            
        })

    return papers