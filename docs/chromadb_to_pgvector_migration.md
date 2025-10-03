# Migrating from ChromaDB to Postgres + pgvector + Prisma

This guide explains how to migrate your vector search and metadata storage from ChromaDB to a robust Postgres setup using the pgvector extension and Prisma ORM.

## Why Migrate?
- **Unified storage**: Vectors and metadata in one database.
- **Scalability**: Postgres is production-ready and easy to scale.
- **Rich queries**: SQL for metadata and vector similarity.
- **LangChain support**: Integrates with modern LLM workflows.

## Migration Steps

### 1. Design Your Postgres Schema
Create a table with a `vector` column (pgvector type) and columns for metadata (e.g., text, book_id, etc.):

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    book_id TEXT,
    embedding VECTOR(1536) -- adjust dimension as needed
);
```

### 2. Set Up Prisma
- Add the table to your `schema.prisma`:

```prisma
model Document {
  id        Int     @id @default(autoincrement())
  content   String
  book_id   String
  embedding Bytes   // Use Prisma's Bytes for vector, then convert as needed
}
```
- Generate the Prisma client.

### 3. Export Data from ChromaDB
- Retrieve all vectors and metadata from ChromaDB.
- Save them in a format suitable for bulk import (e.g., CSV, JSON).

### 4. Import Data into Postgres
- Use Prisma or SQL scripts to insert vectors and metadata into your new table.
- Convert vectors to the pgvector format as needed.

### 5. Update Query Logic
- Replace ChromaDB search calls with SQL queries using pgvector similarity functions (e.g., cosine distance):

```sql
SELECT *, embedding <=> '[your_query_vector]' AS similarity
FROM documents
ORDER BY similarity ASC
LIMIT 5;
```
- Use Prisma to run these queries from your application.

### 6. Integrate with LangChain
- Use LangChain's Postgres/pgvector retriever for semantic search and RAG workflows.

## Tips
- Test with a small dataset first.
- Ensure vector dimensions match between ChromaDB and pgvector.
- Use transactions for bulk inserts to avoid partial migrations.

## References
- [pgvector documentation](https://github.com/pgvector/pgvector)
- [Prisma documentation](https://www.prisma.io/docs)
- [LangChain Postgres Retriever](https://python.langchain.com/docs/integrations/vectorstores/pgvector)

---
For questions or migration scripts, see the repo or contact the maintainer.
