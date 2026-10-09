"""Builds the workshop solution from the finished case: ONE file, MotorClaims_Workshop.uis, holding
  the workers, MyClaimsCase (blank, participants build here), the five finished cases 1_HappyPath..5_Complete
  (read-only reference, Debug only, never publish).
Also MotorClaimsWorkshop_Setup.uis: a separate solution with only SetupWorkshop, which carries the workshop file and installs it.
Usage: python build_solutions.py <finished_solution_dir> <output_dir>"""
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# reuse the case-trimming logic (SNAPS, build, check, drop_intake) from build_snapshots.py without running its main part
_src = open(os.path.join(HERE, "build_snapshots.py"), encoding="utf-8").read()
exec(compile(_src.split("os.makedirs(OUT, exist_ok=True)")[0], "build_snapshots_head", "exec"))  # defines SRC, OUT, final, LABEL, SNAPS, build, check, summary, drop_intake

NS = uuid.UUID("6f1b6e1e-2c1a-4f7e-9a53-0c9d4b7f1a11")
ORIG = "MotorInsuranceClaimCase"
CASE_TEMPLATE = os.path.join(SRC, ORIG)
BASE_PKG = "MotorInsuranceClaimManagement"
BUILD_CLIENT_ID = "39d65bc4-48c5-4ea4-9c19-d96788c98486"  # the client id inside the finished source
CLIENT_PLACEHOLDER = "00000000-0000-4000-8000-000000000000"
BUILD_ROUTING = "claims-intake"  # the Intake App address inside the finished source
ROUTING_PLACEHOLDER = "claims-placeholder"  # setup replaces it with an address that is unique to the participant


def u(*parts):
    return str(uuid.uuid5(NS, ":".join(parts)))


def rd(p):
    return json.load(open(p, encoding="utf-8"))


def wr(p, d, indent=2):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=indent)


WORKERS = os.path.normpath(os.path.join(HERE, "..", "MotorInsuranceClaimManagement"))  # the current worker source (package 1.0.17)
KEEP_FROM_CASE_COPY = {"project.uiproj", "uipath.json"}  # Studio Web adds tooling fields to these; keep its version
SKIP_WORKER_FILES = {".env", ".venv", "node_modules", "__pycache__", ".claude", ".agent", ".uipath", "AGENTS.md", "CLAUDE.md", "dist"}


def overlay_workers(dst):
    """The downloaded case copy holds older worker code than the package that was tested. Put the current worker files on top of it."""
    n = 0
    uipx = [f for f in os.listdir(WORKERS) if f.endswith(".uipx")][0]
    names = [p["ProjectRelativePath"].split("/")[0] for p in rd(os.path.join(WORKERS, uipx))["Projects"]]
    for name in names:
        if name in (ORIG, "MotorInsuranceClaim_Intake") or not os.path.isdir(os.path.join(dst, name)):
            continue
        for root, dirs, files in os.walk(os.path.join(WORKERS, name)):
            dirs[:] = [d for d in dirs if d not in SKIP_WORKER_FILES]
            for f in files:
                if f in SKIP_WORKER_FILES or f.endswith(".pyc"):
                    continue
                rel = os.path.relpath(os.path.join(root, f), os.path.join(WORKERS, name))
                if rel in KEEP_FROM_CASE_COPY:
                    continue
                target = os.path.join(dst, name, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copyfile(os.path.join(root, f), target)
                n += 1
    # table and agent definitions live in the solution resources
    for sub in (("Entity", "Native"), ("process", "agent"), ("app", "CodedAction")):
        src_dir = os.path.join(WORKERS, "resources", "solution_folder", *sub)
        if os.path.isdir(src_dir):
            for f in os.listdir(src_dir):
                if f.endswith(".json") and not f.startswith("MotorInsuranceClaim_Intake"):
                    shutil.copyfile(os.path.join(src_dir, f), os.path.join(dst, "resources", "solution_folder", *sub, f))
                    n += 1
    print(f"  worker files taken from the current source: {n}")


def base_tree(dst, sol_name):
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("userProfile", "__pycache__", "*.pyc"))
    overlay_workers(dst)  # the Intake App stays in the solution: one deploy then creates the whole system, including the app that registers claims
    # the approval-screen apps carry the sign-in client id of the tenant they were built in; ship a placeholder that setup.mjs replaces with the participant's own
    for root, _, files in os.walk(dst):
        for f in files:
            if f.endswith(".json"):
                fp = os.path.join(root, f)
                t = open(fp, encoding="utf-8").read()
                if BUILD_CLIENT_ID in t or BUILD_ROUTING in t:
                    open(fp, "w", encoding="utf-8", newline="").write(t.replace(BUILD_CLIENT_ID, CLIENT_PLACEHOLDER).replace(BUILD_ROUTING, ROUTING_PLACEHOLDER))
    # remove the original single case; each solution adds exactly the cases it wants
    shutil.rmtree(os.path.join(dst, ORIG), ignore_errors=True)
    for rel in (("resources", "solution_folder", "package", ORIG + ".json"), ("resources", "solution_folder", "process", "caseManagement", ORIG + ".json")):
        fp = os.path.join(dst, *rel)
        if os.path.exists(fp):
            os.remove(fp)
    uipx_old = [f for f in os.listdir(dst) if f.endswith(".uipx")][0]
    d = rd(os.path.join(dst, uipx_old))
    d["Projects"] = [p for p in d["Projects"] if not p["ProjectRelativePath"].startswith(ORIG + "/")]
    d["SolutionId"] = u(sol_name, "solution")
    os.remove(os.path.join(dst, uipx_old))
    wr(os.path.join(dst, sol_name + ".uipx"), d, indent=4)
    s = rd(os.path.join(dst, "SolutionStorage.json"))
    s["Projects"] = [p for p in s["Projects"] if not p["ProjectRelativePath"].startswith(ORIG + "/")]
    s["SolutionId"] = d["SolutionId"]
    wr(os.path.join(dst, "SolutionStorage.json"), s, indent=1)
    return sol_name + ".uipx"


def add_case(dst, uipx, sol_name, name, case, b2):
    pid = u(sol_name, name, "project")
    ep = u(sol_name, name, "entrypoint")
    pkg_key = u(sol_name, name, "package")
    proc_key = u(sol_name, name, "process")
    folder = os.path.join(dst, name)
    os.makedirs(folder, exist_ok=True)
    proj = rd(os.path.join(CASE_TEMPLATE, "project.uiproj"))
    proj["Name"] = name
    wr(os.path.join(folder, "project.uiproj"), proj)
    eps = rd(os.path.join(CASE_TEMPLATE, "entry-points.json"))
    eps["entryPoints"][0]["uniqueId"] = ep
    wr(os.path.join(folder, "entry-points.json"), eps, indent=4)
    c = copy.deepcopy(case)
    c["id"] = "case-" + u(sol_name, name, "caseid").replace("-", "")[:10]
    c["name"] = name
    for n in c["nodes"]:
        if n["id"] == "trigger_1":
            n["data"]["inputs"]["entryPointId"] = ep
    json.dump(c, open(os.path.join(folder, "caseplan.case"), "w", encoding="utf-8", newline=""), separators=(",", ":"), ensure_ascii=False)
    for r in b2["resources"]:
        if r["resource"] == "EventTrigger":
            r["value"]["EntryPointUniqueId"]["defaultValue"] = ep
    wr(os.path.join(folder, "bindings_v2.json"), b2)
    bpmn = open(os.path.join(CASE_TEMPLATE, "caseplan.case.bpmn"), encoding="utf-8").read().replace(ORIG, name)
    open(os.path.join(folder, "caseplan.case.bpmn"), "w", encoding="utf-8", newline="").write(bpmn)
    # solution resources for this case project
    pk = rd(os.path.join(SRC, "resources", "solution_folder", "package", ORIG + ".json"))
    pk["resource"].update(name=name, projectKey=pid, key=pkg_key)
    pk["resource"]["spec"]["name"] = name
    wr(os.path.join(dst, "resources", "solution_folder", "package", name + ".json"), pk)
    pr = rd(os.path.join(SRC, "resources", "solution_folder", "process", "caseManagement", ORIG + ".json"))
    pr["resource"].update(name=name, projectKey=pid, key=proc_key)
    pr["resource"]["spec"].update(name=name, packageName=BASE_PKG + ".caseManagement." + name)
    pr["resource"]["spec"]["package"]["key"] = pkg_key
    for dep in pr["resource"].get("dependencies", []):
        if dep.get("name") == ORIG:
            dep["name"] = name  # the process depends on its own package; the original case name no longer exists in this solution
    wr(os.path.join(dst, "resources", "solution_folder", "process", "caseManagement", name + ".json"), pr)
    d = rd(os.path.join(dst, uipx))
    d["Projects"].append({"Type": "CaseManagement", "ProjectRelativePath": name + "/project.uiproj", "Id": pid})
    wr(os.path.join(dst, uipx), d, indent=4)
    s = rd(os.path.join(dst, "SolutionStorage.json"))
    s["Projects"].append({"ProjectId": u(sol_name, name, "cloudproject"), "ProjectRelativePath": name + "/project.uiproj"})
    wr(os.path.join(dst, "SolutionStorage.json"), s, indent=1)


SETUP_FN = os.path.normpath(os.path.join(HERE, "..", "WorkshopSetup", "SetupWorkshop"))


def add_function(dst, uipx, sol_name, src_dir, name):
    """Add a coded function project (here: the setup function) with its package and process resource files."""
    pid = u(sol_name, name, "project")
    shutil.copytree(src_dir, os.path.join(dst, name), ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
    tp = rd(os.path.join(WORKERS, "resources", "solution_folder", "package", "GetClaimHistory.json"))
    tr = rd(os.path.join(WORKERS, "resources", "solution_folder", "process", "function", "GetClaimHistory.json"))
    pkg_key = u(sol_name, name, "package")
    tp["resource"].update(name=name, projectKey=pid, key=pkg_key)
    tp["resource"]["spec"]["name"] = name
    wr(os.path.join(dst, "resources", "solution_folder", "package", name + ".json"), tp)
    tr["resource"].update(name=name, projectKey=pid, key=u(sol_name, name, "process"))
    tr["resource"]["spec"].update(name=name, packageName=BASE_PKG + ".function." + name)
    tr["resource"]["spec"]["package"]["key"] = pkg_key
    for dep in tr["resource"].get("dependencies", []):
        dep["name"] = name
    wr(os.path.join(dst, "resources", "solution_folder", "process", "function", name + ".json"), tr)
    d = rd(os.path.join(dst, uipx))
    d["Projects"].append({"Type": "Function", "ProjectRelativePath": name + "/project.uiproj", "Id": pid})
    wr(os.path.join(dst, uipx), d, indent=4)
    s = rd(os.path.join(dst, "SolutionStorage.json"))
    s["Projects"].append({"ProjectId": u(sol_name, name, "cloudproject"), "ProjectRelativePath": name + "/project.uiproj"})
    wr(os.path.join(dst, "SolutionStorage.json"), s, indent=1)


# Names that must never ship (the author's own addresses) live in private_names.json, which is not in git.
# Without that file there is nothing to rename and nothing to check.
_PRIVATE = os.path.join(HERE, "private_names.json")
_cfg = json.load(open(_PRIVATE, encoding="utf-8")) if os.path.exists(_PRIVATE) else {"renames": [], "forbidden": []}
RENAMES = [(a.encode(), b.encode()) for a, b in _cfg["renames"]]
FORBIDDEN = [x.encode() for x in _cfg["forbidden"]]


def sanitize(dst):
    """Rename the connection slots everywhere (file names and contents) so no personal address is left in the solution."""
    changed = 0
    for root, _, files in os.walk(dst):
        for f in files:
            fp = os.path.join(root, f)
            b = open(fp, "rb").read()
            nb = b
            for old, new in RENAMES:
                nb = nb.replace(old, new)
            if nb != b:
                open(fp, "wb").write(nb)
                changed += 1
            nf = f
            for old, new in RENAMES:
                nf = nf.replace(old.decode(), new.decode())
            if nf != f:
                os.replace(fp, os.path.join(root, nf))
    return changed


def leak_check(uis):
    """Fail the build if any forbidden string is left anywhere in the finished file (including inside nested zips)."""
    bad = []

    def scan(zf, pre=""):
        for n in zf.namelist():
            b = zf.read(n)
            if n.endswith(".zip"):
                scan(zipfile.ZipFile(io.BytesIO(b)), pre + n + ">")
                continue
            for pat in FORBIDDEN:
                if pat in b.lower():
                    bad.append(f"{pre}{n}: {pat.decode()}")

    scan(zipfile.ZipFile(uis))
    if bad:
        sys.exit("personal details left in " + os.path.basename(uis) + ": " + "; ".join(bad[:6]))


def verify(dst, uipx):
    d = rd(os.path.join(dst, uipx))
    ids = [p["Id"] for p in d["Projects"]]
    assert len(ids) == len(set(ids)), "duplicate project ids"
    for p in d["Projects"]:
        assert os.path.exists(os.path.join(dst, p["ProjectRelativePath"])), "missing project folder " + p["ProjectRelativePath"]
    keys, errs = set(), []
    found, wanted = set(), []
    for root, _, files in os.walk(os.path.join(dst, "resources", "solution_folder")):
        for f in files:
            if not f.endswith(".json"):
                continue
            r = rd(os.path.join(root, f)).get("resource")
            if not r:
                continue
            found.add((r.get("kind"), r.get("name")))
            wanted += [(d.get("kind"), d.get("name"), r["name"]) for d in r.get("dependencies", [])]
            if r["key"] in keys:
                errs.append("duplicate resource key " + r["key"])
            keys.add(r["key"])
            if r.get("projectKey") and r["projectKey"] not in ids:
                errs.append(f"resource {r['name']} points at a project that is not in the solution")
    for kind, name, owner in wanted:
        if (kind, name) not in found:
            errs.append(f"{owner} depends on {kind} '{name}', which is not in the solution")
    eps = []
    for p in d["Projects"]:
        if p["Type"] == "CaseManagement":
            e = rd(os.path.join(dst, os.path.dirname(p["ProjectRelativePath"]), "entry-points.json"))
            eps.append(e["entryPoints"][0]["uniqueId"])
    if len(eps) != len(set(eps)):
        errs.append("duplicate entry point ids")
    return errs


def make(sol_name, cases, functions=(), file_name=None):
    tmp = os.path.join(tempfile.mkdtemp(prefix="mc_solution_"), sol_name)  # fresh folder every run (a locked leftover can block a fixed one)
    uipx = base_tree(tmp, sol_name)
    for name, spec in cases:
        c, b2 = build(spec)
        errs = check(c, name)
        if errs:
            sys.exit(f"integrity problems in {name}: {errs}")
        add_case(tmp, uipx, sol_name, name, c, b2)
    for fname, fdir in functions:
        add_function(tmp, uipx, sol_name, fdir, fname)
    errs = verify(tmp, uipx)
    if errs:
        sys.exit(f"{sol_name}: {errs}")
    print(f"  neutral connection names applied in {sanitize(tmp)} files")
    os.makedirs(OUT, exist_ok=True)
    uis = os.path.join(OUT, (file_name or sol_name) + ".uis")
    if os.path.exists(uis):
        os.remove(uis)
    with zipfile.ZipFile(uis, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(tmp):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, tmp).replace(os.sep, "/"))
    shutil.rmtree(tmp, ignore_errors=True)
    leak_check(uis)
    print(f"{sol_name}: {len(cases)} case(s) -> {os.path.basename(uis)} ({os.path.getsize(uis)//1024} KB)")


def make_setup():
    """The standalone setup solution: only SetupWorkshop, carrying the workshop solution (built just above) and the sample files."""
    import subprocess
    sol = "MotorClaimsWorkshop_Setup"
    tmp = os.path.join(tempfile.mkdtemp(prefix="mc_setup_"), sol)
    shutil.copytree(os.path.join(HERE, "..", "WorkshopSetup"), tmp, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
    shutil.copyfile(os.path.join(OUT, "MotorClaims_Workshop.uis"), os.path.join(tmp, "SetupWorkshop", "assets", "MotorClaims_Workshop.uis"))
    old = [f for f in os.listdir(tmp) if f.endswith(".uipx")][0]
    if old != sol + ".uipx":
        os.replace(os.path.join(tmp, old), os.path.join(tmp, sol + ".uipx"))
    node = ["node", os.path.join(os.environ["APPDATA"], "npm", "node_modules", "@uipath", "cli", "dist", "index.js")]
    for args in (["solution", "projects", "add", "SetupWorkshop", os.path.join(tmp, sol + ".uipx")], ["solution", "resources", "refresh", "--solution-folder", tmp]):
        r = subprocess.run(node + args + ["--output", "json"], capture_output=True, text=True, cwd=tmp, encoding="utf-8", errors="replace")
        if '"Result": "Success"' not in r.stdout:
            sys.exit(f"{' '.join(args[:3])} failed: {r.stdout[-600:]} {r.stderr[-300:]}")
    uis = os.path.join(OUT, sol + ".uis")
    if os.path.exists(uis):
        os.remove(uis)
    with zipfile.ZipFile(uis, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(tmp):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, tmp).replace(os.sep, "/"))
    leak_check(uis)
    print(f"{sol}: -> {os.path.basename(uis)} ({os.path.getsize(uis)//1024} KB)")


SPEC = dict(SNAPS)
make("MotorInsuranceClaimManagement",  # same name as the deployed package, so Publish gives a new version of it and Upgrade adds the cases to the running system
     [("MyClaimsCase", SPEC["00_Blank"]),
      ("1_HappyPath", SPEC["01_HappyPath"]), ("2_PendingCustomer", SPEC["02_PendingCustomer"]), ("3_Denied", SPEC["03_Denied"]),
      ("4_FraudInvestigation", SPEC["04_FraudInvestigation"]), ("5_Complete", SPEC["05_Complete"])],
     file_name="MotorClaims_Workshop")
make_setup()

