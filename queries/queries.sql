-- ============================================================
-- Z2004 Project Milestone 2 — queries.sql
-- Climate Policy RAG Pipeline
-- Rohan Saha (ZDA24B009) & Anubhav Kumar (ZDA24B034)
-- ============================================================

-- ── AGGREGATION 1 ──────────────────────────────────────────
-- Total chunks and average word count per document type
SELECT 
    d.doc_type,
    COUNT(c.chunk_id)          AS total_chunks,
    ROUND(AVG(c.word_count))   AS avg_word_count,
    MAX(c.word_count)          AS max_word_count,
    MIN(c.word_count)          AS min_word_count
FROM documents d
JOIN chunks c ON c.doc_id = d.doc_id
GROUP BY d.doc_type
ORDER BY total_chunks DESC;

-- ── AGGREGATION 2 ──────────────────────────────────────────
-- Number of documents and chunks per country
SELECT 
    co.name                        AS country,
    co.iso_code,
    COUNT(DISTINCT d.doc_id)       AS num_documents,
    COUNT(c.chunk_id)              AS num_chunks,
    ROUND(AVG(c.word_count))       AS avg_chunk_words
FROM countries co
JOIN documents d  ON d.country_id  = co.country_id
JOIN chunks c     ON c.doc_id      = d.doc_id
GROUP BY co.name, co.iso_code
ORDER BY num_chunks DESC;

-- ── JOIN 1 ─────────────────────────────────────────────────
-- Full chunk details with document and country info
SELECT 
    c.chunk_id,
    c.chunk_index,
    c.word_count,
    d.title        AS document_title,
    d.doc_type,
    d.year_published,
    co.name        AS country,
    co.iso_code
FROM chunks c
JOIN documents d  ON c.doc_id      = d.doc_id
JOIN countries co ON d.country_id  = co.country_id
ORDER BY co.name, d.year_published, c.chunk_index
LIMIT 100;

-- ── JOIN 2 ─────────────────────────────────────────────────
-- Chunks and their embedding status (LEFT JOIN)
SELECT 
    c.chunk_id,
    c.doc_id,
    c.word_count,
    CASE WHEN e.chunk_id IS NULL 
         THEN 'Missing' 
         ELSE 'Present' 
    END AS embedding_status
FROM chunks c
LEFT JOIN embeddings e ON e.chunk_id = c.chunk_id
ORDER BY embedding_status, c.chunk_id;

-- ── SUBQUERY 1 ─────────────────────────────────────────────
-- Documents whose average chunk word count exceeds global average
SELECT 
    d.doc_id,
    d.title,
    d.doc_type,
    ROUND(AVG(c.word_count)) AS avg_words
FROM documents d
JOIN chunks c ON c.doc_id = d.doc_id
GROUP BY d.doc_id, d.title, d.doc_type
HAVING AVG(c.word_count) > (
    SELECT AVG(word_count) FROM chunks
)
ORDER BY avg_words DESC;

-- ── SUBQUERY 2 ─────────────────────────────────────────────
-- Countries that have more than one document type
SELECT 
    co.name,
    co.iso_code
FROM countries co
WHERE co.country_id IN (
    SELECT d.country_id
    FROM documents d
    GROUP BY d.country_id
    HAVING COUNT(DISTINCT d.doc_type) > 1
)
ORDER BY co.name;

-- ── CTE 1 ──────────────────────────────────────────────────
-- Top 10 most data-rich documents by chunk count
WITH doc_stats AS (
    SELECT 
        d.doc_id,
        d.title,
        d.doc_type,
        d.year_published,
        co.name              AS country,
        COUNT(c.chunk_id)    AS chunk_count,
        SUM(c.word_count)    AS total_words,
        ROUND(AVG(c.word_count)) AS avg_words
    FROM documents d
    JOIN chunks c     ON c.doc_id     = d.doc_id
    JOIN countries co ON co.country_id = d.country_id
    GROUP BY d.doc_id, d.title, d.doc_type, d.year_published, co.name
)
SELECT * FROM doc_stats
ORDER BY chunk_count DESC
LIMIT 10;

-- ── CTE 2 ──────────────────────────────────────────────────
-- Country-level summary with above/below average classification
WITH country_stats AS (
    SELECT 
        co.name                  AS country,
        co.iso_code,
        COUNT(DISTINCT d.doc_id) AS num_docs,
        COUNT(c.chunk_id)        AS num_chunks
    FROM countries co
    JOIN documents d ON d.country_id = co.country_id
    JOIN chunks c    ON c.doc_id     = d.doc_id
    GROUP BY co.name, co.iso_code
),
avg_stats AS (
    SELECT ROUND(AVG(num_chunks)) AS avg_chunks FROM country_stats
)
SELECT 
    cs.country,
    cs.iso_code,
    cs.num_docs,
    cs.num_chunks,
    av.avg_chunks,
    CASE WHEN cs.num_chunks > av.avg_chunks 
         THEN 'Above Average' 
         ELSE 'Below Average' 
    END AS coverage_level
FROM country_stats cs
CROSS JOIN avg_stats av
ORDER BY cs.num_chunks DESC;

-- ── WINDOW FUNCTION 1 ───────────────────────────────────────
-- Rank chunks within each document by word count
SELECT 
    c.chunk_id,
    c.doc_id,
    c.word_count,
    d.title,
    RANK()       OVER (PARTITION BY c.doc_id ORDER BY c.word_count DESC) AS rank_in_doc,
    DENSE_RANK() OVER (PARTITION BY c.doc_id ORDER BY c.word_count DESC) AS dense_rank,
    NTILE(4)     OVER (PARTITION BY c.doc_id ORDER BY c.word_count)      AS quartile
FROM chunks c
JOIN documents d ON d.doc_id = c.doc_id;

-- ── WINDOW FUNCTION 2 ───────────────────────────────────────
-- Running total of chunks per country ordered by document year
SELECT 
    co.name              AS country,
    d.year_published,
    d.title,
    COUNT(c.chunk_id)    AS chunks_this_doc,
    SUM(COUNT(c.chunk_id)) OVER (
        PARTITION BY co.country_id
        ORDER BY d.year_published, d.doc_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                    AS running_chunk_total
FROM countries co
JOIN documents d ON d.country_id = co.country_id
JOIN chunks c    ON c.doc_id     = d.doc_id
GROUP BY co.country_id, co.name, d.year_published, d.doc_id, d.title
ORDER BY co.name, d.year_published;