import os
import requests
from groq import Groq
from dotenv import load_dotenv
from app import get_connection, load_model, log_query

load_dotenv()

_GROQ_MODEL = "llama-3.1-8b-instant"


def tiered_retrieve(query: str, countries_list, top_k: int = 5):
    """
    3-tier retrieval. Returns (tier, chunks, detected_country).

    Tier 1: DB results found (country-specific or global).
    Tier 3: No DB results — caller should fall back to web_search_fallback.

    chunks rows: (chunk_id, chunk_text, title, year_published, country_name, distance)
    """
    model = load_model()
    query_lower = query.lower()
    detected = None

    for row in sorted(countries_list, key=lambda r: len(r[0]), reverse=True):
        if row[0].lower() in query_lower:
            detected = row[0]
            break

    embedding = model.encode(query).tolist()
    vector_str = "[" + ",".join(map(str, embedding)) + "]"

    try:
        conn = get_connection()
        cur = conn.cursor()

        if detected:
            cur.execute(
                "SELECT COUNT(*) FROM documents d "
                "JOIN countries c ON d.country_id = c.country_id WHERE c.name = %s;",
                (detected,),
            )
            if cur.fetchone()[0] == 0:
                cur.close()
                conn.close()
                return "tier3", [], detected

            cur.execute(
                """
                SELECT c.chunk_id, c.chunk_text, d.title, d.year_published, co.name,
                       e.embedding_vector <=> %s::vector AS distance
                FROM embeddings e
                JOIN chunks    c  ON e.chunk_id    = c.chunk_id
                JOIN documents d  ON c.doc_id      = d.doc_id
                JOIN countries co ON d.country_id  = co.country_id
                WHERE co.name = %s
                ORDER BY distance ASC
                LIMIT %s;
                """,
                (vector_str, detected, top_k),
            )
        else:
            cur.execute(
                """
                SELECT c.chunk_id, c.chunk_text, d.title, d.year_published, co.name,
                       e.embedding_vector <=> %s::vector AS distance
                FROM embeddings e
                JOIN chunks    c  ON e.chunk_id    = c.chunk_id
                JOIN documents d  ON c.doc_id      = d.doc_id
                JOIN countries co ON d.country_id  = co.country_id
                ORDER BY distance ASC
                LIMIT %s;
                """,
                (vector_str, top_k),
            )

        chunks = cur.fetchall()
        cur.close()
        conn.close()

        if not chunks:
            return "tier3", [], detected

        return "tier1", list(chunks), detected

    except Exception:
        return "tier3", [], detected


def generate_answer_grounded(query: str, chunks: list, tier: str) -> str:
    if not chunks:
        return "No relevant documents found in the database."

    context = ""
    for i, (chunk_id, chunk_text, title, year, country, distance) in enumerate(chunks):
        context += f"\n[{i+1}] Source: {title} ({country}, {year})\n{chunk_text}\n"

    unique_countries = list(set(c[4] for c in chunks))
    target = unique_countries[0] if len(unique_countries) == 1 else None

    if target:
        prompt = f"""You are a climate policy expert assistant. The user is asking specifically about {target}.

RULES:
1. Answer using ONLY information explicitly stated in the context below — all of it is from {target}
2. Do NOT invent, infer, or estimate numbers or facts not directly present in the context
3. Provide a complete, well-cited answer using all available context
4. If the context doesn't fully answer the question, share what IS available and note what's missing
5. Always cite the exact source document name

Question: {query}

Context (all from {target}):
{context}

Answer:"""
    else:
        prompt = f"""You are a climate policy expert assistant analyzing documents from multiple countries.

RULES:
1. Answer using ONLY information explicitly stated in the context below
2. Do NOT invent, infer, or estimate numbers or facts not directly present in the context
3. Always specify which country each piece of information comes from
4. Always cite the exact source document name

Question: {query}

Context:
{context}

Answer:"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def web_search_fallback(query: str) -> dict:
    """
    DuckDuckGo instant-answer API + Groq fallback generation.
    Returns {"answer": str, "sources": [{"title": str, "url": str}]}.
    """
    sources = []
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
            timeout=10,
        )
        data = resp.json()

        abstract_url  = data.get("AbstractURL", "")
        abstract_src  = data.get("AbstractSource", "")
        abstract_text = data.get("AbstractText", "")

        if abstract_url:
            sources.append({"title": abstract_src or "Web Result", "url": abstract_url})

        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("FirstURL"):
                sources.append({
                    "title": (topic.get("Text") or "")[:80] or "Related Result",
                    "url":   topic["FirstURL"],
                })

        if abstract_text:
            return {"answer": abstract_text, "sources": sources}

    except Exception:
        pass

    return {"answer": _groq_general_answer(query, sources), "sources": sources}


def _groq_general_answer(query: str, sources: list) -> str:
    try:
        sources_text = "\n".join(f"- {s['title']}: {s['url']}" for s in sources)
        prompt = (
            "You are a climate policy expert. The user's query could not be answered from "
            "the local climate policy database. Answer from your general knowledge, but "
            "CLEARLY state that this is not from the local database and may not reflect "
            "the most recent official policy documents.\n\n"
            f"Question: {query}\n\n"
            + (f"Relevant web sources:\n{sources_text}\n\n" if sources_text else "")
            + "Answer:"
        )
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        return "Web search unavailable. Please try rephrasing your query."


def log_with_tier(query: str, answer: str, top_chunk_id, tier: str) -> None:
    try:
        log_query(query, answer, top_chunk_id)
    except Exception:
        pass
