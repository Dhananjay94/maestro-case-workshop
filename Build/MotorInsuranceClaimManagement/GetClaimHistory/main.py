"""GetClaimHistory: returns the insurer's internal claim history for a policy.

Deterministic coded function (no LLM). Reads the ClaimHistory Data Fabric entity BY NAME, in whichever
folder this function is deployed to: no folder or entity IDs are written anywhere in this code.
Used as a tool by the FraudRiskAssessment agent.
"""
from __future__ import annotations

import os

from pydantic import BaseModel
from uipath.platform import UiPath
from uipath.platform.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    LogicalOperator,
    QueryFilterOperator,
)
from uipath.tracing import traced

ENTITY_NAME = "ClaimHistory"


class Input(BaseModel):
    DataFolder: str = ""  # optional folder name/path holding the solution data; empty = auto (this job's folder, then its sub-folders)
    PolicyNumber: str = ""


class Output(BaseModel):
    PriorClaimCount: float = 0
    RecentSimilarClaimCount: float = 0
    LastClaimDate: str = ""
    HistoryRiskNote: str = ""
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


@traced(name="get_claim_history", run_type="uipath")
def get_claim_history(input: Input) -> Output:
    out = Output()
    try:
        policy = input.PolicyNumber.strip()
        if not policy:
            out.error_type = "NO_POLICY_NUMBER"
            out.error_message = "PolicyNumber is empty."
            return out
        # Resolve the entity BY NAME in the folder this job runs in; the ID is looked up, never stored.
        entity = sdk().entities.retrieve_by_name(ENTITY_NAME, folder_key=data_folder_key(ENTITY_NAME, input.DataFolder))
        result = sdk().entities.retrieve_records(
            entity_key=entity.id,
            filter_group=EntityQueryFilterGroup(
                logical_operator=LogicalOperator.And,
                query_filters=[
                    EntityQueryFilter(field_name="PolicyNumber", operator=QueryFilterOperator.Equals, value=policy)
                ],
            ),
            limit=5,
        )
        if not result.items:
            out.HistoryRiskNote = "No claim history record found for this policy."
            return out
        row = result.items[0].model_extra or {}
        out.PriorClaimCount = float(row.get("PriorClaimCount") or 0)
        out.RecentSimilarClaimCount = float(row.get("RecentSimilarClaimCount") or 0)
        out.LastClaimDate = str(row.get("LastClaimDate") or "")[:10]
        out.HistoryRiskNote = str(row.get("HistoryRiskNote") or "")
    except Exception as exc:
        out.error_type = "FAILED"
        out.error_message = str(exc)
    return out
