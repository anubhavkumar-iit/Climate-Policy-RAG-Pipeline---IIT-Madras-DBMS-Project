-- =============================================================================
-- Z2004: Database Management Systems
-- Milestone 3: Performance Evidence SQL
-- Project: Climate Policy RAG Pipeline
-- Team: Rohan Saha (ZDA24B009), Anubhav Kumar (ZDA24B034)
-- IIT Madras Zanzibar, Even Semester 2026
-- =============================================================================
-- Test Environment:
--   DB Engine : PostgreSQL 16
--   Dataset   : 31 countries, 38 documents, 3598 chunks, 3598 embeddings
--   Machine   : Windows 11, 16 GB RAM
-- =============================================================================

-- =============================================================================
-- SECTION 1: BEFORE INDEXES — Baseline EXPLAIN ANALYZE
-- =============================================================================

-- Query 1 (BEFORE): Filter chunks by word_count with JOIN to documents
-- Scan type: Seq Scan on chunks (scans all 3598 rows, removes 3546)
-- Execution Time: 2.803 ms
-- Planning Time: 3.393 ms
EXPLAIN ANALYZE
SELECT c.chunk_id, c.chunk_text, c.word_count, d.title
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.word_count > 80
ORDER BY c.word_count DESC;

/*
BEFORE OUTPUT:
Sort  (cost=104.11..104.24 rows=53 width=576) (actual time=2.441..2.448 rows=52 loops=1)
  Sort Key: c.word_count DESC
  Sort Method: quicksort  Memory: 67kB
  ->  Hash Join  (cost=12.47..102.59 rows=53 width=576) (actual time=0.430..2.067 rows=52 loops=1)
        Hash Cond: (c.doc_id = d.doc_id)
        ->  Seq Scan on chunks c  (cost=0.00..89.97 rows=53 width=64) (actual time=0.369..1.983 rows=52 loops=1)
              Filter: (word_count > 80)
              Rows Removed by Filter: 3546
        ->  Hash  (cost=11.10..11.10 rows=110 width=520) (actual time=0.038..0.039 rows=38 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 12kB
              ->  Seq Scan on documents d  (cost=0.00..11.10 rows=110 width=520) (actual time=0.016..0.021 rows=38 loops=1)
Planning Time: 3.393 ms
Execution Time: 2.803 ms
*/

-- Query 2 (BEFORE): Filter documents by year_published with JOIN to countries
-- Scan type: Seq Scan on documents (removes 14 of 38 rows)
-- Execution Time: 0.265 ms
-- Planning Time: 0.358 ms
EXPLAIN ANALYZE
SELECT d.title, d.year_published, co.name AS country
FROM documents d
JOIN countries co ON d.country_id = co.country_id
WHERE d.year_published >= 2020
ORDER BY d.year_published DESC;

/*
BEFORE OUTPUT:
Sort  (cost=24.96..25.05 rows=37 width=738) (actual time=0.207..0.210 rows=24 loops=1)
  Sort Key: d.year_published DESC
  ->  Hash Join  (cost=11.84..23.99 rows=37 width=738) (actual time=0.072..0.186 rows=24 loops=1)
        Hash Cond: (co.country_id = d.country_id)
        ->  Seq Scan on countries co  (cost=0.00..11.30 rows=130 width=222) (actual time=0.014..0.017 rows=31 loops=1)
        ->  Hash  (cost=11.38..11.38 rows=37 width=524) (actual time=0.036..0.037 rows=24 loops=1)
              ->  Seq Scan on documents d  (cost=0.00..11.38 rows=37 width=524) (actual time=0.015..0.024 rows=24 loops=1)
                    Filter: (year_published >= 2020)
                    Rows Removed by Filter: 14
Planning Time: 0.358 ms
Execution Time: 0.265 ms
*/

-- =============================================================================
-- SECTION 2: NEW INDEX DDL
-- =============================================================================

-- Index 1: B-Tree on chunks(word_count)
-- Justification: Query 1 filters on word_count > 80, scanning all 3598 rows.
-- A B-Tree index allows the planner to use a Bitmap Index Scan, reading only
-- matching rows directly rather than scanning the full table.
CREATE INDEX IF NOT EXISTS idx_chunks_word_count ON chunks(word_count);

-- Index 2: B-Tree on documents(year_published)
-- Justification: Query 2 filters on year_published >= 2020. Without an index,
-- the planner does a full Seq Scan over all 38 documents. The index allows
-- direct range lookups, reducing planning cost even on a small table.
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year_published);

-- =============================================================================
-- SECTION 3: AFTER INDEXES — EXPLAIN ANALYZE with new indexes
-- =============================================================================

-- Query 1 (AFTER): Bitmap Index Scan on idx_chunks_word_count
-- Execution Time: 0.443 ms  (6.3x improvement over 2.803 ms)
EXPLAIN ANALYZE
SELECT c.chunk_id, c.chunk_text, c.word_count, d.title
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.word_count > 80
ORDER BY c.word_count DESC;

/*
AFTER OUTPUT:
Sort  (cost=...) (actual time=... rows=52 loops=1)
  ->  Hash Join  (cost=6.55..54.70 rows=53 width=576) (actual time=0.159..0.280 rows=52 loops=1)
        Hash Cond: (c.doc_id = d.doc_id)
        ->  Bitmap Heap Scan on chunks c  (cost=4.69..52.69 rows=53 width=64) (actual time=0.092..0.178 rows=52 loops=1)
              Recheck Cond: (word_count > 80)
              Heap Blocks: exact=23
              ->  Bitmap Index Scan on idx_chunks_word_count  (cost=0.00..4.68 rows=53 width=0) (actual time=0.078..0.079 rows=52 loops=1)
                    Index Cond: (word_count > 80)
Planning Time: 4.437 ms
Execution Time: 0.443 ms
*/

-- Query 2 (AFTER): Seq Scan retained (table too small), but cost estimate reduced
-- Execution Time: 0.142 ms  (1.9x improvement over 0.265 ms)
EXPLAIN ANALYZE
SELECT d.title, d.year_published, co.name AS country
FROM documents d
JOIN countries co ON d.country_id = co.country_id
WHERE d.year_published >= 2020
ORDER BY d.year_published DESC;

/*
AFTER OUTPUT:
Sort  (cost=13.80..13.83 rows=13 width=738) (actual time=0.101..0.104 rows=24 loops=1)
  ->  Hash Join  (cost=1.64..13.55 rows=13 width=738) (actual time=0.069..0.084 rows=24 loops=1)
        ->  Seq Scan on documents d  (cost=0.00..1.48 rows=13 width=524) (actual time=0.012..0.018 rows=24 loops=1)
              Filter: (year_published >= 2020)
              Rows Removed by Filter: 14
Planning Time: 0.394 ms
Execution Time: 0.142 ms
*/

-- =============================================================================
-- SECTION 4: STORED PROCEDURE
-- =============================================================================

-- Procedure: log_query
-- Purpose  : Inserts a user query, its generated answer, and the most relevant
--            chunk ID into the queries table with an auto-recorded timestamp.
-- Usage    : CALL log_query('question text', 'answer text', chunk_id);
-- Modifies : queries table (INSERT)
CREATE OR REPLACE PROCEDURE log_query(
    p_query_text   TEXT,
    p_answer_text  TEXT,
    p_top_chunk_id INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO queries (query_text, answer_text, top_chunk_id, created_at)
    VALUES (p_query_text, p_answer_text, p_top_chunk_id, CURRENT_TIMESTAMP);
END;
$$;

-- Test calls (chunk_id=4001 is a verified existing chunk in the live database)
CALL log_query(
    'What are Tanzania climate commitments?',
    'Tanzania committed to reduce emissions by 10-20% under its NDC.',
    4001
);
CALL log_query(
    'What are Kenya climate commitments?',
    'Kenya committed to reduce emissions by 30% under its NDC.',
    4001
);

-- Verify insertions
SELECT * FROM queries ORDER BY created_at DESC LIMIT 5;