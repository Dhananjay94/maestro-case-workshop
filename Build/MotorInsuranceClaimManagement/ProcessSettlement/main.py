"""ProcessSettlement: records the simulated payment in the SettlementRegister Data Fabric entity.

Writes to SettlementRegister BY NAME in the folder this function is deployed to; no IDs are written in code.
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


def find_one(entity_name: str, field: str, value: str):
    """First record of an entity (resolved BY NAME in the job's folder) where field == value, or None."""
    entity = sdk().entities.retrieve_by_name(entity_name, folder_key=job_folder_key())
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


class Input(BaseModel):
    DataFolder: str = ""  # optional folder name/path holding the solution data; empty = auto (this job's folder, then its sub-folders)
    ClaimId: str = ""
    CustomerName: str = ""
    PolicyNumber: str = ""
    SettlementAmount: float = 0
    SeniorApprovalRequired: bool = False
    SeniorApprovalDecision: str = ""


class Output(BaseModel):
    SettlementStatus: str = ""
    PaymentReference: str = ""
    SettlementDate: str = ""
    error_type: str = ""
    error_message: str = ""


@traced(name="process_settlement", run_type="uipath")
def process_settlement(input: Input) -> Output:
    out = Output()
    try:
        if not input.ClaimId.strip():
            out.error_type = "NO_CLAIM_ID"
            out.error_message = "ClaimId is empty."
            return out
        approval = (input.SeniorApprovalDecision or "Pending") if input.SeniorApprovalRequired else "NotRequired"
        if input.SeniorApprovalRequired and approval.strip().lower() != "approved":
            out.error_type = "APPROVAL_REQUIRED"
            out.error_message = f"Senior approval is required and the decision is '{approval}'. Settlement not paid."
            return out
        reference = f"PAY-{input.ClaimId.strip()}"
        today = date.today().isoformat()
        entity = sdk().entities.retrieve_by_name("SettlementRegister", folder_key=data_folder_key("SettlementRegister", input.DataFolder))
        # Idempotent: running the same claim again (a re-run, or a retried step) returns the existing payment instead of failing on the unique ClaimId.
        existing = sdk().entities.retrieve_records(
            entity_key=entity.id,
            filter_group=EntityQueryFilterGroup(
                logical_operator=LogicalOperator.And,
                query_filters=[EntityQueryFilter(field_name="ClaimId", operator=QueryFilterOperator.Equals, value=input.ClaimId.strip())],
            ),
            limit=1,
        )
        if existing.items:
            row = existing.items[0].model_extra or {}
            out.SettlementStatus = str(row.get("SettlementStatus") or "Paid")
            out.PaymentReference = str(row.get("PaymentReference") or reference)
            out.SettlementDate = str(row.get("SettlementDate") or today)[:10]
            return out
        sdk().entities.insert_record(
            entity_key=entity.id,
            data={
                "ClaimId": input.ClaimId.strip(),
                "CustomerName": input.CustomerName,
                "PolicyNumber": input.PolicyNumber,
                "SettlementAmount": input.SettlementAmount,
                "ApprovalStatus": approval,
                "SettlementStatus": "Paid",
                "PaymentReference": reference,
                "SettlementDate": today,
            },
        )
        out.SettlementStatus = "Paid"
        out.PaymentReference = reference
        out.SettlementDate = today
    except Exception as exc:
        out.error_type = "FAILED"
        out.error_message = str(exc)
    return out
