import pandas as pd
import psycopg2
from datasets import load_dataset, concatenate_datasets
from sentence_transformers import SentenceTransformer
import os

# ── Database connection ────────────────────────────────────
conn = psycopg2.connect(
    host="localhost",
    database="climate_rag",
    user="postgres",
    password="RohanSaha2006@"
)
cur = conn.cursor()
print("Connected to database.")

# ── Load from many positions across the dataset ───────────
print("Loading dataset from spread positions...")
splits = [
    'train[0:100]',
    'train[2000000:2000100]',
    'train[4000000:4000100]',
    'train[6000000:6000100]',
    'train[8000000:8000100]',
    'train[10000000:10000100]',
    'train[12000000:12000100]',
    'train[14000000:14000100]',
    'train[16000000:16000100]',
    'train[18000000:18000100]',
    'train[20000000:20000100]',
    'train[22000000:22000100]',
    'train[24000000:24000100]',
    'train[26000000:26000100]',
    'train[28000000:28000100]',
    'train[30000000:30000100]',
    'train[32000000:32000100]',
    'train[34000000:34000100]',
    'train[36000000:36000100]',
    'train[38000000:38000100]',
    'train[40000000:40000100]',
    'train[42000000:42000100]',
    'train[44000000:44000100]',
    'train[46000000:46000100]',
    'train[48000000:48000100]',
    'train[50000000:50000100]',
    'train[52000000:52000100]',
    'train[54000000:54000100]',
    'train[56000000:56000100]',
    'train[58000000:58000100]',
    'train[60000000:60000100]',
    'train[62000000:62000100]',
    'train[64000000:64000100]',
    'train[66000000:66000100]',
    'train[68000000:68000100]',
    'train[70000000:70000100]',
]
datasets = [load_dataset('ClimatePolicyRadar/all-document-text-data', split=s) for s in splits]
ds = concatenate_datasets(datasets)
df = pd.DataFrame(ds)
print(f"Dataset loaded. Rows: {len(df)}")
print(f"Unique docs: {df['document_id'].nunique()}")
print(f"Unique geos: {df['document_metadata.geographies'].apply(lambda x: x[0] if isinstance(x,list) and len(x)>0 else 'UNK').nunique()}")

# Save as data.csv
os.makedirs("data", exist_ok=True)
df.to_csv("data/data.csv", index=False)
print("Saved data/data.csv")

# ── Helper ────────────────────────────────────────────────
def get_country(geo):
    try:
        if isinstance(geo, list) and len(geo) > 0:
            iso = str(geo[0])[:10]
            return iso, iso
        return 'UNK', 'Unknown'
    except:
        return 'UNK', 'Unknown'

# ── Insert countries ──────────────────────────────────────
print("Inserting countries...")
iso_to_id = {}
seen_countries = set()
for _, row in df.iterrows():
    iso, name = get_country(row['document_metadata.geographies'])
    if iso not in seen_countries:
        seen_countries.add(iso)
        cur.execute("""
            INSERT INTO countries (iso_code, name)
            VALUES (%s, %s)
            ON CONFLICT (iso_code) DO NOTHING
            RETURNING country_id
        """, (iso, name[:100]))
        result = cur.fetchone()
        if result:
            iso_to_id[iso] = result[0]
conn.commit()

cur.execute("SELECT iso_code, country_id FROM countries")
for row in cur.fetchall():
    iso_to_id[row[0]] = row[1]
print(f"Inserted {len(seen_countries)} countries.")

# ── Insert documents ──────────────────────────────────────
print("Inserting documents...")
docstr_to_id = {}
seen_docs = set()
for _, row in df.iterrows():
    doc_str = str(row['document_id'])
    if doc_str in seen_docs:
        continue
    seen_docs.add(doc_str)
    iso, _ = get_country(row['document_metadata.geographies'])
    country_id = iso_to_id.get(iso)
    title = str(row['document_metadata.document_title'])[:255]

    raw_type = str(row['document_metadata.type']).strip()
    if 'Law' in raw_type:
        doc_type = 'Law'
    elif 'IPCC' in raw_type:
        doc_type = 'IPCC'
    elif 'IPBES' in raw_type:
        doc_type = 'IPBES'
    else:
        doc_type = 'NDC'

    pub_ts = str(row['document_metadata.publication_ts'])
    try:
        year = int(pub_ts[:4])
        if year < 1990 or year > 2100:
            year = 2020
    except:
        year = 2020

    cur.execute("""
        INSERT INTO documents (title, country_id, doc_type, year_published)
        VALUES (%s, %s, %s, %s)
        RETURNING doc_id
    """, (title, country_id, doc_type, year))
    doc_id = cur.fetchone()[0]
    docstr_to_id[doc_str] = doc_id

conn.commit()
print(f"Inserted {len(seen_docs)} documents.")

# ── Insert chunks + embeddings ────────────────────────────
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

sample = df.dropna(subset=['text_block.text'])
print(f"Inserting {len(sample)} chunks and embeddings...")

chunk_index_tracker = {}

for i, (_, row) in enumerate(sample.iterrows(), 1):
    text = str(row['text_block.text'])
    doc_str = str(row['document_id'])
    doc_id = docstr_to_id.get(doc_str)
    if doc_id is None:
        continue

    chunk_index_tracker[doc_id] = chunk_index_tracker.get(doc_id, 0) + 1
    chunk_idx = chunk_index_tracker[doc_id]
    word_count = max(1, len(text.split()))

    cur.execute("""
        INSERT INTO chunks (doc_id, chunk_text, chunk_index, word_count)
        VALUES (%s, %s, %s, %s)
        RETURNING chunk_id
    """, (doc_id, text, chunk_idx, word_count))
    chunk_id = cur.fetchone()[0]

    vec = model.encode(text).tolist()
    vec_str = "[" + ",".join(str(x) for x in vec) + "]"
    cur.execute("""
        INSERT INTO embeddings (chunk_id, embedding)
        VALUES (%s, %s)
    """, (chunk_id, vec_str))

    if i % 100 == 0:
        conn.commit()
        print(f"  {i}/{len(sample)} chunks processed...")

conn.commit()
cur.close()
conn.close()
print("All done!")