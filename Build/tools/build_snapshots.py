"""Builds the workshop checkpoint solutions (.uis) by pruning the finished case back step by step.
Usage: python build_snapshots.py <finished_solution_dir> <output_dir>"""
import copy
import tempfile
import json
import os
import re
import shutil
import sys
import uuid
import zipfile

SRC, OUT = sys.argv[1], sys.argv[2]
CASE_REL = os.path.join("MotorInsuranceClaimCase", "caseplan.case")
BIND_REL = os.path.join("MotorInsuranceClaimCase", "bindings_v2.json")
final = json.load(open(os.path.join(SRC, CASE_REL), encoding="utf-8"))
final_b2 = json.load(open(os.path.join(SRC, BIND_REL), encoding="utf-8"))
LABEL = {n["data"]["label"]: n["id"] for n in final["nodes"] if n["type"] == "case-management:Stage"}
ID2LABEL = {v: k for k, v in LABEL.items()}

PRIMARY = ["Intake", "Assessment", "Review", "Settlement", "Closure"]
SNAPS = [
    ("00_Blank", dict(stages=[], saves=False, emails=False, slas=False)),
    ("01_HappyPath", dict(stages=PRIMARY, saves=False, emails=False, slas=False)),
    ("02_PendingCustomer", dict(stages=PRIMARY + ["Pending Customer"], saves=False, emails=False, slas=False)),
    ("03_Denied", dict(stages=PRIMARY + ["Pending Customer", "Denied"], saves=False, emails=False, slas=False)),
    ("04_FraudInvestigation", dict(stages=PRIMARY + ["Pending Customer", "Denied", "Fraud Investigation"], saves=False, emails=False, slas=False)),
    ("05_Complete", dict(stages=PRIMARY + ["Pending Customer", "Denied", "Fraud Investigation"], saves=True, emails=True, slas=True)),
]


def strings(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(k)
            yield from strings(v)
    elif isinstance(o, list):
        for x in o:
            yield from strings(x)
    elif isinstance(o, str):
        yield o


def build(spec):
    c = copy.deepcopy(final)
    keep = set(spec["stages"])
    keep_ids = {LABEL[k] for k in keep}
    c["nodes"] = [n for n in c["nodes"] if n["type"] != "case-management:Stage" or n["data"]["label"] in keep]
    removed_tasks = set()
    for n in c["nodes"]:
        if n["type"] != "case-management:Stage":
            continue
        d = n["data"]
        label = d["label"]
        groups = []
        for g in d["tasks"]:
            ng = []
            for t in g:
                drop = False
                if t["displayName"].startswith("Save ") and not spec["saves"]:
                    drop = True
                if t["type"] == "execute-connector-activity" and label in ("Closure", "Denied") and not spec["emails"]:
                    drop = True
                if drop:
                    removed_tasks.add(t["id"])
                else:
                    ng.append(t)
            if ng:
                groups.append(ng)
        d["tasks"] = groups
        if "Fraud Investigation" not in keep:
            # the fraud result does not exist yet in this checkpoint: leave that mapping empty until the Fraud stage is added
            for g in d["tasks"]:
                for t in g:
                    for i in t["data"].get("inputs", []):
                        if i.get("value") == "=js:vars.fraudResult":
                            i["value"] = ""
        if not spec["slas"]:
            d.pop("slaRules", None)
        # exits
        ex = []
        for e in d.get("exitConditions", []):
            if not e["marksStageComplete"] and e.get("exitToStageId") not in keep_ids:
                continue
            for grp in e["rules"]:
                for r in grp:
                    if "selectedTasksIds" in r:
                        r["selectedTasksIds"] = [x for x in r["selectedTasksIds"] if x not in removed_tasks]
            ex.append(e)
        d["exitConditions"] = ex
        if label == "Assessment" and "Fraud Investigation" not in keep:
            for e in d["exitConditions"]:
                for grp in e["rules"]:
                    for r in grp:
                        r.pop("conditionExpression", None)
        # entries that point at stages that are not in this checkpoint
        if "entryConditions" in d:
            ent = []
            for e in d["entryConditions"]:
                refs = [s for grp in e["rules"] for r in grp for s in r.get("selectedStageIds", [])]
                if all(s in keep_ids for s in refs):
                    ent.append(e)
            d["entryConditions"] = ent
    # case-level rules
    if not spec["slas"]:
        c["metadata"].pop("slaRules", None)
    c["metadata"]["caseExitRules"] = [r for r in c["metadata"]["caseExitRules"]
                                     if all(s in keep_ids for grp in r["rules"] for x in grp for s in x.get("selectedStageIds", []))]
    c["edges"] = [e for e in c.get("edges", []) if e.get("source") in {n["id"] for n in c["nodes"]} and e.get("target") in {n["id"] for n in c["nodes"]}]
    # drop bindings nothing refers to
    node_text = json.dumps(c["nodes"], ensure_ascii=False) + json.dumps(c["metadata"], ensure_ascii=False)
    alive = set(re.findall(r"=bindings\.(\w+)", node_text))
    bind = c["bindings"]
    changed = True
    while changed:
        changed = False
        for b in bind:
            if b["id"] in alive:
                for ref in re.findall(r"=bindings\.(\w+)", json.dumps(b)):
                    if ref not in alive:
                        alive.add(ref)
                        changed = True
    c["bindings"] = [b for b in bind if b["id"] in alive]
    # bindings_v2: keep what the remaining bindings and nodes use
    live_text = json.dumps(c["bindings"]) + node_text
    b2 = copy.deepcopy(final_b2)
    res = []
    for r in b2["resources"]:
        k = r["key"]
        if r["resource"] == "process":
            m = re.search(r"=bindings\.(\w+)", k)
            if m and m.group(1) not in alive:
                continue
        elif r["resource"] == "app":
            if f'"{k}"' not in node_text and k.split(".")[-1] not in node_text:
                continue
        elif r["resource"] == "Connection":
            if k not in live_text:
                continue
        res.append(r)
    b2["resources"] = res
    # layout: only what exists
    ids = {n["id"] for n in c["nodes"]}
    c["layout"]["nodes"] = {k: v for k, v in c["layout"]["nodes"].items() if k in ids}
    c["layout"]["edges"] = {k: v for k, v in c["layout"].get("edges", {}).items() if k in ids or True}
    return c, b2


def check(c, name):
    """Integrity: every reference inside the checkpoint points at something that is in it."""
    errs = []
    stages = {n["id"]: n for n in c["nodes"] if n["type"] == "case-management:Stage"}
    taskids = {t["id"]: sid for sid, n in stages.items() for g in n["data"]["tasks"] for t in g}
    allids = [n["id"] for n in c["nodes"]] + list(taskids)
    if len(set(allids)) != len(allids):
        errs.append("duplicate ids")
    defined = {"response", "error"}
    for n in c["nodes"]:
        for s in strings(n):
            pass
    def collect(o):
        if isinstance(o, dict):
            if "var" in o and isinstance(o["var"], str):
                defined.add(o["var"])
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
    collect(c["nodes"])
    dispnames = []
    for sid, n in stages.items():
        d = n["data"]
        for e in d.get("exitConditions", []) + d.get("entryConditions", []):
            dispnames.append(e["displayName"])
            if e.get("exitToStageId") and e["exitToStageId"] not in stages:
                errs.append(f"{d['label']}: exit to missing stage")
            for grp in e["rules"]:
                for r in grp:
                    for s in r.get("selectedStageIds", []):
                        if s not in stages:
                            errs.append(f"{d['label']}: rule refers to missing stage {s}")
                    for t in r.get("selectedTasksIds", []):
                        if taskids.get(t) != sid:
                            errs.append(f"{d['label']}: rule refers to missing task {t}")
        for g in d["tasks"]:
            for t in g:
                for e in t.get("entryConditions", []):
                    dispnames.append(e["displayName"])
    for s in strings(c["nodes"]):
        for v in re.findall(r"vars\.([A-Za-z_]\w*)", s):
            if v not in defined:
                errs.append(f"variable vars.{v} is used but nothing in this checkpoint produces it")
    for s in set(strings(c["nodes"])):
        for ref in re.findall(r"=bindings\.(\w+)", s):
            if ref not in {b["id"] for b in c["bindings"]}:
                errs.append(f"missing binding {ref}")
    if len(set(dispnames)) != len(dispnames):
        errs.append("duplicate rule names")
    return sorted(set(errs))


def summary(c):
    st = [n for n in c["nodes"] if n["type"] == "case-management:Stage"]
    tasks = [t for n in st for g in n["data"]["tasks"] for t in g]
    return dict(stages=len(st), tasks=len(tasks), rules=sum(len(n["data"].get("entryConditions", [])) + len(n["data"].get("exitConditions", [])) for n in st) + sum(len(t.get("entryConditions", [])) for t in tasks),
                slas=sum(len(n["data"].get("slaRules", []) or []) for n in st) + len(c["metadata"].get("slaRules", []) or []))


def drop_intake(tmp):
    """The Intake web app is deployed by setup.mjs, and the case never uses it. Leaving it in the solution makes Studio Web's Debug try to
    deploy a second copy (routing name and sign-in client from the author's tenant), which fails in every other tenant."""
    name = "MotorInsuranceClaim_Intake"
    shutil.rmtree(os.path.join(tmp, name), ignore_errors=True)
    for rel in (os.path.join("resources", "solution_folder", "app", "Coded", name + ".json"), os.path.join("resources", "solution_folder", "package", name + ".json")):
        fp = os.path.join(tmp, rel)
        if os.path.exists(fp):
            os.remove(fp)
    p = os.path.join(tmp, "MotorInsuranceClaimManagement.uipx")
    d = json.load(open(p, encoding="utf-8"))
    d["Projects"] = [x for x in d["Projects"] if not x["ProjectRelativePath"].startswith(name + "/")]
    json.dump(d, open(p, "w", encoding="utf-8"), indent=4)
    p = os.path.join(tmp, "SolutionStorage.json")
    d = json.load(open(p, encoding="utf-8"))
    d["Projects"] = [x for x in d["Projects"] if not x["ProjectRelativePath"].startswith(name + "/")]
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1)


os.makedirs(OUT, exist_ok=True)
report = {}
for name, spec in SNAPS:
    c, b2 = build(spec)
    errs = check(c, name)
    report[name] = (summary(c), errs)
    if errs:
        print("INTEGRITY PROBLEMS in", name)
        for e in errs:
            print("   ", e)
        continue
    tmp = os.path.join(tempfile.gettempdir(), "mc_snapshot_work_" + name)
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    shutil.copytree(SRC, tmp, ignore=shutil.ignore_patterns("userProfile", "__pycache__", "*.pyc"))
    json.dump(c, open(os.path.join(tmp, CASE_REL), "w", encoding="utf-8", newline=""), separators=(",", ":"), ensure_ascii=False)
    json.dump(b2, open(os.path.join(tmp, BIND_REL), "w", encoding="utf-8"), indent=2)
    drop_intake(tmp)
    new_id = str(uuid.uuid4())
    for f in ("MotorInsuranceClaimManagement.uipx", "SolutionStorage.json"):
        p = os.path.join(tmp, f)
        t = open(p, encoding="utf-8").read()
        old = json.loads(t).get("SolutionId")
        assert old, f
        open(p, "w", encoding="utf-8", newline="").write(t.replace(old, new_id))
    uis = os.path.join(OUT, f"MotorInsuranceClaim_{name}.uis")
    if os.path.exists(uis):
        os.remove(uis)
    with zipfile.ZipFile(uis, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(tmp):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, tmp).replace(os.sep, "/"))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{name}: OK  {report[name][0]}  -> {os.path.basename(uis)} ({os.path.getsize(uis)//1024} KB, solution id {new_id[:8]}...)")
json.dump({k: v[0] for k, v in report.items()}, open(os.path.join(OUT, "_summary.json"), "w"), indent=1)
