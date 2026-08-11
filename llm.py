import requests
import json

def generate_answer_stream(context, question):
    prompt = f"""
You are ResearchGPT. /no_think

Your job is to synthesize information from multiple research papers.

Instructions:
- Begin with a brief introduction to the topic.
- Explain concepts in clear, easy-to-understand language.
- Combine information from multiple papers when appropriate.
- Do not repeat information
- If multiple papers agree, mention that.
- If papers disagree, explain the disagreement.
- Use headings and bullet points whenever they improve readability.
- Include examples if they are supported by the provided papers.
- Keep the answer informative but avoid unnecessary repetition.
- Cite factual statements using [1], [2], etc.
- Never invent information that is not supported by the context.
- If the context does not contain enough information, clearly state that.
- Treat each paper's TITLE field as its exact, correct title. Never comment on, question, or repeat the raw formatting of the context (e.g. do not say a title looks cut off, incomplete, or malformed).
- Never describe or refer to the structure of the context itself (e.g. do not mention "PAPER 1", field labels, or how the information was provided to you). Refer to sources only by their title or citation number.
- If a title is missing, generic, or unclear, simply refer to that source by its citation number (e.g. [1]) rather than commenting on the title.

Context:
{context}

Question:
{question}

Answer:
"""

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen3:4b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "think": False
        },
        stream=True
    )

    buffer = ""
    thinking_done = False

    for line in response.iter_lines():
        if not line:
            continue

        data = json.loads(line.decode("utf-8"))
        token = data.get("message", {}).get("content", "")

        if thinking_done:
            if token:
                yield token
        else:
            buffer += token
            if "</think>" in buffer:
                thinking_done = True
                remainder = buffer.split("</think>", 1)[1]
                if remainder:
                    yield remainder

        if data.get("done"):
            break

def rewrite_query_for_search(question):
    prompt = f"""Rewrite the following question as a concise academic search query (3-8 words), matching how a research paper title or keyword phrase would be written. Return ONLY the rewritten query, nothing else.

Question: {question}

Search query:"""

    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "qwen3:4b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False
        }
    )

    data = response.json()
    content = data.get("message", {}).get("content", "")

    if "</think>" in content:
        content = content.split("</think>", 1)[1]

    return content.strip().strip('"')