"""
CLI entry point that actually runs the ingestion pipeline over a folder of
approved materials — addresses mentor feedback: "you have per-file loading
and per-document ingest, but no entry point that points at a set of
approved materials and runs them all."
 
Convention (flag to mentor if a different layout is expected): materials
are organized in subfolders named after MaterialType values, e.g.
 
    materials/
      faq/
        onboarding_faq.md
      onboarding/
        welcome_notes.md
      schedule/
        cohort_a_schedule.md
      program_doc/
        curriculum_overview.md
 
Usage:
    python scripts/ingest_materials.py --materials-dir materials/ --cohort cohort-2026-a
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the repo root (parent of scripts/) is importable regardless of
# how this script is invoked (uv run, plain python, from a different cwd).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.loader import load_material
from app.kb.store import ingest_document
from app.schemas.knowledge import MaterialType
 
 
def iter_material_files(materials_dir: Path):
    """Yield (material_type, path) for every file under materials_dir,
    inferring type from the immediate parent folder name."""
    for material_type in MaterialType:
        type_dir = materials_dir / material_type.value
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*")):
            if path.is_file():
                yield material_type, path
 
 
def run_ingestion(materials_dir: Path, cohort: str) -> dict[str, int]:
    """Ingest every material file under materials_dir for the given cohort.
 
    Returns a summary count of inserted/updated/skipped/failed documents —
    printed at the end so a re-run is easy to sanity-check (re-running with
    no source changes should report all "skipped").
    """
    summary = {"inserted": 0, "updated": 0, "skipped": 0, "failed": 0}
 
    for material_type, path in iter_material_files(materials_dir):
        try:
            document = load_material(path, material_type, cohort)
            result = ingest_document(document)
            summary[result] += 1
            print(f"[{result}] {material_type.value}: {path.name}")
        except Exception as exc:  # noqa: BLE001 — surface and continue, don't abort the whole run
            summary["failed"] += 1
            print(f"[failed] {material_type.value}: {path.name} — {exc}")
 
    return summary
 
 
def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest approved materials into the knowledge base.")
    parser.add_argument(
        "--materials-dir",
        type=Path,
        required=True,
        help="Directory containing subfolders named after material types (faq/, onboarding/, schedule/, program_doc/).",
    )
    parser.add_argument("--cohort", type=str, required=True, help="Cohort these materials belong to.")
    args = parser.parse_args()
 
    if not args.materials_dir.is_dir():
        raise SystemExit(f"Materials directory not found: {args.materials_dir}")
 
    summary = run_ingestion(args.materials_dir, args.cohort)
 
    print("\n--- Ingestion summary ---")
    for key, count in summary.items():
        print(f"{key}: {count}")
 
 
if __name__ == "__main__":
    main()