"""UpdateClaim: writes the case results of one stage back to the claim record (MotorInsuranceClaim) in Data Fabric.

The case calls it at the end of each stage with Stage = that stage; only the fields that belong to that stage are written.
The entity is found BY NAME in the folder this function runs in (or its data folder); no IDs are written in code.
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


# Which claim fields each stage owns. The case maps the matching outputs on the call; anything else is ignored.
STAGE_FIELDS: dict[str, list[str]] = {
    "Intake": ["DocumentIngestionStatus", "DocumentsComplete", "MissingDocuments", "DocumentInconsistencies", "PolicyValid",
               "PolicyValidationReason", "ExtractedCustomerName", "ExtractedPolicyNumber", "ExtractedVehicleRegistration",
               "ExtractedIncidentDate", "ExtractedDocumentTypes", "ExtractedRepairEstimate"],
    "Assessment": ["FraudScore", "RiskLevel", "FraudFlag", "FraudReasons", "DamageEstimate"],
    "FraudInvestigation": ["FraudInvestigationResult", "FraudInvestigationComments"],
    "Review": ["AdjusterDecision", "AdjusterComments"],
    "PendingCustomer": ["CustomerInformationStatus"],
    "SettlementCalculation": ["SettlementAmount", "SeniorApprovalRequired"],
    "Settlement": ["SeniorApprovalDecision", "SeniorApprovalComments", "SettlementStatus", "PaymentReference", "SettlementDate"],
    "Closure": ["ClaimPacketReference", "NotificationStatus", "ClaimOutcome"],
    "Denied": ["NotificationStatus", "ClaimOutcome", "SeniorApprovalDecision", "SeniorApprovalComments"],
}
BOOL_FIELDS = {"DocumentsComplete", "PolicyValid", "FraudFlag", "SeniorApprovalRequired"}
NUMBER_FIELDS = {"ExtractedRepairEstimate", "FraudScore", "DamageEstimate", "SettlementAmount"}
DATE_FIELDS = {"ExtractedIncidentDate", "SettlementDate"}
# Maximum text length the claim record accepts per field; longer values are trimmed instead of failing the update.
MAX_LENGTH = {
    "ClaimStatus": 50, "SeniorApprovalDecision": 50, "ClaimOutcome": 50, "CustomerInformationStatus": 50, "NotificationStatus": 50,
    "FraudInvestigationResult": 50, "AdjusterDecision": 50, "RiskLevel": 50, "SettlementStatus": 50, "DocumentIngestionStatus": 100,
    "ExtractedPolicyNumber": 200, "ExtractedVehicleRegistration": 200, "ExtractedCustomerName": 200, "PaymentReference": 200,
    "ClaimPacketReference": 1000,
}


def to_date(value) -> str | None:
    try:
        return date.fromisoformat(str(value)[:10]).isoformat()
    except Exception:
        return None


class Input(BaseModel):
    DataFolder: str = ""  # optional folder name/path holding the solution data; empty = auto (this job's folder, then its sub-folders)
    ClaimId: str = ""
    Stage: str = ""  # Intake, Assessment, FraudInvestigation, Review, PendingCustomer, SettlementCalculation, Settlement, Closure or Denied
    ClaimStatus: str = ""  # progress label shown on the claim record, set at every stage
    # Intake
    DocumentIngestionStatus: str = ""
    DocumentsComplete: bool = False
    MissingDocuments: str = ""
    DocumentInconsistencies: str = ""
    PolicyValid: bool = False
    PolicyValidationReason: str = ""
    ExtractedCustomerName: str = ""
    ExtractedPolicyNumber: str = ""
    ExtractedVehicleRegistration: str = ""
    ExtractedIncidentDate: str = ""
    ExtractedDocumentTypes: str = ""
    ExtractedRepairEstimate: float = 0
    # Assessment
    FraudScore: float = 0
    RiskLevel: str = ""
    FraudFlag: bool = False
    FraudReasons: str = ""
    DamageEstimate: float = 0
    # Fraud investigation
    FraudInvestigationResult: str = ""
    FraudInvestigationComments: str = ""
    # Review
    AdjusterDecision: str = ""
    AdjusterComments: str = ""
    # Pending customer
    CustomerInformationStatus: str = ""
    # Settlement
    SettlementAmount: float = 0
    SeniorApprovalRequired: bool = False
    SeniorApprovalDecision: str = ""
    SeniorApprovalComments: str = ""
    SettlementStatus: str = ""
    PaymentReference: str = ""
    SettlementDate: str = ""
    # Closure / denied
    ClaimPacketReference: str = ""
    NotificationStatus: str = ""
    ClaimOutcome: str = ""


class Output(BaseModel):
    Updated: bool = False
    FieldsWritten: str = ""
    error_type: str = ""
    error_message: str = ""


@traced(name="update_claim", run_type="uipath")
def update_claim(input: Input) -> Output:
    out = Output()
    try:
        claim_id = input.ClaimId.strip()
        if not claim_id:
            out.error_type = "NO_CLAIM_ID"
            out.error_message = "ClaimId is empty."
            return out
        if input.Stage not in STAGE_FIELDS:
            out.error_type = "UNKNOWN_STAGE"
            out.error_message = f"Stage '{input.Stage}' is not one of: {', '.join(STAGE_FIELDS)}."
            return out
        data: dict = {}
        if input.ClaimStatus.strip():
            data["ClaimStatus"] = input.ClaimStatus.strip()[: MAX_LENGTH["ClaimStatus"]]
        for field in STAGE_FIELDS[input.Stage]:
            value = getattr(input, field)
            if field in BOOL_FIELDS or field in NUMBER_FIELDS:
                data[field] = value
            elif field in DATE_FIELDS:
                parsed = to_date(value)
                if parsed:
                    data[field] = parsed
            elif str(value).strip() != "":
                data[field] = str(value)[: MAX_LENGTH.get(field, 9000)]
        if not data:
            out.error_type = "NOTHING_TO_WRITE"
            out.error_message = f"No values were supplied for stage '{input.Stage}'."
            return out
        entity = sdk().entities.retrieve_by_name("MotorInsuranceClaim", folder_key=data_folder_key("MotorInsuranceClaim", input.DataFolder))
        found = sdk().entities.retrieve_records(
            entity_key=entity.id,
            filter_group=EntityQueryFilterGroup(
                logical_operator=LogicalOperator.And,
                query_filters=[EntityQueryFilter(field_name="ClaimId", operator=QueryFilterOperator.Equals, value=claim_id)],
            ),
            limit=1,
        )
        if not found.items:
            out.error_type = "CLAIM_NOT_FOUND"
            out.error_message = f"No claim record with ClaimId '{claim_id}'."
            return out
        record_id = str(found.items[0].id or (found.items[0].model_extra or {}).get("Id"))
        sdk().entities.update_record(entity_key=entity.id, record_id=record_id, data=data)
        out.Updated = True
        out.FieldsWritten = ", ".join(data)
    except Exception as exc:
        out.error_type = "FAILED"
        out.error_message = str(exc)
    return out
