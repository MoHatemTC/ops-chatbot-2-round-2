"""
These tests exercise ingest_document()'s insert/update/skip contract using
the throwaway in-memory fakes in scratch_fakes_storage.py — NOT the real
pgvector/embedding client, which don't exist yet.
"""
 
from __future__ import annotations
 
import pytest
 
from app.ingestion.loader import FAQLoader, load_material
from app.kb.store import ingest_document
from app.schemas.knowledge import MaterialType
from scratch_fakes_storage import InMemoryKnowledgeStore
 
 
@pytest.fixture
def faq_file(tmp_path):
    content = (
        "Q: When does the program start?\nA: Cohort kickoff is on the first Monday.\n\n"
        "Q: How do I request an extension?\nA: Message your mentor before the deadline.\n"
    )
    path = tmp_path / "onboarding_faq.md"
    path.write_text(content, encoding="utf-8")
    return path
 
 
@pytest.fixture
def store():
    return InMemoryKnowledgeStore()
 
 
def _ingest(document, store):
    return ingest_document(
        document,
        get_existing_hash=store.get_existing_hash,
        delete_chunks=store.delete_chunks,
        embed=store.fake_embed,
        store_chunks=store.store_chunks,
    )
 
 
def test_first_ingestion_inserts(faq_file, store):
    doc = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
 
    result = _ingest(doc, store)
 
    assert result == "inserted"
    assert store.get_existing_hash(doc.id) == doc.content_hash
    assert len(store.chunks_for(doc.id)) == 2  # two Q/A blocks
 
 
def test_reingesting_unchanged_content_skips(faq_file, store):
    doc = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    _ingest(doc, store)
 
    calls_before = store.embed_call_count
    result = _ingest(doc, store)  # same file, same content, re-ingested
 
    assert result == "skipped"
    assert store.embed_call_count == calls_before  # no wasted re-embedding
 
 
def test_reingesting_changed_content_updates(faq_file, store):
    doc_v1 = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    _ingest(doc_v1, store)
 
    # Simulate the source file being edited: same path/id, new content.
    faq_file.write_text(
        "Q: When does the program start?\nA: Kickoff moved to the second Monday.\n\n"
        "Q: How do I request an extension?\nA: Message your mentor before the deadline.\n\n"
        "Q: Who do I contact for admin questions?\nA: Contact the internship coordinator.\n",
        encoding="utf-8",
    )
    doc_v2 = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
 
    result = _ingest(doc_v2, store)
 
    assert result == "updated"
    assert doc_v1.id == doc_v2.id  # same identity
    assert doc_v1.content_hash != doc_v2.content_hash  # different content
    assert store.get_existing_hash(doc_v2.id) == doc_v2.content_hash
    # Old chunks were replaced, not appended to — exactly 3 blocks now, not 5.
    assert len(store.chunks_for(doc_v2.id)) == 3
 
 
def test_update_does_not_duplicate_across_multiple_reingestions(faq_file, store):
    doc = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    for _ in range(3):
        _ingest(doc, store)  # rerun the exact same ingestion three times
 
    assert len(store.chunks_for(doc.id)) == 2  # still just the original 2 chunks, never triplicated
 
 
def test_different_cohorts_are_independent_documents(faq_file, store):
    doc_a = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    doc_b = load_material(faq_file, MaterialType.FAQ, cohort="cohort-b")
 
    _ingest(doc_a, store)
    _ingest(doc_b, store)
 
    assert doc_a.id != doc_b.id
    assert len(store.chunks_for(doc_a.id)) == 2
    assert len(store.chunks_for(doc_b.id)) == 2  # cohort-b unaffected by cohort-a
 
 
def test_embedding_is_batched_not_per_chunk(faq_file, store):
    """The FAQ fixture produces 2 chunks; embedding them should take exactly
    ONE call to the embedder, not one call per chunk."""
    doc = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
 
    _ingest(doc, store)
 
    assert store.embed_call_count == 1
    assert len(store.chunks_for(doc.id)) == 2  # both chunks still stored correctly