"""
Ingest text/markdown documents into the RAG knowledge base.
Chunks documents into overlapping segments, embeds with Gemini, stores in DocumentChunk.

Usage:
  python manage.py ingest_rag_docs                    # ingest from knowledge_base/ in project root
  python manage.py ingest_rag_docs path/to/folder
  python manage.py ingest_rag_docs path/to/file.txt
"""
import json
import os
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from users.models import DocumentChunk
from users.rag import embed_text


CHUNK_SIZE = 600
CHUNK_OVERLAP = 100


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks by character count, trying to break on sentences."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunk = text[start:].strip()
        else:
            # Prefer breaking at sentence end
            segment = text[start:end]
            last_period = max(
                segment.rfind(". "),
                segment.rfind(".\n"),
                segment.rfind("? "),
                segment.rfind("! "),
            )
            if last_period > chunk_size // 2:
                end = start + last_period + 1
            chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def read_file(path):
    """Read file as UTF-8 text."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        print(f"  Read error {path}: {e}")
        return None


def collect_files(path):
    """Collect .txt and .md files from a path (file or directory)."""
    path = Path(path).resolve()
    if path.is_file():
        if path.suffix.lower() in (".txt", ".md"):
            return [path]
        return []
    if path.is_dir():
        files = []
        for p in path.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".txt", ".md"):
                files.append(p)
        return sorted(files)
    return []


class Command(BaseCommand):
    help = "Ingest documents from a folder or file into the RAG knowledge base (DocumentChunk)."

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default=None,
            help="Path to a folder or a single .txt/.md file. Default: knowledge_base/ in project root.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "GOOGLE_API_KEY", None):
            self.stderr.write(self.style.ERROR("GOOGLE_API_KEY not set. Set it in .env to use embeddings."))
            return

        base_dir = Path(settings.BASE_DIR)
        path_arg = options.get("path")
        if path_arg:
            search_path = Path(path_arg)
            if not search_path.is_absolute():
                search_path = base_dir / path_arg
        else:
            search_path = base_dir / "knowledge_base"
            if not search_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"Default path '{search_path}' not found. Creating it with a sample file."
                    )
                )
                search_path.mkdir(parents=True, exist_ok=True)
                sample = search_path / "sample_medical.txt"
                sample.write_text(
                    "Diabetes is a condition where blood sugar levels are too high. "
                    "Type 2 diabetes can often be managed with diet, exercise, and medication. "
                    "Always follow your doctor's advice and monitor your glucose levels.\n\n"
                    "Hypertension (high blood pressure) increases risk of heart disease and stroke. "
                    "Reducing sodium, exercising regularly, and maintaining a healthy weight can help.",
                    encoding="utf-8",
                )
                self.stdout.write(f"Created sample file: {sample}")

        files = collect_files(search_path)
        if not files:
            self.stderr.write(self.style.ERROR(f"No .txt or .md files found at: {search_path}"))
            return

        total_chunks = 0
        for fp in files:
            text = read_file(fp)
            if not text:
                continue
            source_name = fp.name
            chunks = chunk_text(text)
            self.stdout.write(f"  {source_name}: {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                embedding = embed_text(chunk, task_type="retrieval_document")
                if embedding is None:
                    self.stderr.write(self.style.WARNING(f"    Skipped chunk {i+1} (embed failed)"))
                    continue
                DocumentChunk.objects.create(
                    source=source_name,
                    text=chunk,
                    embedding_json=json.dumps(embedding),
                )
                total_chunks += 1

        self.stdout.write(self.style.SUCCESS(f"Ingested {total_chunks} chunks from {len(files)} file(s)."))
