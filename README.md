# Z2004 Milestone 2 — Climate Policy RAG Pipeline
**Group:** Rohan Saha (ZDA24B009), Anubhav Kumar (ZDA24B034)  
**Track:** A — RAG Pipeline  
**Due:** 15 May 2026, 23:59 EAT

---

## Dataset
- **Source:** ClimatePolicyRadar/all-document-text-data (Hugging Face, CC-BY 4.0)
- **URL:** https://huggingface.co/datasets/ClimatePolicyRadar/all-document-text-data
- **Rows loaded:** 3598 chunks from 38 documents across 31 countries
- **Embedding model:** all-MiniLM-L6-v2 (384 dimensions, stored as TEXT)

---

## Data Dictionary

### countries
| Column | Type | Meaning | Allowed Values |
|--------|------|---------|----------------|
| country_id | INTEGER | Auto-increment primary key | >0 |
| iso_code | VARCHAR(10) | ISO 3166-1 alpha-3 country code | e.g. TZA, IND, USA |
| name | VARCHAR(100) | Country name | string |
| region | VARCHAR(100) | Geographic region | nullable |
| continent | VARCHAR(50) | Continent | nullable |

### documents
| Column | Type | Meaning | Allowed Values |
|--------|------|---------|----------------|
| doc_id | INTEGER | Auto-increment primary key | >0 |
| title | VARCHAR(255) | Document title | string |
| country_id | INTEGER | FK to countries | valid country_id |
| doc_type | VARCHAR(50) | Type of climate document | NDC, Law, IPCC, IPBES |
| year_published | INTEGER | Publication year | 1990–2100 |
| source_url | TEXT | Original document URL | nullable |

### chunks
| Column | Type | Meaning | Allowed Values |
|--------|------|---------|----------------|
| chunk_id | INTEGER | Auto-increment primary key | >0 |
| doc_id | INTEGER | FK to documents | valid doc_id |
| chunk_text | TEXT | Raw passage text from document | string |
| chunk_index | INTEGER | Position of chunk within document | >0 |
| word_count | INTEGER | Number of words in chunk | >0 |

### embeddings
| Column | Type | Meaning | Allowed Values |
|--------|------|---------|----------------|
| embedding_id | INTEGER | Auto-increment primary key | >0 |
| chunk_id | INTEGER | FK to chunks (1-to-1) | valid chunk_id |
| embedding | TEXT | 384-dim vector from all-MiniLM-L6-v2 | "[f1,f2,...,f384]" |
| model_name | VARCHAR(100) | Embedding model used | all-MiniLM-L6-v2 |

---

## Setup and Reproduction Instructions

### Step 1 — Install dependencies
```bash
pip install datasets sentence-transformers psycopg2-binary pandas huggingface_hub
```

### Step 2 — Login to Hugging Face
```bash
python -c "from huggingface_hub import login; login()"
```
Get your token from: https://huggingface.co/settings/tokens  
Also accept dataset terms at: https://huggingface.co/datasets/ClimatePolicyRadar/all-document-text-data

### Step 3 — Create and set up the database
```bash
psql -U postgres -c "CREATE DATABASE climate_rag;"
psql -U postgres -d climate_rag -f schema.sql
```

### Step 4 — Run the ingestion script
```bash
python injest.py
```
This will download the dataset, insert countries, documents, chunks, and embeddings into the database. Expected output: 31 countries, 38 documents, 3598 chunks, 3598 embeddings.

### Step 5 — Run the SQL queries
```bash
psql -U postgres -d climate_rag -f queries.sql
```

---

## Query Coverage
| # | Type | Description |
|---|------|-------------|
| 1 | Aggregation | Chunks and word count statistics per document type |
| 2 | Aggregation | Number of documents and chunks per country |
| 3 | Join | Full chunk details joined with document and country info |
| 4 | Join | Chunks with embedding status using LEFT JOIN |
| 5 | Subquery | Documents above global average word count |
| 6 | Subquery | Countries with more than one document type |
| 7 | CTE | Top 10 documents by chunk count |
| 8 | CTE | Country coverage classification (above/below average) |
| 9 | Window Function | Chunk ranking within each document by word count |
| 10 | Window Function | Running total of chunks per country by year |

---

## AI Usage Disclosure
Claude (Anthropic) was used to assist with debugging column name mismatches. All code was manually written , reviewed, tested, and adapted by the team members.

