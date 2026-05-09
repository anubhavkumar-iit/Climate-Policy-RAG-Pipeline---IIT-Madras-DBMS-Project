-- =============================================================================
-- Z2004: Database Management Systems
-- Milestone 1: Schema DDL Script
-- Project: Climate Policy RAG Pipeline
-- Team: Rohan Saha (ZDA24B009), Anubhav Kumar (ZDA24B034)
-- IIT Madras Zanzibar, Even Semester 2026
-- =============================================================================
-- HOW TO RUN:
--   1. Open pgAdmin 4
--   2. Click on climate_rag database -> Tools -> Query Tool
--   3. Paste this entire file and press F5
-- NOTE: pgvector extension is installed separately before M2.
--       The embedding column uses TEXT for M1 and will be altered to
--       vector(384) once pgvector is installed for M2.
-- =============================================================================

-- =============================================================================
-- TABLE 1: countries
-- Stores one row per country.
-- Acts as the top-level dimension table for filtering documents by nation.
-- All country-specific attributes (region, continent) are stored here once
-- to avoid repeating them in every document row (3NF compliance).
-- =============================================================================
CREATE TABLE countries (
    country_id   SERIAL          PRIMARY KEY,
    name         VARCHAR(100)    NOT NULL,
    iso_code     CHAR(2)         NOT NULL UNIQUE,   -- e.g. TZ, KE, IN, US
    region       VARCHAR(100),                       -- e.g. East Africa
    continent    VARCHAR(50)                         -- e.g. Africa
);

-- =============================================================================
-- TABLE 2: documents
-- Stores one row per source document (NDC, climate law, IPCC report chapter).
-- Links to countries via country_id FK.
-- Document-level metadata is stored here, not repeated in every chunk.
-- =============================================================================
CREATE TABLE documents (
    doc_id          SERIAL          PRIMARY KEY,
    title           VARCHAR(255)    NOT NULL,
    country_id      INT             REFERENCES countries(country_id)
                                    ON DELETE SET NULL,
    -- ON DELETE SET NULL: if a country is deleted, document stays but
    -- loses its country link rather than being deleted entirely.
    doc_type        VARCHAR(50)     NOT NULL
                                    CHECK (doc_type IN ('NDC', 'Law', 'IPCC', 'IPBES')),
    -- CHECK ensures only valid document types are inserted.
    year_published  INT             CHECK (year_published BETWEEN 1990 AND 2100),
    -- CHECK prevents garbage year values outside the realistic range.
    source_url      TEXT
    -- Stores the original HuggingFace or UNFCCC URL for citations.
);

-- =============================================================================
-- TABLE 3: chunks
-- Stores the actual text passages extracted from documents.
-- This is the largest table (5000+ rows) and the core of the RAG system.
-- Documents are split into chunks because LLMs have token limits and
-- embeddings work better on short focused passages than full documents.
-- =============================================================================
CREATE TABLE chunks (
    chunk_id        SERIAL      PRIMARY KEY,
    doc_id          INT         NOT NULL
                                REFERENCES documents(doc_id)
                                ON DELETE CASCADE,
    -- ON DELETE CASCADE: deleting a document deletes all its chunks automatically.
    chunk_text      TEXT        NOT NULL,
    -- The raw text passage (typically 200-300 words).
    chunk_index     INT         NOT NULL,
    -- Position of this chunk within its parent document (1, 2, 3, ...).
    word_count      INT         CHECK (word_count > 0),
    -- Helps filter out empty or near-empty chunks during loading.

    CONSTRAINT uq_chunk_position UNIQUE (doc_id, chunk_index)
    -- Each position within a document must be unique.
);

-- =============================================================================
-- TABLE 4: embeddings
-- Stores the vector representation of each chunk.
-- NOTE: embedding column is TEXT for M1. It will be altered to vector(384)
-- after pgvector is installed for M2. The model used will be all-MiniLM-L6-v2
-- from sentence-transformers (384 dimensions).
-- =============================================================================
CREATE TABLE embeddings (
    embedding_id    SERIAL          PRIMARY KEY,
    chunk_id        INT             NOT NULL UNIQUE
                                    REFERENCES chunks(chunk_id)
                                    ON DELETE CASCADE,
    -- UNIQUE: exactly one embedding per chunk, no duplicates allowed.
    -- ON DELETE CASCADE: deleting a chunk deletes its embedding automatically.
    embedding       TEXT            NOT NULL,
    -- TEXT placeholder for M1. Will be altered to vector(384) in M2
    -- once pgvector extension is installed.
    model_name      VARCHAR(100)    NOT NULL DEFAULT 'all-MiniLM-L6-v2'
    -- Records which model generated the embedding.
);

-- =============================================================================
-- TABLE 5: queries
-- Logs every question asked by the user and the answer returned.
-- This is the innovation table -- most basic RAG systems do not log queries.
-- Enables analysis of user behaviour, debugging of bad answers, and
-- demonstration of system activity in the demo video.
-- =============================================================================
CREATE TABLE queries (
    query_id        SERIAL      PRIMARY KEY,
    query_text      TEXT        NOT NULL,
    -- The plain-English question asked by the user.
    answer_text     TEXT,
    -- The grounded answer returned by the system (NULL if unanswered).
    top_chunk_id    INT         REFERENCES chunks(chunk_id)
                                ON DELETE SET NULL,
    -- The most relevant chunk retrieved for this query (used for citations).
    created_at      TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
    -- Auto-records when the query was made.
);

-- =============================================================================
-- INDEXES
-- B-Tree indexes speed up JOIN operations between tables.
-- Required by Track A: at least one B-Tree index with EXPLAIN ANALYZE evidence.
-- =============================================================================

-- B-Tree index: speeds up queries filtering documents by country
CREATE INDEX idx_documents_country
    ON documents(country_id);

-- B-Tree index: speeds up queries fetching all chunks for a document
CREATE INDEX idx_chunks_doc
    ON chunks(doc_id);

-- B-Tree index: speeds up lookup of embedding by chunk
CREATE INDEX idx_embeddings_chunk
    ON embeddings(chunk_id);

-- B-Tree index: speeds up filtering by document type
CREATE INDEX idx_documents_type
    ON documents(doc_type);

-- NOTE: HNSW vector index will be added in M2 after pgvector is installed.

-- =============================================================================
-- 3NF VERIFICATION
-- -----------------------------------------------------------------------------
-- countries:  country_id -> name, iso_code, region, continent
--             All attributes depend only on country_id. No transitive deps.
--
-- documents:  doc_id -> title, country_id, doc_type, year_published, source_url
--             country_id is an FK, not a transitive dependency.
--             No non-key attribute determines another non-key attribute.
--
-- chunks:     chunk_id -> doc_id, chunk_text, chunk_index, word_count
--             doc_id is an FK. No transitive dependencies.
--
-- embeddings: embedding_id -> chunk_id, embedding, model_name
--             chunk_id is an FK (UNIQUE). No transitive dependencies.
--
-- queries:    query_id -> query_text, answer_text, top_chunk_id, created_at
--             top_chunk_id is an FK. No transitive dependencies.
--
-- All tables are in 1NF, 2NF, and 3NF.
-- =============================================================================

-- End of schema.sql