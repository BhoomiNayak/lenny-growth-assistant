"""Transcript ingestion pipeline for The Lenny Growth Assistant.

Parses YAML frontmatter, chunks transcript text, generates embeddings
via Ollama (nomic-embed-text), and upserts into PostgreSQL + pgvector.

Usage:
    python scripts/ingest_transcripts.py
    python scripts/ingest_transcripts.py --limit 10
    python scripts/ingest_transcripts.py --data-dir ./data/transcripts/episodes
"""

import argparse
import asyncio
import sys
import time
from datetime import date
from pathlib import Path

import httpx
import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import settings  # noqa: E402
# Shared chunking/parsing logic (single source of truth, also unit-tested)
from app.utils.chunking import chunk_text, parse_transcript  # noqa: E402,F401


# ─── Configuration ─────────────────────────────────────────────────────────────

EMBEDDING_DIMENSION = 768
BATCH_SIZE = 20  # embeddings batch size


# ─── (parse_transcript / chunk_text imported from app.utils.chunking) ───────────


# ─── Embedding Generation ──────────────────────────────────────────────────────


async def generate_embeddings(texts: list[str], ollama_url: str, model: str) -> list[list[float]]:
    """Generate embeddings for a batch of texts using Ollama."""
    embeddings = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for text_item in texts:
            # Truncate very long texts to avoid Ollama issues
            truncated = text_item[:8000]
            try:
                resp = await client.post(
                    f"{ollama_url}/api/embed",
                    json={"model": model, "input": truncated},
                )
                resp.raise_for_status()
                data = resp.json()
                emb = data.get("embeddings", [[]])[0]
                if emb:
                    embeddings.append(emb)
                else:
                    embeddings.append([0.0] * EMBEDDING_DIMENSION)
            except Exception as e:
                print(f"  [WARN] Embedding failed: {e}")
                embeddings.append([0.0] * EMBEDDING_DIMENSION)
    return embeddings


# ─── Database Operations ───────────────────────────────────────────────────────


async def upsert_chunks(
    session: AsyncSession,
    episode_id: str,
    guest: str,
    title: str,
    youtube_url: str | None,
    publish_date: date | None,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    """Upsert transcript chunks with embeddings into the database."""
    inserted = 0
    for idx, (chunk_text_val, embedding) in enumerate(zip(chunks, embeddings)):
        # Format embedding as pgvector-compatible string literal
        embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

        stmt = text("""
            INSERT INTO transcript_chunks
                (episode_id, guest, episode_title, youtube_url, publish_date, chunk_index, content, embedding, metadata)
            VALUES
                (:episode_id, :guest, :episode_title, :youtube_url, :publish_date, :chunk_index, :content, cast(:embedding as vector), cast(:metadata as jsonb))
            ON CONFLICT ON CONSTRAINT uq_episode_chunk
            DO UPDATE SET
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                guest = EXCLUDED.guest,
                episode_title = EXCLUDED.episode_title,
                youtube_url = EXCLUDED.youtube_url
        """)

        await session.execute(stmt, {
            "episode_id": episode_id,
            "guest": guest,
            "episode_title": title,
            "youtube_url": youtube_url,
            "publish_date": publish_date,
            "chunk_index": idx,
            "content": chunk_text_val,
            "embedding": embedding_literal,
            "metadata": "{}",
        })
        inserted += 1

    await session.commit()
    return inserted


# ─── Main Pipeline ─────────────────────────────────────────────────────────────


async def ingest_episode(
    session: AsyncSession,
    episode_dir: Path,
    ollama_url: str,
    embedding_model: str,
) -> tuple[int, int]:
    """Ingest a single episode: parse → chunk → embed → store.

    Returns (chunks_stored, 0) on success or (0, 1) on failure.
    """
    transcript_file = episode_dir / "transcript.md"
    if not transcript_file.exists():
        return 0, 0

    episode_id = episode_dir.name
    parsed = parse_transcript(transcript_file)
    if not parsed:
        return 0, 0

    metadata = parsed["metadata"]
    transcript = parsed["transcript"]

    guest = metadata.get("guest", episode_id.replace("-", " ").title())
    title = metadata.get("title", f"Episode: {guest}")
    youtube_url = metadata.get("youtube_url")
    pub_date_raw = metadata.get("publish_date")

    # Parse publish date
    pub_date = None
    if pub_date_raw:
        if isinstance(pub_date_raw, date):
            pub_date = pub_date_raw
        elif isinstance(pub_date_raw, str):
            try:
                from datetime import datetime
                pub_date = datetime.strptime(pub_date_raw, "%Y-%m-%d").date()
            except ValueError:
                pass

    # Chunk the transcript
    chunks = chunk_text(transcript)
    if not chunks:
        return 0, 0

    # Generate embeddings
    embeddings = await generate_embeddings(chunks, ollama_url, embedding_model)

    # Upsert to database
    stored = await upsert_chunks(
        session, episode_id, guest, title, youtube_url, pub_date, chunks, embeddings
    )

    return stored, 0


async def main():
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcripts")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=settings.TRANSCRIPT_DATA_DIR,
        help="Path to episodes directory",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of episodes to ingest (0 = all)",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default=settings.OLLAMA_BASE_URL,
        help="Ollama API base URL",
    )
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=settings.OLLAMA_EMBEDDING_MODEL,
        help="Embedding model name",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=settings.DATABASE_URL,
        help="Database connection URL",
    )
    args = parser.parse_args()

    # Resolve data directory
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parent.parent / args.data_dir
    
    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        print("Run: git clone https://github.com/ChatPRD/lennys-podcast-transcripts.git data/transcripts")
        sys.exit(1)

    # Get episode directories
    episode_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    if args.limit > 0:
        episode_dirs = episode_dirs[: args.limit]

    print(f"═══════════════════════════════════════════════════════")
    print(f"  Lenny Growth Assistant — Transcript Ingestion")
    print(f"═══════════════════════════════════════════════════════")
    print(f"  Episodes to process: {len(episode_dirs)}")
    print(f"  Ollama URL: {args.ollama_url}")
    print(f"  Embedding model: {args.embedding_model}")
    print(f"  Database: {args.db_url.split('@')[-1] if '@' in args.db_url else 'local'}")
    print(f"═══════════════════════════════════════════════════════\n")

    # Verify Ollama is available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{args.ollama_url}/api/tags")
            resp.raise_for_status()
            print("✓ Ollama is reachable\n")
    except Exception as e:
        print(f"ERROR: Cannot reach Ollama at {args.ollama_url}: {e}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)

    # Create async engine
    engine = create_async_engine(args.db_url, pool_size=5)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_chunks = 0
    total_errors = 0
    start_time = time.time()

    async with async_session() as session:
        for i, episode_dir in enumerate(episode_dirs, 1):
            episode_name = episode_dir.name
            print(f"  [{i}/{len(episode_dirs)}] {episode_name}...", end=" ", flush=True)

            try:
                chunks_stored, errors = await ingest_episode(
                    session, episode_dir, args.ollama_url, args.embedding_model
                )
                total_chunks += chunks_stored
                total_errors += errors

                if chunks_stored > 0:
                    print(f"✓ {chunks_stored} chunks")
                else:
                    print("⊘ skipped (empty/too short)")
            except Exception as e:
                total_errors += 1
                print(f"✗ ERROR: {e}")

    # Rebuild the IVFFlat index now that data is loaded.
    # Building it here (not in the migration) ensures the cluster centroids are
    # computed from real embeddings. lists ~= sqrt(row_count) is a good heuristic.
    if total_chunks > 0:
        print("\n  Building IVFFlat index (this improves search speed at scale)...")
        try:
            async with engine.begin() as conn:
                # Count total rows to size the index
                count_result = await conn.execute(
                    text("SELECT count(*) FROM transcript_chunks WHERE embedding IS NOT NULL")
                )
                row_count = count_result.scalar() or 0
                lists = max(1, min(1000, int(row_count ** 0.5)))
                assert isinstance(lists, int), "lists must be an integer"

                await conn.execute(text("DROP INDEX IF EXISTS idx_transcript_chunks_embedding"))
                # Note: DDL statements don't support parameterized values for WITH options.
                # Safety: `lists` is derived from count(*) and bounded by max(1, min(1000, ...)).
                await conn.execute(
                    text(
                        "CREATE INDEX idx_transcript_chunks_embedding "
                        "ON transcript_chunks USING ivfflat (embedding vector_cosine_ops) "
                        f"WITH (lists = {int(lists)})"
                    )
                )
            print(f"  ✓ Index built with lists={lists} over {row_count} chunks")
        except Exception as e:
            print(f"  [WARN] Index build failed (exact search will be used): {e}")

    await engine.dispose()

    elapsed = time.time() - start_time
    print(f"\n═══════════════════════════════════════════════════════")
    print(f"  Ingestion Complete")
    print(f"═══════════════════════════════════════════════════════")
    print(f"  Total chunks stored: {total_chunks}")
    print(f"  Errors: {total_errors}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"═══════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
