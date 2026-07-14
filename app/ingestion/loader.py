"""Material loaders for the Knowledge Base ingestion pipeline.

This module converts supported source documents into normalized
Document objects used by the ingestion pipeline.

"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.knowledge import Document, DocumentMetadata, MaterialType


def _slugify(title: str) -> str:
    return title.strip().lower().replace(" ", "-")


def _document_id(cohort: str, material_type: MaterialType, title: str) -> str:
    # Stable identifier for update-not-duplicate lookups.
    return f"{cohort}:{material_type.value}:{_slugify(title)}"


class MaterialLoader(ABC):
    """Base interface every material loader implements.

    Single responsibility: turn one raw source file into a unified Document.
    Loaders must not chunk, embed, or touch storage.
    """

    material_type: MaterialType

    @abstractmethod
    def load(self, path: Path, cohort: str) -> Document:
        """Read a source file and return a populated document."""

    def _title_from_path(self, path: Path) -> str:
        return path.stem.replace("_", " ").replace("-", " ").title()

    def _build_document(
        self,
        path: Path,
        cohort: str,
        title: str,
        raw_text: str,
    ) -> Document:
        metadata = DocumentMetadata(
            title=title,
            source=str(path),
            type=self.material_type,
            cohort=cohort,
        )

        return Document.create(
            id=_document_id(cohort, self.material_type, title),
            raw_text=raw_text,
            metadata=metadata,
        )


class FAQLoader(MaterialLoader):
    """Loads FAQ documents."""

    material_type = MaterialType.FAQ

    def load(self, path: Path, cohort: str) -> Document:
        """Load a FAQ document from disk."""
        raw_text = path.read_text(encoding="utf-8")
        return self._build_document(
            path,
            cohort,
            self._title_from_path(path),
            raw_text,
        )


class OnboardingNoteLoader(MaterialLoader):
    """Loads onboarding notes."""

    material_type = MaterialType.ONBOARDING

    def load(self, path: Path, cohort: str) -> Document:
        """Load onboarding notes from disk."""
        raw_text = path.read_text(encoding="utf-8")
        return self._build_document(
            path,
            cohort,
            self._title_from_path(path),
            raw_text,
        )


class ScheduleLoader(MaterialLoader):
    """Loads schedule documents."""

    material_type = MaterialType.SCHEDULE

    def load(self, path: Path, cohort: str) -> Document:
        """Load a schedule document from disk."""
        raw_text = path.read_text(encoding="utf-8")
        return self._build_document(
            path,
            cohort,
            self._title_from_path(path),
            raw_text,
        )


LOADERS: dict[MaterialType, type[MaterialLoader]] = {
    MaterialType.FAQ: FAQLoader,
    MaterialType.ONBOARDING: OnboardingNoteLoader,
    MaterialType.SCHEDULE: ScheduleLoader,
}


def load_material(path: Path, material_type: MaterialType, cohort: str) -> Document:
    """Load a material using the appropriate loader."""
    loader_cls = LOADERS[material_type]
    return loader_cls().load(path, cohort)