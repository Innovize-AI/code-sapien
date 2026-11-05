# Docling + Cloud Run Jobs + GCS Architecture

## Context

When a dashboard upload feature is needed (admin uploads PDFs → auto-indexed into Pinecone),
the seeding pipeline needs to move from CLI scripts to a cloud-hosted background job.

## Why Docling over current stack

Current: PyMuPDF (text extraction) + Gemini Vision OCR (image pages)
Docling: single library, handles both — plus structure-aware output (tables, headings, lists preserved as Markdown)

Better chunk quality for school documents: fee tables, curriculum grids, admission checklists stay coherent instead of being flattened into a word-split blob.

**Only used in the seed/indexing pipeline — not in the production FastAPI server.**

## Architecture

```
Admin uploads PDF via dashboard
  → FastAPI stores file in Supabase Storage
  → API triggers Cloud Run Job (async, returns immediately)
  → Job: Docling parse → chunk → embed → Pinecone upsert
  → Job writes status to indexing_jobs Supabase table
  → Dashboard polls status → shows ✓ Indexed / ⏳ Processing / ✗ Failed
```

## Model persistence via GCS

Docling downloads ~1GB of ML models on first use. To avoid re-downloading on every job run:

1. Download models once locally
2. Upload to GCS: `gsutil -m cp -r ~/.cache/huggingface/ gs://saarthi-models/docling/`
3. Mount GCS bucket in Cloud Run Job at `/root/.cache/huggingface/` via Cloud Storage FUSE

Docker image stays lean (~500MB). Models load from GCS at job startup (~30-60s).

### GCS mount vs baking into image

| | GCS mount | Baked into image |
|---|---|---|
| Image size | ~500MB | ~3-4GB |
| First model access | ~30-60s (GCS read) | Instant |
| Model updates | Re-upload to GCS only | Rebuild + push image |
| CI/CD build time | Fast | Slow |

**Decision: GCS mount** — job runs infrequently (few times/month), startup latency acceptable.
Model updates don't require image rebuilds. Image stays deployable without pulling 3GB.

## FAQ management

FAQs stay in Pinecone as the search index (semantic search is the point).
For dashboard CRUD: upsert/delete to Pinecone directly from the API on save.
No Supabase table needed unless you want a human-readable list view — optional.

## When to build this

Not now. DWPS has a handful of documents that change rarely.
CLI scripts (`upload_resource.py`, `seed_pinecone_knowledge.py`) are sufficient for v1.

Build the dashboard upload UI when the client asks for self-serve document management.
At that point: Cloud Run Job image + GCS model bucket is the right approach.
