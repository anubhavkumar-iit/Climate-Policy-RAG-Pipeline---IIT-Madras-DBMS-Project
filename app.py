# =============================================================================
# Climate Policy RAG Pipeline
# Z2004: Database Management Systems — Final Submission
# Team: Rohan Saha (ZDA24B009) | Anubhav Kumar (ZDA24B034)
# IIT Madras Zanzibar, Even Semester 2026
# =============================================================================

import os
import psycopg2
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# 1. Database Connection
# =============================================================================
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# =============================================================================
# 2. Embedding Model
# =============================================================================
_model = None

def load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

# =============================================================================
# 3. Detect if a specific country is named in the query
# =============================================================================
def get_all_country_names():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM countries;")
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return names

def detect_country_in_query(query_text):
    query_lower = query_text.lower()
    for name in sorted(get_all_country_names(), key=len, reverse=True):
        if name.lower() in query_lower:
            return name
    return None

# =============================================================================
# 4. Retrieve Top-K Chunks via pgvector Cosine Similarity
#    If a specific country is detected, filter results to that country only
# =============================================================================
def retrieve_chunks(query_text, top_k=5):
    query_embedding = load_model().encode(query_text).tolist()
    vector_str = "[" + ",".join(map(str, query_embedding)) + "]"

    target_country = detect_country_in_query(query_text)

    conn = get_connection()
    cur = conn.cursor()

    if target_country:
        # Country-specific query — only retrieve chunks from that country,
        # ranked by similarity score within that country
        cur.execute("""
            SELECT c.chunk_id, c.chunk_text, d.title, d.year_published, co.name AS country,
                   e.embedding_vector <=> %s::vector AS distance
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            JOIN countries co ON d.country_id = co.country_id
            WHERE co.name = %s
            ORDER BY distance ASC
            LIMIT %s;
        """, (vector_str, target_country, top_k))
    else:
        # General query — search across all countries
        cur.execute("""
            SELECT c.chunk_id, c.chunk_text, d.title, d.year_published, co.name AS country,
                   e.embedding_vector <=> %s::vector AS distance
            FROM embeddings e
            JOIN chunks c ON e.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
            JOIN countries co ON d.country_id = co.country_id
            ORDER BY distance ASC
            LIMIT %s;
        """, (vector_str, top_k))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return results, target_country

# =============================================================================
# 5. Generate Answer via Groq LLaMA 3
# =============================================================================
def generate_answer(query_text, chunks, target_country=None):
    if not chunks:
        if target_country:
            return f"I cannot find any documents about {target_country} in the database."
        return "No relevant documents found."

    context = ""
    for i, (chunk_id, chunk_text, title, year, country, distance) in enumerate(chunks):
        context += f"\n[{i+1}] Source: {title} ({country}, {year})\n{chunk_text}\n"

    if target_country:
        prompt = f"""You are a climate policy expert assistant. The user is asking specifically about {target_country}.

RULES:
1. Answer using ONLY information explicitly stated in the context below — all of it is from {target_country}
2. Do NOT invent, infer, or estimate numbers, statistics, or facts not directly present in the context
3. Use all the provided context to give a complete, well-cited answer about {target_country}'s climate policy
4. If the context doesn't fully answer the question, share what IS available and note what's missing
5. Always cite the exact source document name

Question: {query_text}

Context (all from {target_country}):
{context}

Answer:"""
    else:
        prompt = f"""You are a climate policy expert assistant analyzing climate policy documents from multiple countries.

RULES:
1. Answer using ONLY information explicitly stated in the context below
2. Do NOT invent, infer, or estimate numbers, statistics, or facts not directly present in the context
3. Always specify which country each piece of information comes from
4. Always cite the exact source document name

Question: {query_text}

Context:
{context}

Answer:"""

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# =============================================================================
# 6. Log Query to Database
# =============================================================================
def log_query(query_text, answer_text, top_chunk_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CALL log_query(%s, %s, %s);", (query_text, answer_text, top_chunk_id))
    conn.commit()
    cur.close()
    conn.close()

# =============================================================================
# 7. Get all countries (for UI/sidebar use)
# =============================================================================
def get_all_countries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT co.name, co.iso_code, COUNT(DISTINCT d.doc_id) as docs, COUNT(c.chunk_id) as chunks
        FROM countries co
        JOIN documents d ON co.country_id = d.country_id
        JOIN chunks c ON d.doc_id = c.doc_id
        GROUP BY co.name, co.iso_code
        ORDER BY co.name;
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

# =============================================================================
# 8. Full RAG Pipeline
# =============================================================================
def rag_pipeline(query_text):
    print(f"\n{'='*60}")
    print(f"Query: {query_text}")
    print('='*60)

    print("\nRetrieving relevant chunks...")
    chunks, target_country = retrieve_chunks(query_text, top_k=5)

    if target_country:
        print(f"Detected country: {target_country} — filtering results to this country only")

    if not chunks:
        print("No relevant chunks found.")
        answer = generate_answer(query_text, chunks, target_country)
        print(f"\nAnswer:\n{answer}")
        return answer

    print(f"Found {len(chunks)} relevant chunks:")
    for i, (chunk_id, chunk_text, title, year, country, distance) in enumerate(chunks):
        print(f"  [{i+1}] {title} ({country}, {year}) — distance: {distance:.4f}")

    print("\nGenerating answer...")
    answer = generate_answer(query_text, chunks, target_country)
    print(f"\nAnswer:\n{answer}")

    top_chunk_id = chunks[0][0]
    log_query(query_text, answer, top_chunk_id)
    print(f"\nQuery logged to database (top chunk: {top_chunk_id})")
    print('='*60)

    return answer

# =============================================================================
# 9. Main — Interactive or Test Mode
# =============================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("   Climate Policy RAG Pipeline")
    print("   IIT Madras Zanzibar — Z2004 DBMS Final Project")
    print("   Team: Rohan Saha & Anubhav Kumar")
    print("="*60)
    print("Type your climate policy question and press Enter.")
    print("Type 'quit' to exit.\n")

    while True:
        query = input("Your question: ").strip()
        if query.lower() == "quit":
            print("Exiting. Goodbye!")
            break
        if not query:
            continue
        rag_pipeline(query)