"""
These tests cover the parts of the pipeline that don't need a live DB or
embedding client: schemas, loaders, and chunking. Once repo access lands,
add tests for ingest_document()'s insert/update/skip behavior against a
real (or test) pgvector instance, and mock the embedding call.
"""
 
from __future__ import annotations
 
import pytest
 
from app.schemas.knowledge import (
    Document,
    DocumentMetadata,
    MaterialType,
    compute_content_hash,
)
from app.ingestion.loader import load_material, FAQLoader
from app.kb.store import chunk_document, _chunk_fixed_size
 
 
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
 
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
def onboarding_file(tmp_path):
    content = "Welcome to the program. " * 50  # long prose, no blank-line structure
    path = tmp_path / "onboarding_notes.md"
    path.write_text(content, encoding="utf-8")
    return path
 
 
# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------
 
def test_content_hash_is_stable_for_same_text():
    assert compute_content_hash("hello world") == compute_content_hash("hello world")
 
 
def test_content_hash_changes_when_text_changes():
    assert compute_content_hash("hello world") != compute_content_hash("hello there")
 
 
def test_document_create_computes_hash_automatically():
    metadata = DocumentMetadata(title="T", source="s", type=MaterialType.FAQ, cohort="c1")
    doc = Document.create(id="c1:faq:t", raw_text="some text", metadata=metadata)
    assert doc.content_hash == compute_content_hash("some text")
 
 
# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------
 
def test_faq_loader_returns_document_with_correct_metadata(faq_file):
    doc = FAQLoader().load(faq_file, cohort="cohort-2026-a")
 
    assert doc.metadata.type == MaterialType.FAQ
    assert doc.metadata.cohort == "cohort-2026-a"
    assert doc.metadata.source == str(faq_file)
    assert doc.metadata.title  # non-empty
    assert doc.raw_text  # file content loaded
 
 
def test_load_material_dispatches_by_type(faq_file):
    doc = load_material(faq_file, MaterialType.FAQ, cohort="cohort-2026-a")
    assert doc.metadata.type == MaterialType.FAQ
 
 
def test_program_doc_loader_is_registered(tmp_path):
    """Regression test: PROGRAM_DOC is in MaterialType but was previously
    missing from LOADERS, causing load_material(..., PROGRAM_DOC, ...) to
    raise KeyError. Confirms it now dispatches correctly."""
    path = tmp_path / "curriculum_overview.md"
    path.write_text("Program overview content.", encoding="utf-8")
 
    doc = load_material(path, MaterialType.PROGRAM_DOC, cohort="cohort-a")
 
    assert doc.metadata.type == MaterialType.PROGRAM_DOC
    assert doc.raw_text == "Program overview content."
 
 
def test_document_id_is_scoped_to_cohort_and_type(faq_file):
    doc_a = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    doc_b = load_material(faq_file, MaterialType.FAQ, cohort="cohort-b")
    # Same source file, different cohort -> different document identity.
    assert doc_a.id != doc_b.id
 
 
def test_reloading_same_file_produces_same_content_hash(faq_file):
    doc1 = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    doc2 = load_material(faq_file, MaterialType.FAQ, cohort="cohort-a")
    # Same id and same hash -> this is what update-not-duplicate keys off.
    assert doc1.id == doc2.id
    assert doc1.content_hash == doc2.content_hash
 
 
# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------
 
def test_faq_chunks_split_on_qa_blocks(faq_file):
    doc = FAQLoader().load(faq_file, cohort="cohort-a")
    chunks = chunk_document(doc)
 
    assert len(chunks) == 2  # two Q/A blocks in the fixture
    assert all(c.document_id == doc.id for c in chunks)
    assert all(c.metadata.cohort == "cohort-a" for c in chunks)
 
 
def test_chunks_retain_parent_metadata(faq_file):
    doc = FAQLoader().load(faq_file, cohort="cohort-a")
    chunks = chunk_document(doc)
 
    for chunk in chunks:
        assert chunk.metadata.title == doc.metadata.title
        assert chunk.metadata.source == doc.metadata.source
        assert chunk.metadata.type == doc.metadata.type
        assert chunk.metadata.cohort == doc.metadata.cohort
 
 
def test_fixed_size_chunking_respects_size_and_overlap():
    text = "x" * 1000
    chunks = _chunk_fixed_size(text, size=300, overlap=50)
 
    assert len(chunks) > 1
    # Each chunk except possibly the last should be close to `size`.
    assert all(len(c) <= 300 for c in chunks)
 
 
def test_fixed_size_chunking_rejects_overlap_greater_than_size():
    with pytest.raises(ValueError):
        _chunk_fixed_size("some text", size=100, overlap=150)
 
 
def test_chunk_indices_are_sequential(onboarding_file):
    from app.ingestion.loader import OnboardingNoteLoader
 
    doc = OnboardingNoteLoader().load(onboarding_file, cohort="cohort-a")
    chunks = chunk_document(doc)
 
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert [c.id for c in chunks] == [f"{doc.id}:{i}" for i in range(len(chunks))]