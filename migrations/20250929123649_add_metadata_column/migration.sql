-- CreateTable
CREATE TABLE "Document" (
    "id" SERIAL NOT NULL,
    "content" TEXT NOT NULL,
    "book_id" TEXT NOT NULL,
    "embedding" BYTEA NOT NULL,
    "metadata" JSONB NOT NULL,

    CONSTRAINT "Document_pkey" PRIMARY KEY ("id")
);
