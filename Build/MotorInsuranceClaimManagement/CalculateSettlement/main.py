"""CalculateSettlement: SettlementAmount = MIN(ClaimAmount, DamageEstimate, CoverageLimit) - Deductible.

Coverage limit comes from the PolicyMaster Data Fabric entity (read BY NAME in the job's folder).
The deductible and the senior-approval threshold are Orchestrator ASSETS in the same folder, so they are
business settings that can be changed without touching code; nothing is hardcoded here.
"""
from __future__ import annotations

import os
from datetime import date

from pydantic import BaseModel
from uipath.platform import UiPath
from uipath.platform.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    LogicalOperator,
    QueryFilterOperator,
)
from uipath.tracing import traced

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


def find_one(entity_name: str, field: str, value: str, folder: str = ""):
    """First record of an entity (resolved BY NAME in the job's folder) where field == value, or None."""
    entity = sdk().entities.retrieve_by_name(entity_name, folder_key=data_folder_key(entity_name, folder))
    result = sdk().entities.retrieve_records(
        entity_key=entity.id,
        filter_group=EntityQueryFilterGroup(
            logical_operator=LogicalOperator.And,
            query_filters=[EntityQueryFilter(field_name=field, operator=QueryFilterOperator.Equals, value=value)],
        ),
        limit=5,
    )
    return (result.items[0].model_extra or {}) if result.items else None


def to_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None

DEDUCTIBLE_ASSET = "ClaimsDeductible"
THRESHOLD_ASSET = "ClaimsSeniorApprovalThreshold"


class Input(BaseModel):
    DataFolder: str = ""  # optional folder name/path holding the solution data; empty = auto (this job's folder, then its sub-folders)
    PolicyNumber: str = ""
    ClaimAmount: float = 0
    DamageEstimate: float = 0


class Output(BaseModel):
    SettlementAmount: float = 0
    SeniorApprovalRequired: bool = False
    error_type: str = ""
    error_message: str = ""


def number_asset(name: str, folder: str = "") -> float:
    """Read a numeric Orchestrator asset from the job's folder. Never silently defaults: a missing value is an error."""
    asset = sdk().assets.retrieve(name, folder_key=data_folder_key("PolicyMaster", folder))
    if getattr(asset, "value_type", None) == "Integer" and getattr(asset, "int_value", None) is not None:
        return float(asset.int_value)
    for raw in (getattr(asset, "value", None), getattr(asset, "string_value", None)):
        if raw not in (None, ""):
            return float(raw)
    raise ValueError(f"Asset '{name}' has no value")


@traced(name="calculate_settlement", run_type="uipath")
def calculate_settlement(input: Input) -> Output:
    out = Output()
    try:
        policy = find_one("PolicyMaster", "PolicyNumber", input.PolicyNumber.strip(), input.DataFolder)
        if policy is None:
            out.error_type = "POLICY_NOT_FOUND"
            out.error_message = f"No policy {input.PolicyNumber} in PolicyMaster."
            return out
        limit = float(policy.get("CoverageLimit") or 0)
        deductible = number_asset(DEDUCTIBLE_ASSET, input.DataFolder)
        threshold = number_asset(THRESHOLD_ASSET, input.DataFolder)
        amount = max(0.0, min(float(input.ClaimAmount), float(input.DamageEstimate), limit) - deductible)
        out.SettlementAmount = amount
        out.SeniorApprovalRequired = amount > threshold
    except Exception as exc:
        out.error_type = "FAILED"
        out.error_message = str(exc)
    return out
