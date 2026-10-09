"""SetupWorkshop: sets up a participant's account for the Motor Claims Case workshop.

One function, three actions (type the action name in the input when you press Debug):

  InstallWorkshop  Creates the sign-in client the approval screens need and puts the "Motor Claims Workshop" solution
                   into your Studio Web (the solution you build in). Run this first, once.
  LoadData         Loads the demo policies and the claim history into the tables. Run it after you have pressed Debug
                   once on a case in the workshop solution (that is what creates the tables).
  RegisterClaim    Registers one sample claim (Rahul, Priya or Arjun) with its PDFs. Run it whenever you want a claim to test.

Each action only adds what is missing, so it is safe to run again. No folder, table or bucket ID is written in code.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

from pydantic import BaseModel
from uipath.platform import UiPath
from uipath.platform.entities import (
    EntityQueryFilter,
    EntityQueryFilterGroup,
    LogicalOperator,
    QueryFilterOperator,
)
from uipath.tracing import traced

ASSETS = Path(__file__).parent / "assets"
BUCKET = "MotorInsuranceClaims-Documents"
WORKSHOP_FILE = "MotorClaims_Workshop.uis"
CLIENT_PLACEHOLDER = "00000000-0000-4000-8000-000000000000"
ROUTING_PLACEHOLDER = "claims-placeholder"
CLIENT_NAME = "Motor Claims Workshop"
USER_SCOPES = ["OR.Buckets", "OR.Folders.Read", "DataFabric.Schema.Read", "DataFabric.Data.Read", "DataFabric.Data.Write"]


class Input(BaseModel):
    Action: str = "InstallWorkshop"  # InstallWorkshop | LoadData | RegisterClaim
    CustomerEmail: str = ""  # LoadData: where the demo customer emails go; empty = your own account email
    Customer: str = "Rahul"  # RegisterClaim: Rahul | Priya | Arjun
    ClientId: str = ""  # InstallWorkshop: use this sign-in client instead of creating one
    DataFolder: str = ""  # optional: folder name/path holding the tables; empty = find it automatically
    DeploymentName: str = ""  # InstallWorkshop: name of the environment folder; empty = ClaimsSolution. Only needed if a leftover with that name blocks it.


class Output(BaseModel):
    Report: str = ""
    error_type: str = ""
    error_message: str = ""


# Lazy SDK singleton: never instantiate UiPath() at module level.
_sdk: UiPath | None = None


def sdk() -> UiPath:
    global _sdk
    if _sdk is None:
        _sdk = UiPath()
    return _sdk


def job_folder_key() -> str | None:
    return os.environ.get("UIPATH_FOLDER_KEY") or None


def my_email() -> str:
    """The signed-in user's email: the personal workspace is named '<email>'s workspace'."""
    name = sdk().folders.get_personal_workspace().fully_qualified_name
    return name[: -len("'s workspace")] if name.endswith("'s workspace") else name


# ---------------------------------------------------------------- InstallWorkshop
PACKAGE = "MotorInsuranceClaimManagement"
BASE_NAME = "ClaimsSolution"
ENV = {"name": BASE_NAME}  # deployment and folder name actually used: BASE_NAME, or BASE_NAME2, 3... when a name is taken
PARENT = "Shared"
APPS = ["AdjusterReview", "FraudInvestigation", "SeniorApproval", "RequestCustomerInformation", "MotorInsuranceClaim_Intake"]
TERMINAL = {"DeploymentSucceeded", "DeploymentFailed", "ValidationFailed", "ConflictFixingError", "DeploymentScheduleError"}


def org_ids() -> tuple[str, str]:
    """(organization id, tenant id) from the execution context the platform sets."""
    return os.environ.get("UIPATH_ORGANIZATION_ID", ""), os.environ.get("UIPATH_TENANT_ID", "")


_ORG_NAME: dict[str, str] = {}


def org_name() -> str:
    """The organization's NAME (for example 'acme'), which the app addresses use. Inside a run the platform address carries the id instead,
    so ask the portal. Falls back to the address segment if the portal cannot be reached."""
    if "v" in _ORG_NAME:
        return _ORG_NAME["v"]
    name = ""
    try:
        info = jload(sdk().api_client.request("GET", "portal_/api/filtering/leftnav/tenantsAndOrganizationInfo", scoped="org"))
        name = (info.get("organization") or {}).get("name", "") if isinstance(info, dict) else ""
    except Exception:
        name = ""
    if not name:
        parts = os.environ.get("UIPATH_URL", "").rstrip("/").split("/")  # https://cloud.uipath.com/<org>/<tenant>
        name = parts[3] if len(parts) > 3 else ""
    _ORG_NAME["v"] = name
    return name


def solutions(method: str, path: str, **kw):
    """Call the Solutions service as the signed-in user."""
    return sdk().api_client.request(method, f"automationsolutions_/{path}", **kw)


T0 = time.time()


class Log:
    """The run's log. The Studio Web pane records the variables of every step, so this prints as a short label, never as the whole log."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, line: str) -> None:
        self.lines.append(line)

    def text(self) -> str:
        return chr(10).join(self.lines)

    def __repr__(self) -> str:
        return f"<log: {len(self.lines)} lines>"

    __str__ = __repr__

LOG_FOLDER: dict[str, str | None] = {"key": None}  # once set, every log line is also saved to a file in the bucket
LOG_FILE = "setup/setup-log.txt"


def say(log: Log, msg: str) -> None:
    """Log a line now (it shows in the run's log while the run is still going), keep it for the final report,
    and save the whole log to a file in the bucket so progress can be read from outside, even mid-run."""
    line = f"[{time.time() - T0:6.1f}s] {msg}"
    log.add(line)
    print(line, flush=True)
    sys.stdout.flush()
    if LOG_FOLDER["key"]:
        try:
            sdk().buckets.upload(name=BUCKET, blob_file_path=LOG_FILE, content=log.text(), content_type="text/plain", folder_key=LOG_FOLDER["key"])
        except Exception:
            pass


def jload(resp) -> object:
    """The response body as data. Some services return JSON wrapped in a string; unwrap it."""
    data = resp.json()
    while isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            break
    return data


def error_text(e: Exception) -> str:
    return getattr(getattr(e, "response", None), "text", "") or str(e)


def create_client(log: Log) -> str:
    """Create the sign-in client (External Application) the approval screens use, or reuse the one made by an earlier run."""
    org_id, tenant_id = org_ids()
    host = f"{org_name().lower().replace('_', '-')}.uipath.host"
    redirects = [f"https://{host}/action-**", f"https://{host}/{app_slug()}"]
    if org_id and tenant_id:
        redirects.append(f"https://cloud.uipath.com/{org_id}/{tenant_id}/actions_")
    existing = jload(sdk().api_client.request("GET", f"identity_/api/ExternalClient/{org_id}", scoped="org"))
    rows = existing if isinstance(existing, list) else existing.get("items", existing.get("value", []))
    for c in rows:
        if (c.get("name") or c.get("Name")) == CLIENT_NAME:
            cid = c.get("id") or c.get("Id")
            say(log, f"sign-in client already exists, reusing: {cid}")
            return cid
    body = {
        "partitionGlobalId": org_id,
        "name": CLIENT_NAME,
        "isConfidential": False,
        "redirectUri": ",".join(redirects),
        "scopes": [{"name": s, "type": "User"} for s in USER_SCOPES],
        "generateFirstSecret": False,
    }
    r = sdk().api_client.request("POST", "identity_/api/ExternalClient", scoped="org", json=body)
    data = jload(r)
    cid = data.get("id") or data.get("Id") or ""
    say(log, f"sign-in client created: {cid}")
    return cid


def patched_workshop(client_id: str) -> tuple[bytes, int]:
    out = io.BytesIO()
    patched = 0
    with zipfile.ZipFile(ASSETS / WORKSHOP_FILE) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".json") and (CLIENT_PLACEHOLDER.encode() in data or ROUTING_PLACEHOLDER.encode() in data):
                data = data.replace(CLIENT_PLACEHOLDER.encode(), client_id.encode()).replace(ROUTING_PLACEHOLDER.encode(), app_slug().encode())
                patched += 1
            zout.writestr(item, data)
    return out.getvalue(), patched


def app_slug() -> str:
    """The Intake App address, unique to this organization."""
    return f"claims-{org_name().lower().replace('_', '-')}"[:30]


def publish_package(log: Log) -> str:
    """Upload the worker package (workers, approval screens and the Intake App) to your solution feed."""
    pkg = sorted(ASSETS.glob(f"{PACKAGE}_*.zip"))[-1]
    version = pkg.stem.replace(f"{PACKAGE}_", "")
    say(log, f"uploading {pkg.name} ({pkg.stat().st_size // 1024} KB) to your solution feed...")
    try:
        solutions("POST", "v1/pipelines/packages", headers={"Content-Type": "application/zip"}, content=pkg.read_bytes(), timeout=300)
        say(log, f"package {PACKAGE} {version} uploaded")
    except Exception as e:
        text = error_text(e)
        if "exist" in text.lower() or "conflict" in text.lower() or "409" in text:
            say(log, f"package {version} is already published, continuing")
        else:
            raise RuntimeError(f"package upload failed: {text[:400]}") from e
    for _ in range(36):  # wait until the package is ready (up to 3 minutes)
        try:
            st = jload(solutions("GET", f"v1/pipelines/packages/{PACKAGE}/publish-status/{version}"))
            txt = json.dumps(st).lower()
            say(log, f"waiting for the package to be ready... ({txt[:100]})")
            if "fail" in txt:
                raise RuntimeError(f"package publish failed: {st}")
            if any(w in txt for w in ("complete", "ready", "active", "published", "succe")):
                break
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(5)
    return version


def deploy_package(client_id: str, version: str, log: Log) -> None:
    """Deploy the package into Shared/<name> and activate it. This creates the folder, tables, bucket, assets, workers, apps and the Intake App.
    One environment, one name. If a leftover deployment with that name blocks it, stop with a clear message (see the DeploymentName input)."""
    say(log, "reading the deployment settings...")
    cfg = jload(solutions("GET", f"v1/pipelines/packages/{PACKAGE}/config.json"))
    say(log, f"settings read: {len(cfg.get('resources', []))} resources")
    for res in cfg.get("resources", []):
        if res.get("name") in APPS:
            res.setdefault("configuration", {})["externalClientId"] = client_id
        if res.get("name") == "MotorInsuranceClaim_Intake":
            res.setdefault("configuration", {})["routingName"] = app_slug()
    status = ""
    detail: object = {}
    say(log, f"sending the deployment request: {ENV['name']} into {PARENT}/{ENV['name']}...")
    try:
        r = solutions(
            "POST",
            f"v1/pipelines/deployments/{ENV['name']}/deploy-from-package/{PACKAGE}/{version}/to-folder/{ENV['name']}",
            params={"folderFullyQualifiedName": PARENT},
            json=cfg,
            timeout=300,
        )
        pid = (jload(r) or {}).get("pipelineDeploymentId")
    except Exception as e:
        raise RuntimeError(
            f"The platform refused the deployment name '{ENV['name']}'. A leftover deployment with that name probably exists (open Orchestrator > Solutions > Deployments, "
            f"set the status filter to All and uninstall or delete it), or run Setup again with DeploymentName set to another name. Platform said: {error_text(e)[-300:]}"
        ) from e
    say(log, f"deployment started ({pid}), this takes a few minutes...")
    for i in range(180):  # up to 15 minutes
        detail = jload(solutions("GET", f"v1/pipelines/deployments/{pid}/deployment-status")) or {}
        status = detail.get("status", "") if isinstance(detail, dict) else ""
        if i % 3 == 0 or status in TERMINAL:
            say(log, f"deployment in progress, status: {status or '(starting)'}")
        if status in TERMINAL:
            break
        time.sleep(5)
    if status != "DeploymentSucceeded":
        say(log, f"platform detail: {json.dumps(detail)[:700]}")
        if status == "ValidationFailed":
            raise RuntimeError(
                f"The deployment name '{ENV['name']}' cannot be used: a leftover deployment with that name (even one whose folder was deleted) blocks it. "
                f"Uninstall or delete it in Orchestrator > Solutions > Deployments (status filter: All), or run Setup again with DeploymentName set to another name, for example {BASE_NAME}New."
            )
    say(log, f"deployment status: {status}")
    if status != "DeploymentSucceeded":
        raise RuntimeError(f"The deployment did not succeed (status: {status}). Platform message: {json.dumps(detail)[:600]}")
    try:
        solutions("POST", f"v1/pipelines/deployments/{ENV['name']}/activate")
        say(log, "deployment activated")
    except Exception as e:  # already active, or needs setup (connections): not fatal
        say(log, f"activation: {error_text(e)[:300]}")


def deployed_resources(fk: str, log: Log) -> dict[str, dict[str, str]]:
    """What the deployment created in the folder, by kind and name: {kind: {name: resource key}}.
    The platform's resource list can lag behind a fresh deployment, so keep looking until everything expected shows up (up to 3 minutes)."""
    from uipath.platform.resource_catalog import ResourceType

    kinds = (
        ("Process", ResourceType.PROCESS, 11),
        ("asset", ResourceType.ASSET, 2),
        ("bucket", ResourceType.BUCKET, 1),
        ("entity", ResourceType.ENTITY, 4),
        ("app", ResourceType.APP, 5),
    )
    found: dict[str, dict[str, str]] = {k: {} for k, _, _ in kinds}
    for attempt in range(1, 37):
        missing = []
        for kind, rtype, expected in kinds:
            if len(found[kind]) >= expected:
                continue
            try:
                for n, res in enumerate(sdk().resource_catalog.list_by_type(resource_type=rtype, folder_path=f"{PARENT}/{ENV['name']}", page_size=100)):
                    found[kind][res.name] = res.resource_key
                    if n >= 400:  # safety stop
                        break
            except Exception as e:
                say(log, f"could not list deployed {kind} resources: {type(e).__name__}: {e}")
            if len(found[kind]) < expected:
                missing.append(f"{kind} {len(found[kind])}/{expected}")
        if not missing:
            break
        say(log, f"waiting for the platform to list everything the deployment created ({', '.join(missing)}), try {attempt}")
        time.sleep(5)
    for kind, _, expected in kinds:
        say(log, f"found {len(found[kind])} deployed {kind} resources")
    return found


def folder_row(fk: str) -> dict:
    resp = sdk().api_client.request("GET", "/orchestrator_/api/FoldersNavigation/GetAllFoldersForCurrentUser", params={"skip": "0", "take": "1000"})
    body = jload(resp)
    rows = body if isinstance(body, list) else body.get("value", [])
    return next((r for r in rows if r["Key"] == fk), {})


def debug_overrides(workshop_zip: bytes, fk: str, tenant_key: str, log: Log) -> dict:
    """Tell Studio Web's Debug to use the resources the deployment created instead of creating its own copies."""
    parent = folder_row(fk).get("ParentKey", "")
    key_path = f"{parent}.{fk}"
    have = deployed_resources(fk, log)
    out, missing = [], []
    with zipfile.ZipFile(io.BytesIO(workshop_zip)) as z:
        for name in z.namelist():
            if not (name.startswith("resources/solution_folder/") and name.endswith(".json")):
                continue
            r = json.loads(z.read(name).decode("utf-8-sig")).get("resource")
            if not r or r.get("kind") in ("package", "connection"):
                continue
            if r.get("kind") == "process" and r.get("type") == "caseManagement":
                continue
            kind = "Process" if r.get("kind") == "process" else r.get("kind")
            key = have.get(kind, {}).get(r["name"])
            if not key:
                missing.append(f"{kind} {r['name']}")
                continue
            path = f"{PARENT}/{ENV['name']}" if kind in ("Process", "app") else key_path  # workers and apps are found by folder path; tables, buckets and assets by key path
            out.append(
                {
                    "solutionResourceKey": r["key"],
                    "reprovisioningIndex": 0,
                    "overwrite": {
                        "resourceKey": key,
                        "resourceName": r["name"],
                        "folderKey": fk,
                        "folderFullyQualifiedName": path,
                        "folderPath": path,
                        "type": "Reference",
                        "kind": kind,
                    },
                }
            )
    if missing:
        say(log, "not linked (Debug will create its own): " + ", ".join(missing))
    return {"docVersion": "1.0", "tenants": [{"tenantKey": tenant_key, "resources": out}]}


def import_and_link(client_id: str, fk: str, log: Log) -> None:
    say(log, "preparing the workshop solution file...")
    data, patched = patched_workshop(client_id)
    say(log, f"your sign-in client and Intake App address put into {patched} files")
    _, tenant_id = org_ids()
    hdr = {"x-uipath-tenantid": tenant_id} if tenant_id else None
    say(log, "uploading the workshop solution to Studio Web...")
    r = sdk().api_client.request(
        "POST",
        "studio_/backend/api/Solution/Import?desktopJit=true&useFileRest=true&enableUnifiedBuild=true",
        scoped="org",
        files={"uploadFile": (WORKSHOP_FILE, data, "application/octet-stream")},
        data={"telemetryData": json.dumps({"FirstRun": False})},
        headers=hdr,
        timeout=180,
    )
    info = jload(r)
    sol_id, user_id = info.get("id"), info.get("userId")
    say(log, f"solution imported into Studio Web (id {sol_id})")
    say(log, "looking up the deployed resources to link Debug to them...")
    overrides = debug_overrides(data, fk, tenant_id, log)
    linked = len(overrides["tenants"][0]["resources"])
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr(f"userProfile/{user_id}/debug_overwrites.json", json.dumps(overrides, indent=2))
    say(log, "saving the Debug links into the Studio Web solution...")
    sdk().api_client.request(
        "POST",
        f"studio_/backend/api/Solution/{sol_id}/Overwrite",
        scoped="org",
        files={"UploadFile": (WORKSHOP_FILE, out.getvalue(), "application/octet-stream")},
        headers=hdr,
        timeout=180,
    )
    say(log, f"Debug linked to the deployed resources ({linked} of them)")


def install(inp: Input, log: Log) -> None:
    say(log, "Step 1 of 5: sign-in client")
    client_id = inp.ClientId.strip() or create_client(log)
    if not client_id:
        raise RuntimeError("Could not create the sign-in client. Create one in Admin > External Applications and run again with ClientId set.")
    ENV["name"] = inp.DeploymentName.strip() or BASE_NAME
    fk = None
    try:
        fk = sdk().folders.retrieve_folder_key(folder_path=f"{PARENT}/{ENV['name']}")
    except Exception:
        fk = None
    if fk:
        LOG_FOLDER["key"] = fk
        say(log, f"Steps 2 and 3 of 5: {PARENT}/{ENV['name']} is already deployed, skipping the publish and deployment")
    else:
        say(log, "Step 2 of 5: publishing the worker package")
        version = publish_package(log)
        say(log, "Step 3 of 5: deploying it (creates the folder, tables, bucket, assets, workers, apps and the Intake App)")
        deploy_package(client_id, version, log)
        fk = sdk().folders.retrieve_folder_key(folder_path=f"{PARENT}/{ENV['name']}")
    if not fk:
        raise RuntimeError(f"The folder {PARENT}/{ENV['name']} was not found after the deployment.")
    LOG_FOLDER["key"] = fk
    try:
        ensure_bucket(fk)
    except Exception:
        pass
    say(log, f"folder {PARENT}/{ENV['name']} is ready with its tables, bucket, assets, workers, apps and the Intake App")
    say(log, "Step 4 of 5: loading policies and claim history")
    load_data(inp, log, fk)
    say(log, "Step 5 of 5: importing the Motor Claims Workshop solution into Studio Web")
    import_and_link(client_id, fk, log)
    say(
        log,
        f"Done. Intake App: https://{org_name().lower().replace('_', '-')}.uipath.host/{app_slug()}  |  In Studio Web open 'MotorInsuranceClaimManagement': "
        "build in MyClaimsCase (or start from an example case), press Debug to test. When finished: Publish, then in Orchestrator Solutions > Deployments "
        f"choose {ENV['name']} > Upgrade to the new version, then Set up activation. Run this function with Action=RegisterClaim to add a test claim.",
    )


# ---------------------------------------------------------------- data actions
def find_data_folder(explicit: str) -> str:
    """The folder that holds the PolicyMaster table: given, the job's own folder, then folders below or beside it."""
    if explicit.strip():
        key = sdk().folders.retrieve_folder_key(folder_path=explicit.strip())
        if not key:
            raise RuntimeError(f"Folder '{explicit}' was not found or is not accessible.")
        return key
    job = job_folder_key()
    candidates = [job] if job else []
    resp = sdk().api_client.request(
        "GET", "/orchestrator_/api/FoldersNavigation/GetAllFoldersForCurrentUser", params={"skip": "0", "take": "1000"}
    )
    body = resp.json()
    rows = body if isinstance(body, list) else body.get("value", [])
    below: list[str] = []
    frontier = [job] if job else []
    while frontier:
        nxt = [r["Key"] for r in rows if r.get("ParentKey") in frontier and r["Key"] not in below]
        below.extend(nxt)
        frontier = nxt
    candidates += below + [r["Key"] for r in rows if r["Key"] not in candidates and r["Key"] not in below]
    hits = []
    for key in candidates:
        try:
            sdk().entities.retrieve_by_name("PolicyMaster", folder_key=key)
            hits.append(key)
        except Exception:
            continue
    if not hits:
        raise RuntimeError("The tables were not found. Press Debug once on a case in the workshop solution so Studio Web creates them, then run this again.")
    if len(hits) > 1:
        raise RuntimeError(f"PolicyMaster exists in {len(hits)} folders you can access; set DataFolder to the one to use.")
    return hits[0]


def has_rows(entity_id: str, field: str, value: str) -> bool:
    res = sdk().entities.retrieve_records(
        entity_key=entity_id,
        filter_group=EntityQueryFilterGroup(
            logical_operator=LogicalOperator.And,
            query_filters=[EntityQueryFilter(field_name=field, operator=QueryFilterOperator.Equals, value=value)],
        ),
        limit=1,
    )
    return bool(res.items)


def seed_file(name: str, email: str) -> str:
    """The seed CSV, with CustomerEmail set on the active demo policies."""
    src = ASSETS / name
    if name != "PolicyMaster_seed.csv":
        return str(src)
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    head = rows[0]
    e, s = head.index("CustomerEmail"), head.index("PolicyStatus")
    for r in rows[1:]:
        if r and r[s] == "Active":
            r[e] = email
    out = Path(tempfile.mkdtemp()) / name
    with open(out, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    return str(out)


def load_data(inp: Input, log: Log, fk: str | None = None) -> None:
    fk = fk or find_data_folder(inp.DataFolder)
    say(log, f"data folder key: {fk}")
    email = inp.CustomerEmail.strip() or my_email()
    say(log, f"customer emails go to: {email}")
    for name, file in (("PolicyMaster", "PolicyMaster_seed.csv"), ("ClaimHistory", "ClaimHistory_seed.csv")):
        ent = sdk().entities.retrieve_by_name(name, folder_key=fk)
        if sdk().entities.retrieve_records(entity_key=ent.id, limit=1).items:
            say(log, f"{name}: already has rows, left as is")
            continue
        res = sdk().entities.import_records(entity_id=ent.id, file_path=seed_file(file, email))
        say(log, f"{name}: loaded ({res})")


def ensure_bucket(folder_key: str) -> None:
    try:
        sdk().buckets.retrieve(name=BUCKET, folder_key=folder_key)
    except Exception:
        sdk().buckets.create(name=BUCKET, description="Claim documents", folder_key=folder_key)


def show_status(inp: Input, log: Log) -> None:
    """Print the latest lines of the install log, so you can see how far Setup got (and whether it is done) without waiting on the pane."""
    fk = find_data_folder(inp.DataFolder)
    dest = Path(tempfile.mkdtemp()) / "setup-log.txt"
    sdk().buckets.download(name=BUCKET, blob_file_path=LOG_FILE, destination_path=str(dest), folder_key=fk)
    lines = dest.read_text(encoding="utf-8").splitlines()
    say(log, f"latest lines of the install log ({len(lines)} lines in total):")
    for line in lines[-25:]:
        say(log, "  " + line)
    say(log, "FINISHED: Setup completed." if any("Done." in x for x in lines) else "NOT FINISHED yet (or it stopped): look at the last line above.")


def register_claim(inp: Input, log: Log) -> None:
    fk = find_data_folder(inp.DataFolder)
    claims = sdk().entities.retrieve_by_name("MotorInsuranceClaim", folder_key=fk)
    with open(ASSETS / "claims.csv", newline="", encoding="utf-8") as f:
        sample = list(csv.DictReader(f))
    first = inp.Customer.strip().split()[0].lower() if inp.Customer.strip() else "rahul"
    row = next((r for r in sample if r["CustomerName"].split()[0].lower() == first), None)
    if row is None:
        raise RuntimeError(f"Unknown customer '{inp.Customer}'. Use Rahul, Priya or Arjun.")
    claim_id = row["ClaimId"]
    if has_rows(claims.id, "ClaimId", claim_id):
        say(log, f"{claim_id}: already registered. Delete its row in Data Fabric (MotorInsuranceClaim) to register it again.")
        return
    ensure_bucket(fk)
    refs = []
    for pdf in sorted((ASSETS / "docs" / row["DocFolder"]).glob("*.pdf")):
        if pdf.name.upper().startswith("SUPPLEMENTAL"):
            continue  # the customer's later reply (Part 6C): not part of the first submission
        name = f"{claim_id}_{pdf.name}"
        sdk().buckets.upload(name=BUCKET, blob_file_path=name, source_path=str(pdf), content_type="application/pdf", folder_key=fk)
        refs.append(name)
    sdk().entities.insert_record(
        entity_key=claims.id,
        data={
            "ClaimId": claim_id,
            "CustomerName": row["CustomerName"],
            "PolicyNumber": row["PolicyNumber"],
            "VehicleRegistration": row["VehicleRegistration"],
            "VehicleModel": row["VehicleModel"],
            "IncidentDate": row["IncidentDate"],
            "ClaimAmount": float(row["ClaimAmount"]),
            "IncidentDescription": row["IncidentDescription"],
            "DocumentReferences": ",".join(refs),
        },
    )
    say(log, f"{claim_id} ({row['CustomerName']}): {len(refs)} documents uploaded, claim registered. Debug a case and pick this claim.")


@traced(name="setup_workshop", run_type="uipath")
def setup_workshop(input: Input) -> Output:
    out = Output()
    log = Log()
    try:
        action = input.Action.strip().lower()
        if action in ("installworkshop", "install"):
            install(input, log)
        elif action in ("loaddata", "load"):
            load_data(input, log)
        elif action == "status":
            show_status(input, log)
        elif action in ("registerclaim", "register"):
            register_claim(input, log)
        else:
            raise RuntimeError(f"Unknown Action '{input.Action}'. Use InstallWorkshop, LoadData, RegisterClaim or Status.")
    except Exception as e:  # errors are returned, never raised
        out.error_type = type(e).__name__
        tb = traceback.format_exc().strip().splitlines()
        out.error_message = f"{e} | at: {' / '.join(tb[-3:])}"
        say(log, f"FAILED: {out.error_type}: {e}")
        say(log, "details: " + " / ".join(tb[-4:]))
    out.Report = log.text()
    return out
