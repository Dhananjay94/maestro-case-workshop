"""FetchClaimDocumentText: downloads a claim's documents from the storage bucket and returns their text.

Deterministic coded function (no LLM). The document-intelligence agent calls it with the claim's
DocumentReferences (comma-separated bucket file names written by the Intake App) and reasons over
the returned text. Nothing is uploaded by hand and no attachments are passed between steps.

Limit: it reads the text layer of PDFs. Scanned images need OCR / Document Understanding instead.
"""
from __future__ import annotations

import os
import tempfile

from pydantic import BaseModel
from pypdf import PdfReader
from uipath.platform import UiPath
from uipath.tracing import traced

DEFAULT_BUCKET = "MotorInsuranceClaims-Documents"
MAX_CHARS_PER_FILE = 6000  # keeps the combined text within an agent prompt budget


class Input(BaseModel):
    claim_id: str = ""  # preferred: the function reads the claim's CURRENT DocumentReferences itself
    document_references: str = ""  # fallback when claim_id is empty: comma-separated bucket file names
    bucket_name: str = DEFAULT_BUCKET
    folder_path: str = ""  # optional override; empty = the folder this job runs in (the normal case)


class Output(BaseModel):
    combined_text: str = ""  # every document, each preceded by a "=== FILE: name ===" header
    document_count: int = 0
    failed_files: str = ""  # comma-separated names that could not be read, with the reason
    error_type: str = ""  # populated on failure, empty on success
    error_message: str = ""


# Lazy SDK singleton: never instantiate UiPath() at module level.
_sdk: UiPath | None = None


def sdk() -> UiPath:
    global _sdk
    if _sdk is None:
        _sdk = UiPath()
    return _sdk


def job_folder_key() -> str | None:
    """The folder this job runs in, from the execution context the platform sets (never written in code)."""
    return os.environ.get("UIPATH_FOLDER_KEY") or None


_folder_cache: dict[str, str | None] = {}


def data_folder_key(entity_name: str, folder: str = "") -> str | None:
    """Folder that holds the solution's data. Normally the folder this job runs in. When the job runs in a parent
    folder (for example the Studio Web personal workspace, which holds the deployed solution in a sub-folder),
    the entity is looked up in that folder's sub-folders instead. No folder name or ID is written in code."""
    if folder.strip():
        # Explicit folder (name or path) given by the caller: go straight there, no searching.
        key = sdk().folders.retrieve_folder_key(folder_path=folder.strip())
        if not key:
            raise RuntimeError(f"Folder '{folder}' was not found or is not accessible.")
        return key
    if entity_name in _folder_cache:
        return _folder_cache[entity_name]
    job = job_folder_key()
    found = job
    try:
        sdk().entities.retrieve_by_name(entity_name, folder_key=job)
    except Exception as first:
        try:
            found = _find_in_subfolders(entity_name, job)
        except RuntimeError:
            raise
        except Exception as second:
            raise RuntimeError(f"{first} || sub-folder search failed: {type(second).__name__}: {second}") from second
        if found is None:
            raise
    _folder_cache[entity_name] = found
    return found


def _find_in_subfolders(entity_name: str, parent_key: str | None) -> str | None:
    """Locate the folder holding the data when it is not in the folder this job runs in: first below the running
    folder, then anywhere else the user can access. Exactly one match is required; several is an error."""
    if not parent_key:
        return None
    resp = sdk().api_client.request(
        "GET", "/orchestrator_/api/FoldersNavigation/GetAllFoldersForCurrentUser", params={"skip": "0", "take": "1000"}
    )
    body = resp.json()
    rows = body if isinstance(body, list) else body.get("value", [])
    below: list[str] = []
    frontier = [parent_key]
    while frontier:
        nxt = [r["Key"] for r in rows if r.get("ParentKey") in frontier and r["Key"] not in below]
        below.extend(nxt)
        frontier = nxt

    def probe(keys: list[str]) -> list[str]:
        found: list[str] = []
        for key in keys:
            try:
                sdk().entities.retrieve_by_name(entity_name, folder_key=key)
                found.append(key)
            except Exception:
                pass
        return found

    hits = probe(below)
    if not hits:
        hits = probe([r["Key"] for r in rows if r["Key"] != parent_key and r["Key"] not in below])
    if len(hits) > 1:
        raise RuntimeError(
            f"Entity '{entity_name}' exists in {len(hits)} folders you can access; set the DataFolder input "
            "to the one to use, or run from the deployed solution folder."
        )
    return hits[0] if hits else None


def current_document_references(claim_id: str) -> str:
    """The claim row's DocumentReferences as stored right now (so documents added later are included)."""
    from uipath.platform.entities import (
        EntityQueryFilter,
        EntityQueryFilterGroup,
        LogicalOperator,
        QueryFilterOperator,
    )

    folder = data_folder_key("MotorInsuranceClaim")
    entity = sdk().entities.retrieve_by_name("MotorInsuranceClaim", folder_key=folder)
    result = sdk().entities.retrieve_records(
        entity_key=entity.id,
        filter_group=EntityQueryFilterGroup(
            logical_operator=LogicalOperator.And,
            query_filters=[
                EntityQueryFilter(field_name="ClaimId", operator=QueryFilterOperator.Equals, value=claim_id.strip())
            ],
        ),
        limit=1,
    )
    if not result.items:
        raise LookupError(f"Claim {claim_id} was not found.")
    row = result.items[0].model_extra or {}
    return str(row.get("DocumentReferences") or "")


def _pdf_text(path: str) -> str:
    reader = PdfReader(path)
    parts = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(p for p in parts if p).strip()


@traced(name="fetch_claim_document_text", run_type="uipath")
def fetch_claim_document_text(input: Input) -> Output:
    out = Output()
    try:
        raw = current_document_references(input.claim_id) if input.claim_id.strip() else input.document_references
        refs = [r.strip() for r in raw.split(",") if r.strip()]
        if not refs:
            out.error_type = "NO_DOCUMENTS"
            out.error_message = "The claim has no documents." if input.claim_id.strip() else "document_references is empty."
            return out

        sections: list[str] = []
        failed: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            for i, ref in enumerate(refs):
                local = os.path.join(tmp, f"doc_{i}.bin")
                try:
                    kwargs = {"name": input.bucket_name, "blob_file_path": ref, "destination_path": local}
                    if input.folder_path:
                        kwargs["folder_path"] = input.folder_path
                    else:
                        kwargs["folder_key"] = data_folder_key("MotorInsuranceClaim")
                    sdk().buckets.download(**kwargs)
                    text = _pdf_text(local)
                    if not text:
                        text = "[no extractable text: the file may be a scanned image]"
                    sections.append(f"=== FILE: {ref} ===\n{text[:MAX_CHARS_PER_FILE]}")
                except Exception as exc:  # per-file failure must not lose the other documents
                    failed.append(f"{ref} ({type(exc).__name__}: {exc})")

        out.combined_text = "\n\n".join(sections)
        out.document_count = len(sections)
        out.failed_files = "; ".join(failed)
        if not sections:
            out.error_type = "NO_DOCUMENT_READ"
            out.error_message = "None of the documents could be downloaded and read."
    except Exception as exc:
        out.error_type = "FAILED"
        out.error_message = str(exc)
    return out
