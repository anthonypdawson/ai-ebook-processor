# Setting Up Postgres + pgvector + Prisma with Poetry

This guide covers the steps to set up your database and Prisma client for a Python project using Poetry.

## 1. Install Dependencies

```bash
poetry add prisma
```

## 2. Create the Database Table

Connect to your Postgres instance and run:

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    book_id TEXT,
    embedding VECTOR(1536) -- adjust dimension as needed
);
```

## 3. Create `.env` File

Add your database connection string to a `.env` file in your project root:

```
DB_URL="postgresql://username:password@localhost:5432/your_database"
```

## 4. Create `schema.prisma` in Project Root

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DB_URL")
}

generator client {
  provider = "prisma-client-py"
}

model Document {
  id        Int     @id @default(autoincrement())
  content   String
  book_id   String
  embedding Bytes   // Use Bytes for vector, then convert as needed
}
```

## 5. Generate Prisma Client

```bash
poetry run prisma generate
```

## 6. (Optional) Introspect Existing Database

If you already have tables, you can auto-generate models:

```bash
poetry run prisma db pull
```

## 7. Usage Example

Import and use the Prisma client in your Python code:

```python
from prisma import Prisma

prisma = Prisma()
await prisma.connect()

# Example: create a document
await prisma.document.create({
    'content': 'Example text',
    'book_id': 'book123',
    'embedding': embedding_bytes  # Convert your vector to bytes
})

await prisma.disconnect()
```

---
For more details, see the Prisma and pgvector documentation.
