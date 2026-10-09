/* Motor Claims workshop site: a small single-page app. Hash routes, no server, works from a file or GitHub Pages. */
(function () {
  "use strict";
  var D = window.DATA;
  var app = document.getElementById("app");

  /* ---------- tiny DOM helpers ---------- */
  function h(tag, props) {
    var el = document.createElement(tag);
    props = props || {};
    Object.keys(props).forEach(function (k) {
      var v = props[k];
      if (v == null || v === false) return;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { add(el, x); }); return; }
    el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  /* **bold**, `code`, [label](#/route) */
  function rich(text) {
    var frag = document.createDocumentFragment();
    var re = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    String(text).split(re).forEach(function (part) {
      if (!part) return;
      if (part.slice(0, 2) === "**") frag.appendChild(h("strong", { text: part.slice(2, -2) }));
      else if (part[0] === "`") frag.appendChild(h("code", { text: part.slice(1, -1) }));
      else if (part[0] === "[") {
        var m = /\[([^\]]+)\]\(([^)]+)\)/.exec(part);
        frag.appendChild(h("a", { href: m[2], text: m[1] }));
      } else frag.appendChild(document.createTextNode(part));
    });
    return frag;
  }
  function p(text, cls) { return h("p", { class: cls }, rich(text)); }

  /* ---------- saved state (progress, self-check). Never required. ---------- */
  var KEY = "mcw-site-v1";
  var S = { built: {}, call: {}, done: {} };
  try { var raw = localStorage.getItem(KEY); if (raw) S = Object.assign(S, JSON.parse(raw)); } catch (e) { /* storage blocked: fine */ }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* ignore */ } }
  var REVEAL = {}; // what is open right now (kept while you move around, reset on reload)

  /* ---------- copy ---------- */
  function copyText(text, done) {
    function fallback() {
      var ta = h("textarea", { style: "position:fixed;opacity:0" });
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) { /* ignore */ }
      document.body.removeChild(ta); done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  }
  function copyBtn(value, label) {
    var b = h("button", { class: "copy", type: "button", "aria-label": "Copy " + value, title: "Copy" }, label || "Copy");
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      copyText(value, function () {
        b.textContent = "Copied"; b.classList.add("ok");
        setTimeout(function () { b.textContent = label || "Copy"; b.classList.remove("ok"); }, 1200);
      });
    });
    return b;
  }
  function codeLine(value) { return h("div", { class: "codeline" }, h("code", { text: value }), copyBtn(value)); }

  /* ---------- lookups ---------- */
  function act(name) { return D.ACTIVITIES.filter(function (a) { return a.name === name; })[0]; }
  function stage(id) { return D.STAGES.filter(function (s) { return s.id === id; })[0]; }
  function primaries() { return D.STAGES.filter(function (s) { return s.kind === "primary"; }); }
  function builtCount() { return primaries().filter(function (s) { return S.built[s.id]; }).length; }
  function nextUnbuilt() { var l = primaries().filter(function (s) { return !S.built[s.id]; }); return l.length ? l[0].id : "done"; }

  /* ---------- building blocks ---------- */
  function typeBadge(t) { return h("span", { class: "badge t-" + t }, D.TYPES[t].label); }

  function actCard(a, opts) {
    opts = opts || {};
    var later = a.chapter > 1;
    return h("article", { class: "act t-" + a.type + (later ? " later" : ""), id: "act-" + a.name },
      h("div", { class: "act-top" },
        h("span", { class: "act-icon t-" + a.type, "aria-hidden": "true" }, D.TYPES[a.type].icon),
        h("div", { class: "act-name" }, h("code", { text: a.name })),
        copyBtn(a.name)),
      h("div", { class: "act-meta" }, typeBadge(a.type),
        h("span", { class: "studio" }, "Task type in Studio Web: " + D.TYPES[a.type].studio),
        later ? h("span", { class: "chip soft" }, "Chapter " + a.chapter) : null),
      p(a.line, "act-line"),
      a.gives.length ? h("div", { class: "gives" }, h("span", { class: "k" }, "You get: "),
        a.gives.map(function (g) { return h("code", { class: "var", text: g }); })) : null,
      h("div", { class: "used" }, h("span", { class: "k" }, "Used in: "),
        a.stages.map(function (sid) {
          var s = stage(sid);
          return s && !opts.noLinks && a.chapter === 1 ? h("a", { class: "chip", href: "#/" + sid }, s.name) : h("span", { class: "chip" }, s ? s.name : sid);
        })));
  }

  function actChip(name, extra) {
    var a = act(name);
    return h("div", { class: "taskrow" },
      h("div", { class: "taskrow-head" },
        h("span", { class: "act-icon t-" + a.type, "aria-hidden": "true" }, D.TYPES[a.type].icon),
        h("div", {}, h("div", {}, h("code", { class: "act-code", text: a.name }), copyBtn(a.name)),
          h("div", { class: "taskrow-sub" }, typeBadge(a.type), h("span", {}, extra.required ? "Required" : "Not required"))),
        h("button", { class: "linkbtn", type: "button", onclick: function () { openDrawer(a.name); } }, "Details")),
      p(a.line, "taskrow-line"),
      extra.rule ? h("div", { class: "taskrule" }, h("span", { class: "k" }, "Task rule: "),
        h("code", { text: extra.rule.name }), h("span", { class: "muted" }, " · " + extra.rule.type),
        extra.rule.expr ? h("div", {}, codeLine(extra.rule.expr)) : null) : null);
  }

  function ruleCard(rule, key) {
    var open = !!REVEAL[key];
    var body = h("div", { class: "rule-expr" });
    function paint() {
      body.textContent = "";
      if (!REVEAL[key]) {
        body.appendChild(h("button", { class: "btn small", type: "button", onclick: function () { REVEAL[key] = true; paint(); } }, "Show the rule"));
        return;
      }
      body.appendChild(h("div", { class: "kvline" }, h("span", { class: "k" }, "Name"), h("code", { text: rule.name }), copyBtn(rule.name)));
      body.appendChild(h("div", { class: "kvline" }, h("span", { class: "k" }, "Type"), h("span", {}, rule.type + (rule.stage ? " · stage " + rule.stage : ""))));
      body.appendChild(h("div", { class: "kvline" }, h("span", { class: "k" }, "Expression"),
        rule.expr ? h("span", { class: "expr" }, h("code", { text: rule.expr }), copyBtn(rule.expr)) : h("span", { class: "muted" }, "None. Leave it empty.")));
      if (rule.why) body.appendChild(p(rule.why, "why-line"));
    }
    paint();
    return h("div", { class: "rule" },
      h("div", { class: "rule-label" }, rule.label),
      p(rule.plain, "rule-plain"),
      body);
  }

  /* ---------- content blocks (shared by stage build steps and plain pages) ---------- */
  function blocks(list) {
    var out = [];
    list.forEach(function (b) {
      switch (b.t) {
        case "h": out.push(h("h3", { text: b.text })); break;
        case "text": out.push(p(b.text)); break;
        case "list": out.push(h("ul", {}, b.items.map(function (i) { return h("li", {}, rich(i)); }))); break;
        case "ol": out.push(h("ol", {}, b.items.map(function (i) { return h("li", {}, rich(i)); }))); break;
        case "kv":
          out.push(h("div", { class: "kv" }, b.rows.map(function (r) {
            return h("div", { class: "kvrow" }, h("div", { class: "kvk" }, r[0]),
              h("div", { class: "kvv" }, h("code", { text: r[1] })), copyBtn(r[1]));
          }))); break;
        case "table":
          out.push(h("div", { class: "tablewrap" }, h("table", { class: "tbl" },
            h("thead", {}, h("tr", {}, b.head.map(function (x) { return h("th", { text: x }); }), h("th", { class: "narrow" }, ""))),
            h("tbody", {}, b.rows.map(function (r) {
              return h("tr", {}, h("td", {}, h("code", { text: r[0] })), h("td", {}, h("code", { text: r[1] })), h("td", { class: "narrow" }, copyBtn(r[1])));
            }))))); break;
        case "info":
          out.push(h("div", { class: "tablewrap" }, h("table", { class: "tbl info" },
            h("thead", {}, h("tr", {}, b.head.map(function (x) { return h("th", { text: x }); }))),
            h("tbody", {}, b.rows.map(function (r) { return h("tr", {}, r.map(function (c) { return h("td", {}, rich(c)); })); }))))); break;
        case "code": out.push(codeLine(b.text)); break;
        case "why": case "note": case "check": case "stuck": case "heads":
          var title = { why: "Why", note: "Note", check: "Check", stuck: "Stuck?", heads: "Heads-up" }[b.t];
          out.push(h("aside", { class: "callout " + b.t },
            h("div", { class: "callout-t" }, title),
            b.items ? h("ul", {}, b.items.map(function (i) { return h("li", {}, rich(i)); })) : p(b.text)));
          break;
        case "cards":
          out.push(h("div", { class: "cards3" }, b.items.map(function (c) {
            return h("div", { class: "mini" }, h("h4", { text: c.title }), p(c.text));
          }))); break;
      }
    });
    return out;
  }

  /* ---------- the map ---------- */
  function caseMap(opts) {
    opts = opts || {};
    var cur = opts.current, tokenAt = nextUnbuilt();
    var row = h("ol", { class: "map", "aria-label": "The five main stages" });
    primaries().forEach(function (s, i) {
      var built = !!S.built[s.id];
      var node = h("li", { class: "node" + (built ? " built" : "") + (cur === s.id ? " current" : "") },
        tokenAt === s.id ? h("span", { class: "token", title: "Rahul's claim is waiting here", "aria-hidden": "true" }, "R") : null,
        h("a", { href: "#/" + s.id, class: "node-box" },
          h("span", { class: "node-no" }, built ? "✓" : String(i + 1)),
          h("span", { class: "node-name" }, s.name),
          opts.compact ? null : h("span", { class: "node-sub" }, s.short)));
      row.appendChild(node);
    });
    var wrap = h("div", { class: "mapwrap" + (opts.compact ? " compact" : "") }, row);
    if (tokenAt === "done") wrap.appendChild(h("div", { class: "finish" }, "R", " ✓ Rahul's claim has made it through the happy path"));
    if (!opts.compact) {
      wrap.appendChild(h("div", { class: "side" },
        h("span", { class: "side-k" }, "Later chapters add the detours"),
        D.STAGES.filter(function (s) { return s.kind === "secondary"; }).map(function (s) {
          return h("span", { class: "ghost" }, s.name, h("small", {}, "Chapter " + s.chapter));
        })));
    }
    return wrap;
  }

  /* ---------- pages ---------- */
  function pageHead(eyebrow, title, lead) {
    return h("header", { class: "pagehead" },
      eyebrow ? h("div", { class: "eyebrow" }, eyebrow) : null,
      h("h1", { text: title }),
      lead ? p(lead, "lead") : null);
  }

  function pageHome() {
    var n = builtCount();
    var calls = callTally();
    return [
      h("section", { class: "hero" },
        h("div", { class: "eyebrow" }, "Maestro Case workshop"),
        h("h1", { text: "Build a motor insurance claims case" }),
        p("A customer registers a claim. AI agents read the documents, code checks the rules, and people decide only when they must. **You build the conductor.** Every worker is already made for you.", "lead"),
        h("div", { class: "hero-actions" },
          h("a", { class: "btn primary", href: "#/setup" }, "Start with Setup"),
          h("a", { class: "btn", href: "#/scenario" }, "Read the scenario"),
          h("button", { class: "btn", type: "button", onclick: function () { openDrawer(); } }, "Browse the activities"))),
      h("section", { class: "panel" },
        h("div", { class: "panel-h" }, h("h2", { text: "The case you will build" }),
          h("span", { class: "muted" }, n + " of 5 main stages built")),
        caseMap(),
        p("Click a stage to open it. Rahul's claim token sits on the next stage to build.", "muted small")),
      h("section", {}, h("h2", { class: "sec", text: "The chapters" }),
        h("div", { class: "chapters" }, D.CHAPTERS.map(function (c) {
          var inner = [
            h("div", { class: "ch-no" }, "Chapter " + c.no),
            h("h3", { text: c.title }),
            p(c.sub, "muted"),
            c.open ? h("div", { class: "ch-go" }, "Open chapter") : h("div", { class: "ch-lock" }, "Opens later in the workshop")
          ];
          return c.open ? h("a", { class: "chapter open", href: "#/" + c.id }, inner) : h("div", { class: "chapter locked" }, inner);
        }))),
      calls.total ? h("section", { class: "panel mind" },
        h("h2", { text: "Your calls so far" }),
        p("You called **" + calls.nailed + "** exactly, **" + calls.close + "** were close and **" + calls.missed + "** were new to you. Nobody is keeping score but you.", "")) : null
    ];
  }

  function callTally() {
    var t = { nailed: 0, close: 0, missed: 0, total: 0 };
    Object.keys(S.call).forEach(function (k) { if (t[S.call[k]] != null) { t[S.call[k]]++; t.total++; } });
    return t;
  }

  function pageScenario() {
    return [
      pageHead("The scenario", "The business story", "The company, the people, and the journey of a claim. Open this any time you need to remember what the case is for."),
      h("h2", { class: "sec", text: "The company" }),
      p("A motor insurer settles accident claims. Today a clerk reads every document by hand, checks the policy in a spreadsheet, emails people, and chases approvals. **Claims take days and nobody can say where a claim is.**"),
      h("h2", { class: "sec", text: "The goal" }),
      blocks([{ t: "list", items: [
        "Read the documents and check the policy by itself.",
        "Ask a person only when a human decision is really needed.",
        "Never pay more than the policy allows, and never pay without the right approval.",
        "Tell the customer what is happening.",
        "Always show the current status of every claim."
      ] }]),
      h("h2", { class: "sec", text: "The people" }),
      blocks([{ t: "info", head: ["Who", "What they do in the process"], rows: [
        ["**Customer**", "Registers the claim and uploads documents in the Intake App. Receives emails. Adds a missing document later."],
        ["**Claims adjuster**", "Reviews each claim and decides: approve, reject, or ask the customer for more information."],
        ["**Senior approver**", "Approves large settlements before they are paid."],
        ["**Fraud investigator**", "Looks at claims the system flags as high risk."],
        ["**Operations**", "Watches the claim record and the time limits."]
      ] }]),
      h("h2", { class: "sec", text: "The customers you will test with" }),
      blocks([{ t: "info", head: ["Customer", "Story", "What should happen"], rows: [
        ["**Rahul Sharma**", "Rear-ended at a traffic light. All 7 documents, clean history, claim 185,000.", "Straight through. Paid 162,400. No senior approval."],
        ["**Priya Nair**", "Side collision. She forgot the repair estimate.", "The case pauses, emails her, waits for the estimate, then continues."],
        ["**Arjun Mehta**", "Head-on collision, 240,000. The documents contradict each other and he has 3 earlier claims.", "Flagged as high fraud risk. An investigator decides. If cleared, the payout is 230,000 and needs a senior approver."],
        ["**Meera**", "Her policy has expired.", "Denied at the start."]
      ] }]),
      h("h2", { class: "sec", text: "The journey of a claim" }),
      p("Five stages on the **main road**. A claim normally passes through all of them. Three **side stages** only start when something unusual happens."),
      caseMap({ compact: false }),
      blocks([{ t: "info", head: ["Detour", "When it happens", "Where it goes"], rows: [
        ["Pending Customer", "A document is missing, or the adjuster asks for more information.", "Waits for the customer, then back to where it left."],
        ["Fraud Investigation", "The fraud score is High (70 or more).", "Cleared goes back to Assessment. Confirmed goes to Denied."],
        ["Denied", "The policy is invalid, the adjuster rejects, a senior approver rejects, or fraud is confirmed.", "Tells the customer and ends the case."]
      ] }]),
      h("h2", { class: "sec", text: "The rules of the business" }),
      blocks([{ t: "info", head: ["Rule", "In plain words"], rows: [
        ["Documents", "AI reads them. The result is **Complete**, **Inconsistent** (all there but they contradict each other) or **Incomplete** (something is missing)."],
        ["Policy", "Valid only if it exists, is Active, matches the vehicle, and the incident date is inside the cover period."],
        ["Fraud", "A High risk (70 or more) goes to an investigator before anything else happens. Fraud is never named to the customer."],
        ["The adjuster", "A person decides: Approve, Reject (comment required), or Request information."],
        ["Money", "The smallest of claim amount, damage estimate and cover limit, minus the 10,000 deductible, never below zero."],
        ["Senior approval", "Above 175,000 a senior approver must approve before anything is paid."],
        ["Payment", "Recorded once per claim as `PAY-<claim number>`. A second attempt returns the same payment."]
      ] }])
    ];
  }

  function pageSetup() {
    return [
      pageHead("Setup", "Get ready", "About 25 minutes. You prepare your own UiPath account with one import and one run, configure your Gmail and Data Fabric connections, and watch a finished case run. You need a UiPath Community account and the file `MotorClaimsWorkshop_Setup.uis`. Nothing to install."),
      h("h2", { class: "sec", text: "1. Import and run Setup" }),
      blocks([
        { t: "h", text: "Import the Setup solution" },
        { t: "ol", items: [
          "Open **Studio Web** and go to the home page.",
          "Use **Import** (next to **Create New**; the label can differ).",
          "Choose the file `MotorClaimsWorkshop_Setup.uis`.",
          "Open the solution **MotorClaimsWorkshop_Setup**. It has one project, **SetupWorkshop**."
        ] },
        { t: "h", text: "Run Setup" },
        { t: "ol", items: [
          "Open **SetupWorkshop** and press **Debug**. A small form opens.",
          "Set **Action** to `InstallWorkshop`. **Leave every other field empty.**",
          "Run it and **wait for the result**. It takes about a minute."
        ] },
        { t: "check", text: "The result ends with **Done** and gives your **Intake App** address, for example `https://<your-organization>.uipath.host/claims-<your-organization>`. Copy it somewhere." },
        { t: "stuck", items: [
          "**The screen looks stuck.** Studio Web sometimes shows only the first lines until the run ends. Open a second Debug of **SetupWorkshop** with **Action** = `Status`. It ends with **FINISHED** or **NOT FINISHED**.",
          "**It says a name cannot be used.** A leftover from an earlier try is in your account. Run Setup again with **DeploymentName** set to another name, for example `ClaimsSolutionB`."
        ] },
        { t: "h", text: "What Setup just created for you" },
        { t: "info", head: ["What", "Where"], rows: [
          ["A sign-in client for the approval screens and the Intake App", "Your organization"],
          ["The **environment**: the claim tables, the document bucket, the two business-number assets, every worker, the approval screens and the Intake App", "Orchestrator folder `Shared/ClaimsSolution`"],
          ["Demo **policies** and **claim history**, with the customer email set to **your own address**", "The `PolicyMaster` and `ClaimHistory` tables"],
          ["The workshop solution **MotorInsuranceClaimManagement**, linked to that environment", "Your Studio Web"]
        ] },
        { t: "text", text: "No claims exist yet. You create one when you want to test." }
      ]),
      h("h2", { class: "sec", text: "2. Configure your connections" }),
      blocks([
        { t: "text", text: "The case sends real emails through **Gmail** and starts from a row in **Data Fabric**. Both need a connection that belongs to you." },
        { t: "ol", items: [
          "In **Studio Web**, open the solution **MotorInsuranceClaimManagement**, then its **Connections** item. It lists **Data Fabric connection** and **Gmail connection**.",
          "Click **Data Fabric connection** and connect. It uses your UiPath sign-in, so there is nothing to type.",
          "Click **Gmail connection** and connect. A Google window opens. Choose an account **whose inbox you can open**."
        ] },
        { t: "check", text: "Both connections show as connected, with no warning." },
        { t: "why", text: "The customer emails are sent from your Gmail connection to **your own email address**, so you see exactly what a customer would receive." },
        { t: "stuck", text: "If a connection says **expired**, open it and use **Login** (or **Reconnect**) once more." }
      ]),
      h("h2", { class: "sec", text: "3. See a finished case run" }),
      p("Rahul is the clean case: a valid policy, all seven documents, no fraud signs. You run the **finished** case once, so you see what you are going to build."),
      blocks([
        { t: "ol", items: [
          "Go back to **MotorClaimsWorkshop_Setup > SetupWorkshop** and press **Debug**. Set **Action** to `RegisterClaim` and **Customer** to `Rahul`. Run it.",
          "In the solution **MotorInsuranceClaimManagement**, open **5_Complete** and press **Debug**. Choose **CLM-1001** and pick your **Data Fabric** and **Gmail** connections.",
          "The case stops at **Review**. Open **Action Center > Tasks**, open **Review the claim and decide**, choose **Approve** and submit."
        ] },
        { t: "check", items: [
          "Setup said **CLM-1001 (Rahul Sharma): 7 documents uploaded, claim registered**.",
          "In Studio Web the case shows every stage completed.",
          "In **Data Fabric > MotorInsuranceClaim** the row **CLM-1001** is **Closed**, with a settlement amount and payment reference.",
          "A customer email arrived in your inbox."
        ] },
        { t: "stuck", items: [
          "**Debug cannot find the claim.** Run Setup with `RegisterClaim` for Rahul again.",
          "**A policy problem.** Run Setup with **Action** = `LoadData`, then Debug again.",
          "**No task in Action Center.** Wait a minute and refresh. The agents take time to read the documents.",
          "**Anything else.** Run Setup with **Action** = `Status` and send the facilitator what you see."
        ] }
      ]),
      h("div", { class: "next" }, h("a", { class: "btn primary", href: "#/c1" }, "Next: Chapter 1, the happy path"))
    ];
  }

  function pageChapter1() {
    return [
      pageHead("Chapter 1", "The happy path", "You build five stages in a line, run Rahul's claim through them, and deploy it. Nothing goes wrong yet. That is on purpose."),
      caseMap(),
      h("h2", { class: "sec", text: "Before you start" }),
      blocks([
        { t: "ol", items: [
          "In **Studio Web**, open **MotorInsuranceClaimManagement**, then the project **MyClaimsCase**. You see one circle: the trigger, named MotorInsuranceClaim. That is your blank case.",
          "If the designer shows a note about connections, bind **Data Fabric** to your connection.",
          "Click an empty part of the canvas to open **Case plan properties**. Set **Case ID** to **External key** with the value below."
        ] },
        { t: "code", text: "vars.response?.ClaimId" },
        { t: "why", text: "The case is identified by the claim number. Anyone searching for a claim finds its case, and a duplicate claim number cannot start two cases." }
      ]),
      h("h2", { class: "sec", text: "Five words you need" }),
      blocks([{ t: "cards", items: [
        { title: "Stage", text: "A phase of the process. The case moves from stage to stage. Every stage has a name, tasks and rules." },
        { title: "Task", text: "One piece of work inside a stage: run an agent, call a function, ask a person. It has inputs (what you give it) and outputs (what it gives back)." },
        { title: "Variable", text: "A task's outputs are kept as case variables, like `vars.policyValid`. Later tasks and rules read them. Your claim as it was at the start is `vars.response`." },
        { title: "Rule", text: "Rules decide when things happen. An **entry rule** starts a stage. A **completion rule** says when it is done. A **task rule** says when a task runs." },
        { title: "Required", text: "A task marked required (`*`) must finish before its stage can complete. A task that only sometimes runs must not be required." }
      ] }]),
      p("`vars.response?.ClaimId` uses `?.` so that a missing value gives nothing instead of an error. Use it for `vars.response`.", "muted small"),
      h("h2", { class: "sec", text: "How each stage page works" }),
      blocks([{ t: "ol", items: [
        "**Read the story.** What is happening in the business at this point?",
        "**Think.** What does this stage need: which activities, when does it start, when is it done? Press **Hint** if you want a nudge. Press **Reveal** when you are ready.",
        "**Tell yourself how close you were.** Nobody sees it but you.",
        "**Build it.** Every name and value has a Copy button.",
        "**Check it**, and move on."
      ] }]),
      p("Keep the activity list open while you think. Press **Activities** at the top of any page.", "muted"),
      h("div", { class: "next" }, h("a", { class: "btn primary", href: "#/intake" }, "Start with Intake"))
    ];
  }

  function pageDeploy() {
    return [
      pageHead("Chapter 1, finale", "Run it, then deploy it", "Your five stages are in a line. First prove it works in Debug. Then deploy it with the standard Publish and Upgrade buttons, and watch it in Maestro."),
      caseMap({ compact: true }),
      h("h2", { class: "sec", text: "1. Run it in Debug" }),
      blocks([
        { t: "ol", items: [
          "Run Setup with **Action** = `RegisterClaim` and **Customer** = `Rahul`, if you have not already. It creates claim **CLM-1001**.",
          "In **MyClaimsCase**, press **Debug**, choose **CLM-1001** and pick your connections.",
          "When **Review the claim and decide** appears in **Action Center > Tasks**, open it and press **Approve**.",
          "Watch the case move: Intake, Assessment, Review, Settlement, Closure."
        ] },
        { t: "check", items: [
          "The instance reaches **Completed**.",
          "The trail is Intake, Assessment, Review, Settlement, Closure.",
          "Rahul's settlement is **162,400** with payment reference `PAY-CLM-<number>`."
        ] },
        { t: "stuck", text: "Open the example case `1_HappyPath` and compare. It also includes a few conditions you add in later chapters, so small differences are expected." }
      ]),
      h("h2", { class: "sec", text: "2. Deploy it" }),
      blocks([
        { t: "ol", items: [
          "**Remove the example cases.** In Studio Web open the three-dot menu of each of `1_HappyPath`, `2_PendingCustomer`, `3_Denied`, `4_FraudInvestigation` and `5_Complete` and remove it from the solution. Keep **MyClaimsCase**, the workers, the approval screens and the Intake App.",
          "Press **Publish** on **MotorInsuranceClaimManagement**. Pack to **Shared** and keep the version Studio Web proposes. If it says that version exists, raise the last number.",
          "Open **Orchestrator > Solutions > Deployments** at the **tenant** level (the Solutions tab is hidden when a folder is selected). Open your environment `ClaimsSolution`, choose the three-dot menu and **Upgrade** to the new version.",
          "In the wizard, bind your **Gmail** and **Data Fabric** connections. If one is expired, use **Login to connection**.",
          "When it finishes, choose **Activate**.",
          "Open your **Intake App** address, sign in, register a claim with its documents, and open **Maestro > Case management**. Your case runs."
        ] },
        { t: "why", text: "Upgrade adds your case to the same folder as the Intake App, tables and workers. Nothing is duplicated. Activation is needed because the case starts from a claim row, and that start event runs through your Data Fabric connection." },
        { t: "note", text: "Whatever cases are still in the solution when you Publish get deployed, and each starts on every new claim. That is why step 1 removes the examples. If you want an example back later, import `MotorClaims_Workshop.uis` from the kit." },
        { t: "check", text: "Your case appears under **Maestro > Case management**, and a claim registered in the Intake App starts an instance." }
      ]),
      h("div", { class: "next" }, h("span", { class: "muted" }, "Chapter 2 opens later in the workshop: what happens when documents are missing."))
    ];
  }

  /* ---------- stage page ---------- */
  function pageStage(id) {
    var sp = D.STAGE_PAGES[id], s = stage(id);
    var idx = primaries().map(function (x) { return x.id; }).indexOf(id);
    var calls = 0;
    var root = [];
    root.push(caseMap({ compact: true, current: id }));
    root.push(pageHead("Chapter 1 · Stage " + (idx + 1) + " of 5", sp.title, sp.tagline));

    /* story */
    root.push(h("section", { class: "story" },
      h("div", { class: "sec-k" }, "The business story"),
      sp.story.map(function (t) { return p(t); })));

    /* think */
    root.push(h("section", {},
      h("div", { class: "sec-k" }, "Think first"),
      h("p", { class: "muted" }, "What does this stage need? Think about it, say it out loud, then reveal. Keep the activity list open if it helps."),
      sp.think.map(function (card) { return thinkCard(id, card); })));

    /* build */
    root.push(h("section", {},
      h("div", { class: "sec-k" }, "Build it"),
      h("p", { class: "muted" }, "Do these in order in **MyClaimsCase**. Every value has a Copy button.".replace(/\*\*/g, "")),
      h("ol", { class: "steps" }, sp.build.map(function (step, i) {
        var key = id + ":" + i;
        var box = h("input", { type: "checkbox", id: "st-" + key, "aria-label": "Mark step done" });
        box.checked = !!S.done[key];
        box.addEventListener("change", function () { S.done[key] = box.checked; save(); li.classList.toggle("done", box.checked); });
        var li = h("li", { class: "step" + (S.done[key] ? " done" : "") },
          h("div", { class: "step-h" }, box, h("label", { for: "st-" + key }, h("span", { class: "step-no" }, String(i + 1)), step.title)),
          h("div", { class: "step-b" }, blocks(step.blocks)));
        return li;
      }))));

    /* check */
    var builtBox = h("input", { type: "checkbox", id: "built-" + id });
    builtBox.checked = !!S.built[id];
    builtBox.addEventListener("change", function () { S.built[id] = builtBox.checked; save(); });
    root.push(h("section", {},
      h("div", { class: "sec-k" }, "Check it"),
      blocks([{ t: "check", items: sp.check }]),
      h("label", { class: "builtbox", for: "built-" + id }, builtBox, h("span", {}, "I built and checked this stage"))));

    /* example case */
    root.push(h("p", { class: "muted small" }, rich("Stuck? Open the example case `1_HappyPath` and compare. It already has a few conditions that this chapter leaves for later, so small differences are expected.")));

    /* prev / next */
    var prev = idx > 0 ? primaries()[idx - 1] : null;
    var next = idx < 4 ? primaries()[idx + 1] : null;
    root.push(h("div", { class: "pager" },
      prev ? h("a", { class: "btn", href: "#/" + prev.id }, "← " + prev.name) : h("a", { class: "btn", href: "#/c1" }, "← Chapter 1"),
      next ? h("a", { class: "btn primary", href: "#/" + next.id }, next.name + " →") : h("a", { class: "btn primary", href: "#/deploy" }, "Run it and deploy →")));
    return root;
  }

  function thinkCard(stageId, card) {
    var key = stageId + ":" + card.id;
    var wrap = h("div", { class: "think", id: "think-" + card.id });
    function paint() {
      wrap.textContent = "";
      var r = REVEAL[key] || {};
      wrap.appendChild(h("div", { class: "think-top" }, h("span", { class: "think-kind" }, card.kind), r.answer ? h("span", { class: "chip soft" }, "Revealed") : null));
      wrap.appendChild(h("p", { class: "think-q" }, rich(card.q)));
      if (!r.answer) {
        var row = h("div", { class: "think-actions" });
        if (!r.hint) row.appendChild(h("button", { class: "btn small", type: "button", onclick: function () { REVEAL[key] = Object.assign({}, r, { hint: true }); paint(); } }, "Hint"));
        row.appendChild(h("button", { class: "btn small primary", type: "button", onclick: function () { REVEAL[key] = Object.assign({}, r, { answer: true }); paint(); } }, "Reveal"));
        wrap.appendChild(row);
        if (r.hint) wrap.appendChild(h("div", { class: "hint" }, h("span", { class: "k" }, "Hint "), rich(card.hint)));
        return;
      }
      var a = card.answer;
      var ans = h("div", { class: "answer" });
      ans.appendChild(p(a.lead, "answer-lead"));
      if (a.tasks) ans.appendChild(h("div", { class: "tasklist" }, a.tasks.map(function (t) { return actChip(t.act, t); })));
      if (a.rules) a.rules.forEach(function (rule, i) { ans.appendChild(ruleCard(rule, key + ":r" + i)); });
      if (a.note) ans.appendChild(h("div", { class: "answer-note" }, rich(a.note)));
      wrap.appendChild(ans);
      /* self-check */
      var ck = key, cur = S.call[ck];
      var opts = [["nailed", "Nailed it"], ["close", "Close"], ["missed", "New to me"]];
      wrap.appendChild(h("div", { class: "selfcheck" }, h("span", { class: "k" }, "How close were you? "),
        opts.map(function (o) {
          return h("button", { class: "pill" + (cur === o[0] ? " on on-" + o[0] : ""), type: "button",
            onclick: function () { S.call[ck] = o[0]; save(); paint(); } }, o[1]);
        }),
        h("button", { class: "linkbtn", type: "button", onclick: function () { delete REVEAL[key]; paint(); } }, "Hide the answer")));
    }
    paint();
    return wrap;
  }

  /* ---------- activities drawer ---------- */
  var drawerState = { type: "all", q: "", stage: "all" };
  var drawer, drawerBody, scrim;
  function buildDrawer() {
    scrim = h("div", { class: "scrim", onclick: closeDrawer });
    drawerBody = h("div", { class: "drawer-body" });
    var closeBtn = h("button", { class: "btn small", type: "button", onclick: closeDrawer, "aria-label": "Close the activity list" }, "Close");
    drawer = h("aside", { class: "drawer", role: "dialog", "aria-label": "Activities", "aria-hidden": "true" },
      h("div", { class: "drawer-h" }, h("div", {}, h("h2", { text: "Activities" }),
        h("p", { class: "muted small" }, "Named exactly as in the Studio Web task picker.")), closeBtn),
      drawerBody);
    document.body.appendChild(scrim);
    document.body.appendChild(drawer);
  }
  function paintDrawer(focusName) {
    drawerBody.textContent = "";
    var search = h("input", { type: "search", class: "search", placeholder: "Search, for example fraud", value: drawerState.q, "aria-label": "Search activities" });
    search.addEventListener("input", function () { drawerState.q = search.value; paintList(); });
    var chips = h("div", { class: "filters" });
    [["all", "All"], ["agent", "Agents"], ["function", "Functions"], ["api", "API workflows"], ["human", "Human tasks"], ["connector", "Connectors"]].forEach(function (f) {
      chips.appendChild(h("button", { class: "pill" + (drawerState.type === f[0] ? " on" : ""), type: "button",
        onclick: function () { drawerState.type = f[0]; paintDrawer(); } }, f[1]));
    });
    var stageSel = h("select", { class: "select", "aria-label": "Filter by stage" });
    [["all", "All stages"]].concat(primaries().map(function (s) { return [s.id, s.name]; })).forEach(function (o) {
      var op = h("option", { value: o[0], text: o[1] }); if (drawerState.stage === o[0]) op.selected = true; stageSel.appendChild(op);
    });
    stageSel.addEventListener("change", function () { drawerState.stage = stageSel.value; paintList(); });
    var list = h("div", { class: "actlist" });
    drawerBody.appendChild(search); drawerBody.appendChild(chips); drawerBody.appendChild(stageSel); drawerBody.appendChild(list);
    function paintList() {
      list.textContent = "";
      var q = drawerState.q.trim().toLowerCase();
      var shown = D.ACTIVITIES.filter(function (a) {
        if (drawerState.type !== "all" && a.type !== drawerState.type) return false;
        if (drawerState.stage !== "all" && a.stages.indexOf(drawerState.stage) < 0) return false;
        if (q && (a.name + " " + a.line + " " + a.gives.join(" ")).toLowerCase().indexOf(q) < 0) return false;
        return true;
      });
      if (!shown.length) list.appendChild(h("p", { class: "muted" }, "Nothing matches."));
      shown.forEach(function (a) { list.appendChild(actCard(a, { noLinks: false })); });
      if (focusName) {
        var el = document.getElementById("act-" + focusName);
        if (el) { el.scrollIntoView({ block: "center" }); el.classList.add("flash"); }
        focusName = null;
      }
    }
    paintList();
  }
  function openDrawer(name) {
    if (name) { drawerState = { type: "all", q: "", stage: "all" }; }
    else {
      var m = /^#\/(intake|assessment|review|settlement|closure)$/.exec(location.hash);
      if (m && drawerState.stage === "all") drawerState.stage = m[1];
    }
    paintDrawer(name);
    document.body.classList.add("drawer-open");
    drawer.setAttribute("aria-hidden", "false");
  }
  function closeDrawer() { document.body.classList.remove("drawer-open"); drawer.setAttribute("aria-hidden", "true"); }

  /* ---------- router ---------- */
  var STAGE_IDS = ["intake", "assessment", "review", "settlement", "closure"];
  function route() {
    var id = (location.hash.replace(/^#\/?/, "") || "home");
    var view;
    if (id === "home") view = pageHome();
    else if (id === "scenario") view = pageScenario();
    else if (id === "setup") view = pageSetup();
    else if (id === "c1") view = pageChapter1();
    else if (id === "deploy") view = pageDeploy();
    else if (STAGE_IDS.indexOf(id) >= 0) view = pageStage(id);
    else { id = "home"; view = pageHome(); }
    app.textContent = "";
    add(app, h("div", { class: "page", "data-page": id }, view));
    window.scrollTo(0, 0);
    document.title = (id === "home" ? "" : (D.STAGE_PAGES[id] ? D.STAGE_PAGES[id].title : id.charAt(0).toUpperCase() + id.slice(1)) + " | ") + "Motor Claims workshop";
    document.querySelectorAll("[data-nav]").forEach(function (a) {
      a.classList.toggle("on", a.getAttribute("data-nav") === id || (a.getAttribute("data-nav") === "c1" && (STAGE_IDS.indexOf(id) >= 0 || id === "deploy")));
    });
    app.focus({ preventScroll: true });
  }

  /* ---------- chrome: top bar, theme, present mode, keys ---------- */
  function go(delta) {
    var cur = location.hash.replace(/^#\/?/, "") || "home";
    var i = D.ORDER.indexOf(cur); if (i < 0) i = 0;
    var j = Math.max(0, Math.min(D.ORDER.length - 1, i + delta));
    location.hash = "#/" + D.ORDER[j];
  }
  function setPresent(on) {
    document.documentElement.classList.toggle("present", on);
    try { localStorage.setItem(KEY + "-present", on ? "1" : "0"); } catch (e) { /* ignore */ }
    var b = document.getElementById("btn-present"); if (b) { b.textContent = on ? "Exit present" : "Present"; b.setAttribute("aria-pressed", on ? "true" : "false"); }
  }
  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem(KEY + "-theme", t); } catch (e) { /* ignore */ }
  }
  function buildChrome() {
    var nav = document.getElementById("nav");
    [["home", "#/", "Home"], ["scenario", "#/scenario", "Scenario"], ["setup", "#/setup", "Setup"], ["c1", "#/c1", "Build"]].forEach(function (n) {
      nav.appendChild(h("a", { href: n[1], "data-nav": n[0] }, n[2]));
    });
    var tools = document.getElementById("tools");
    tools.appendChild(h("button", { class: "btn small", type: "button", onclick: function () { openDrawer(); } }, "Activities"));
    tools.appendChild(h("button", { class: "btn small", type: "button", id: "btn-present", "aria-pressed": "false", onclick: function () { setPresent(!document.documentElement.classList.contains("present")); } }, "Present"));
    tools.appendChild(h("button", { class: "btn small", type: "button", id: "btn-theme", onclick: function () {
      var cur = document.documentElement.getAttribute("data-theme");
      var dark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
      setTheme(dark ? "light" : "dark");
    } }, "Light / dark"));
    var th; try { th = localStorage.getItem(KEY + "-theme"); } catch (e) { th = null; }
    if (th) document.documentElement.setAttribute("data-theme", th);
    var pr; try { pr = localStorage.getItem(KEY + "-present"); } catch (e) { pr = null; }
    if (pr === "1") setPresent(true);
    document.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.key === "Escape") closeDrawer();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "a" || e.key === "A") openDrawer();
      else if (e.key === "p" || e.key === "P") setPresent(!document.documentElement.classList.contains("present"));
    });
  }

  buildChrome();
  buildDrawer();
  window.addEventListener("hashchange", route);
  route();
})();
