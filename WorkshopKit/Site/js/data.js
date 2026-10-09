/* All site content. Facts come from WorkshopKit/CASE_FLOW_PLAN.md and Participant_Build_Guide.md.
   Text supports: **bold**, `code`, [label](#/route).
   A stage page is a story plus ordered STEPS. A step with a question (q) is "think, hint, reveal, then build". */
window.DATA = (function () {

  var TYPES = {
    agent:    { label: "Agent",        studio: "Agent",              icon: "A" },
    function: { label: "Function",     studio: "Function (process)", icon: "F" },
    api:      { label: "API workflow", studio: "API workflow",       icon: "W" },
    human:    { label: "Human task",   studio: "Action",             icon: "H" },
    connector:{ label: "Connector",    studio: "Connector",          icon: "C" }
  };

  var ACTIVITIES = [
    { name: "ClaimDocumentIntelligence", type: "agent", stages: ["intake"], chapter: 1,
      line: "Reads the claim PDFs and says whether the set is complete, contradicts itself, or is missing something.",
      gives: ["documentIngestionStatus", "extractedRepairEstimate", "documentInconsistencies", "missingDocuments"] },
    { name: "ValidatePolicy", type: "function", stages: ["intake"], chapter: 1,
      line: "Checks the policy exists, is active, matches the vehicle and covers the incident date. Also finds the customer's email.",
      gives: ["policyValid", "policyValidationReason", "customerEmail"] },
    { name: "FraudRiskAssessment", type: "agent", stages: ["assessment"], chapter: 1,
      line: "Scores how suspicious the claim looks (0 to 100) and explains why.",
      gives: ["fraudScore", "riskLevel", "fraudFlag", "fraudReasons"] },
    { name: "AssessDamage", type: "api", stages: ["assessment"], chapter: 1,
      line: "Turns the repair estimate from the documents into the damage estimate.",
      gives: ["damageEstimate"] },
    { name: "AdjusterReview", type: "human", stages: ["review"], chapter: 1,
      line: "The adjuster's screen. Shows everything found so far; they press Approve, Reject or RequestInformation.",
      gives: ["decision", "comments"] },
    { name: "CalculateSettlement", type: "function", stages: ["settlement"], chapter: 1,
      line: "Works out the payable amount and whether a senior approver is needed.",
      gives: ["settlementAmount", "seniorApprovalRequired"] },
    { name: "SeniorApproval", type: "human", stages: ["settlement"], chapter: 1,
      line: "A senior approver signs off a large settlement before anything is paid.",
      gives: ["decision2", "comments2"] },
    { name: "ProcessSettlement", type: "function", stages: ["settlement"], chapter: 1,
      line: "Records the payment, once per claim, and returns the payment reference.",
      gives: ["settlementStatus", "paymentReference", "settlementDate"] },
    { name: "GenerateClaimPacket", type: "api", stages: ["closure"], chapter: 1,
      line: "Creates the claim packet reference for the file.",
      gives: ["claimPacketReference"] },
    { name: "CreateCustomerNotification", type: "api", stages: ["closure"], chapter: 1,
      line: "Writes the outcome message for the customer. Sending it by email comes in a later chapter.",
      gives: ["notificationStatus", "claimOutcome", "notificationText"] },
    { name: "FraudInvestigation", type: "human", stages: ["fraud"], chapter: 4,
      line: "An investigator looks at a high-risk claim and presses Cleared or Confirmed.",
      gives: ["fraudResult", "comments3"] },
    { name: "UpdateClaim", type: "function", stages: ["every stage"], chapter: 5,
      line: "Saves the stage and status on the claim row so anyone can see where a claim is.",
      gives: ["Updated"] },
    { name: "UiPath Data Fabric", type: "connector", stages: ["pending"], chapter: 2,
      line: "Starts the case when a claim row is created, and later waits for the customer's missing document.",
      gives: [] },
    { name: "Gmail", type: "connector", stages: ["pending"], chapter: 2,
      line: "Sends real emails to the customer.",
      gives: [] }
  ];

  var STAGES = [
    { id: "intake", name: "Intake", short: "Read the paperwork, check the cover", kind: "primary" },
    { id: "assessment", name: "Assessment", short: "Judge the risk, size the damage", kind: "primary" },
    { id: "review", name: "Review", short: "A person decides", kind: "primary" },
    { id: "settlement", name: "Settlement", short: "Work out the money and pay", kind: "primary" },
    { id: "closure", name: "Closure", short: "Wrap up and tell the customer", kind: "primary" },
    { id: "pending", name: "Pending Customer", short: "Waiting for the customer", kind: "secondary", chapter: 2 },
    { id: "denied", name: "Denied", short: "Three ways to a no", kind: "secondary", chapter: 3 },
    { id: "fraud", name: "Fraud Investigation", short: "Cleared or confirmed", kind: "secondary", chapter: 4 }
  ];

  var CHAPTERS = [
    { id: "c1", no: 1, title: "The happy path", sub: "Five stages in a line, then deploy", open: true },
    { id: "c2", no: 2, title: "Missing documents", sub: "The Pending Customer stage", open: false },
    { id: "c3", no: 3, title: "Denied", sub: "Three ways to a no", open: false },
    { id: "c4", no: 4, title: "Fraud investigation", sub: "Cleared or confirmed", open: false },
    { id: "c5", no: 5, title: "The complete case", sub: "Record updates, emails, time limits", open: false }
  ];

  var SEQ = "Runs sequentially";

  /* ---------- Reusable step builders ---------- */
  function addStage(name, description) {
    return { title: "Add the stage", build: [
      { t: "kv", rows: [["Name", name], ["Description", description]] }
    ] };
  }
  function entryStep(q, hint, lead, rule, build) {
    return { title: "When does it start?", kind: "Way in", q: q, hint: hint,
      answer: { lead: lead, rules: [rule] }, build: build };
  }
  function doneStep(q, hint, lead, rule, build, note) {
    return { title: "When is it done?", kind: "Done when", q: q, hint: hint,
      answer: { lead: lead, rules: [rule], note: note }, build: build };
  }
  function leaveStep(q, hint, lead, scenarios) {
    return { title: "When should a claim leave early?", kind: "Leave early", q: q, hint: hint,
      answer: { lead: lead, scenarios: scenarios },
      build: [{ t: "heads", text: "**Nothing to build here yet.** You come back to this stage in the chapters named above and add these exits then." }] };
  }
  var MARK = "Tick **Marks stage complete** on this rule, so the case moves on to the next stage.";

  var STAGE_PAGES = {

    /* ============================ INTAKE ============================ */
    intake: {
      title: "Intake",
      tagline: "Read the paperwork. Check the cover.",
      story: [
        "A customer has had an accident. They open the Intake App, enter their policy number and the claim amount, and upload their documents: the claim form, police report, photos, repair estimate, licence, registration and policy copy.",
        "In the old world a clerk opens every PDF, then opens a spreadsheet to see whether the policy is even live. That takes days, and nobody can say where the claim is.",
        "In your case, the moment a claim lands the case starts. The first stage has to find out two things before anyone else spends a minute on it: **what do the documents say**, and **is the customer actually covered**."
      ],
      steps: [
        addStage("Intake", "Reads the claim documents with an AI agent and checks the policy is valid."),
        { title: "Job 1: make sense of the documents", kind: "Which activity?",
          q: "The first job: read the documents the customer uploaded and say whether they are complete, whether they contradict each other, and pull out the facts. Which activity does that?",
          hint: "Someone has to read PDFs and understand them. Think of the activity types in the panel.",
          answer: { lead: "An **agent**. Reading and judging documents is what AI is for.",
            tasks: [{ act: "ClaimDocumentIntelligence", required: true }] },
          build: [
            { t: "text", text: "Add a task to Intake." },
            { t: "kv", rows: [["Type", "Agent"], ["Resource", "ClaimDocumentIntelligence"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["DocumentReferences", "vars.response?.DocumentReferences"]
            ] },
            { t: "note", text: "Keep the default output variable names. They are the `camelCase` versions of the output names, for example `documentIngestionStatus`." },
            { t: "why", text: "`vars.response` is the claim as it was when the case started. `?.` gives nothing instead of an error if a value is missing." }
          ] },
        { title: "Job 2: check the cover", kind: "Which activity?",
          q: "The second job: is the customer actually covered? The policy must exist, be active, match the vehicle, and the accident must fall inside the cover period. Which activity?",
          hint: "This is a fixed set of rules. The answer should be the same every time. No AI needed.",
          answer: { lead: "A **function**: plain code that always gives the same answer for the same input.",
            tasks: [{ act: "ValidatePolicy", required: true }] },
          build: [
            { t: "text", text: "Add a second task to Intake." },
            { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "ValidatePolicy"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["PolicyNumber", "vars.response?.PolicyNumber"],
              ["VehicleRegistration", "vars.response?.VehicleRegistration"],
              ["IncidentDate", "vars.response?.IncidentDate"]
            ] },
            { t: "note", text: "Leave the optional input **DataFolder** empty. The workers find the data themselves." }
          ] },
        { title: "Can we make it faster?", kind: "Faster?",
          q: "Right now the second task waits for the first. Does the policy check need the document result, or the other way round? Can we make this faster?",
          hint: "What if both started at the same moment?",
          answer: { lead: "Yes. **Neither needs the other's answer**, so both can start together, **in parallel**.",
            tasks: [
              { act: "ClaimDocumentIntelligence", required: true, rule: { name: "Start document analysis", type: SEQ } },
              { act: "ValidatePolicy", required: true, rule: { name: "Start policy validation", type: SEQ } }
            ] },
          build: [
            { t: "ol", items: [
              "Place the two tasks side by side, in parallel, instead of one after the other. (The designer lets you add a task beside another.)",
              "Give each task its start rule:"
            ] },
            { t: "kv", rows: [["Rule on ClaimDocumentIntelligence", "Start document analysis"], ["Rule on ValidatePolicy", "Start policy validation"], ["Type (both)", "Runs sequentially"]] },
            { t: "why", text: "Running them together saves time, and a claim waits for nobody." }
          ] },
        entryStep(
          "This is the first stage of the case. What should make it start?",
          "Nothing comes before it.",
          "It starts when the case itself starts.",
          { label: "Entry rule", name: "Case started", type: "Case entered", plain: "Start this stage the moment the case starts.", expr: null,
            why: "Intake is the first stage. There is no earlier stage to wait for." },
          [{ t: "kv", rows: [["Name", "Case started"], ["Type", "Case entered"]] }]),
        doneStep(
          "When can you say Intake is completely fine, and the claim can move on?",
          "Think about the tasks. What must be true for the stage to be done?",
          "When both required tasks have finished. Nothing more, for now.",
          { label: "Completion rule", name: "Documents analysed and policy checked", type: "Required tasks completed",
            plain: "Intake is done when both required tasks have finished.", expr: null,
            why: "Keep it simple for now. Later this rule learns to say what a good result looks like, and that is when missing documents and invalid policies get their own paths." },
          [{ t: "kv", rows: [["Name", "Documents analysed and policy checked"], ["Completes the stage when", "Required tasks completed"]] },
           { t: "note", text: "No expression for now." }],
          MARK),
        leaveStep(
          "Think about what could go wrong at Intake. When should a claim leave this stage for somewhere else?",
          "Two things can go wrong, one with the paperwork and one with the cover.",
          "Two things can pull a claim out of Intake:",
          [
            { what: "Documents are missing", goes: "Pending Customer", chapter: 2 },
            { what: "The policy is not valid", goes: "Denied", chapter: 3 }
          ])
      ],
      check: [
        "Intake shows two tasks, side by side, both marked as required (a `*`).",
        "Intake has one entry rule (Case started) and one completion rule."
      ]
    },

    /* ============================ ASSESSMENT ============================ */
    assessment: {
      title: "Assessment",
      tagline: "Judge the risk. Size the damage.",
      story: [
        "The papers have been read and the policy is confirmed. Before a person looks at the claim, the insurer wants two more answers.",
        "**Does anything look suspicious?** The amount, the history, the way the documents fit together. An AI agent can weigh that up and say why. **How big is the loss?** The repair estimate is already in the documents, so this is a straightforward calculation.",
        "Both answers will be put in front of the adjuster in the next stage, so that the human decides with full information."
      ],
      steps: [
        addStage("Assessment", "Scores the fraud risk with an AI agent and works out the damage estimate from the repair estimate. Both run together."),
        { title: "Job 1: how suspicious does it look?", kind: "Which activity?",
          q: "The first job: judge whether the claim looks suspicious, with reasons, from the amount, the history and any conflicts in the documents. Which activity?",
          hint: "It is a judgement call that comes with an explanation. Same type as the document reader.",
          answer: { lead: "An **agent**. It scores the risk from 0 to 100 and says why.",
            tasks: [{ act: "FraudRiskAssessment", required: true }] },
          build: [
            { t: "text", text: "Add a task to Assessment." },
            { t: "kv", rows: [["Type", "Agent"], ["Resource", "FraudRiskAssessment"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["PolicyNumber", "vars.response?.PolicyNumber"],
              ["ClaimAmount", "vars.response?.ClaimAmount"],
              ["IncidentDate", "vars.response?.IncidentDate"],
              ["IncidentDescription", "vars.response?.IncidentDescription"],
              ["ExtractedRepairEstimate", "vars.extractedRepairEstimate"],
              ["DocumentInconsistencies", "vars.documentInconsistencies"]
            ] },
            { t: "why", text: "The last two inputs come from Intake. That is why Assessment has to come after Intake." }
          ] },
        { title: "Job 2: how big is the loss?", kind: "Which activity?",
          q: "The second job: put a number on the damage, using the repair estimate that was pulled out of the documents. Which activity?",
          hint: "A small calculation. It does not need an agent or a person.",
          answer: { lead: "An **API workflow**, a tiny calculation that turns the repair estimate into the damage estimate.",
            tasks: [{ act: "AssessDamage", required: true }] },
          build: [
            { t: "text", text: "Add a second task to Assessment." },
            { t: "kv", rows: [["Type", "API workflow"], ["Resource", "AssessDamage"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [["ExtractedRepairEstimate", "vars.extractedRepairEstimate"]] }
          ] },
        { title: "Can we make it faster?", kind: "Faster?",
          q: "Does the damage estimate need the fraud score, or the other way round? Can these two run at the same time?",
          hint: "Look at the inputs of each task. Does either use the other's output?",
          answer: { lead: "Yes. Both only need what Intake produced, so they run **in parallel**.",
            tasks: [
              { act: "FraudRiskAssessment", required: true, rule: { name: "Start fraud risk assessment", type: SEQ } },
              { act: "AssessDamage", required: true, rule: { name: "Start damage assessment", type: SEQ } }
            ] },
          build: [
            { t: "text", text: "Place the two tasks side by side, then give each its start rule:" },
            { t: "kv", rows: [["Rule on FraudRiskAssessment", "Start fraud risk assessment"], ["Rule on AssessDamage", "Start damage assessment"], ["Type (both)", "Runs sequentially"]] }
          ] },
        entryStep(
          "What must have finished before Assessment can start? Why can it not simply run beside Intake?",
          "Look at the inputs of the two tasks you just added.",
          "Intake must be completed first. Both tasks use what Intake produced: the repair estimate and any conflicts between documents.",
          { label: "Entry rule", name: "Intake completed", type: "Selected stage completed", plain: "Start Assessment when Intake has completed.", expr: null, stage: "Intake",
            why: "Assessment needs `extractedRepairEstimate` and `documentInconsistencies` from Intake." },
          [{ t: "kv", rows: [["Name", "Intake completed"], ["Type", "Selected stage completed"], ["Stage", "Intake"]] }]),
        doneStep(
          "When can you say Assessment is completely fine?",
          "The same idea as Intake.",
          "When both required tasks have finished.",
          { label: "Completion rule", name: "Fraud score and damage estimate ready", type: "Required tasks completed",
            plain: "Assessment is done when both required tasks have finished.", expr: null },
          [{ t: "kv", rows: [["Name", "Fraud score and damage estimate ready"], ["Completes the stage when", "Required tasks completed"]] },
           { t: "note", text: "No expression for now." }],
          MARK),
        leaveStep(
          "What could the assessment find that should stop the claim here, before a person sees it?",
          "Think about what the fraud score might say.",
          "One thing can pull a claim out of Assessment:",
          [{ what: "The fraud risk is High (a score of 70 or more)", goes: "Fraud Investigation", chapter: 4 }])
      ],
      check: [
        "Assessment shows two required tasks, side by side.",
        "Its entry rule points at Intake."
      ]
    },

    /* ============================ REVIEW ============================ */
    review: {
      title: "Review",
      tagline: "A person owns the decision.",
      story: [
        "The claim now has a policy result, a damage estimate and a fraud score. Money is about to be decided, so a person must own the decision: the claims adjuster.",
        "The adjuster does not open PDFs or spreadsheets. They get one screen in Action Center with everything the machines found, and three buttons: **Approve**, **Reject** and **RequestInformation**.",
        "For this chapter the adjuster presses Approve. You will play the adjuster yourself."
      ],
      steps: [
        addStage("Review", "A claims adjuster reviews the documents, policy result and fraud assessment, then approves, rejects or asks the customer for more information."),
        { title: "The job: someone decides", kind: "Which activity?",
          q: "The insurer wants a person to own this decision. How does the case put the claim in front of them, and what do they get back?",
          hint: "Not an agent, not code. A person, working in Action Center.",
          answer: { lead: "A **human task**. The case creates a task in Action Center and waits until the person submits it.",
            tasks: [{ act: "AdjusterReview", required: true, rule: { name: "Start adjuster review", type: SEQ } }] },
          build: [
            { t: "text", text: "Add a task to Review." },
            { t: "kv", rows: [["Type", "Action (human task)"], ["App", "AdjusterReview"], ["Folder", "Shared/ClaimsSolution"], ["Required", "Yes"], ["Task title", "Review the claim and decide"], ["Assign to", "A specific user: yourself"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["CustomerName", "vars.response?.CustomerName"],
              ["ClaimAmount", "vars.response?.ClaimAmount"],
              ["DamageEstimate", "vars.damageEstimate"],
              ["PolicyValid", "vars.policyValid"],
              ["PolicyValidationReason", "vars.policyValidationReason"],
              ["DocumentIngestionStatus", "vars.documentIngestionStatus"],
              ["DocumentInconsistencies", "vars.documentInconsistencies"],
              ["RiskLevel", "vars.riskLevel"],
              ["FraudScore", "vars.fraudScore"],
              ["FraudReasons", "vars.fraudReasons"]
            ] },
            { t: "kv", rows: [["Task rule name", "Start adjuster review"], ["Task rule type", "Runs sequentially"]] },
            { t: "note", text: "Outputs: `decision` (the button pressed) and `comments`." },
            { t: "why", text: "The adjuster is shown everything the machines found, so they decide with full information." }
          ] },
        entryStep(
          "When should the adjuster get the claim?",
          "After the machines have done their part.",
          "When Assessment is completed.",
          { label: "Entry rule", name: "Assessment completed", type: "Selected stage completed", plain: "Start Review when Assessment has completed.", expr: null, stage: "Assessment",
            why: "The adjuster needs the fraud score and damage estimate on their screen." },
          [{ t: "kv", rows: [["Name", "Assessment completed"], ["Type", "Selected stage completed"], ["Stage", "Assessment"]] }]),
        doneStep(
          "When can you say Review is done?",
          "Which task has to be finished?",
          "When the adjuster has submitted their decision.",
          { label: "Completion rule", name: "Adjuster decision recorded", type: "Required tasks completed",
            plain: "Review is done when the adjuster has submitted the task.", expr: null,
            why: "For now any button finishes Review. Later only Approve will complete it, and the other two buttons get their own paths." },
          [{ t: "kv", rows: [["Name", "Adjuster decision recorded"], ["Completes the stage when", "Required tasks completed"]] },
           { t: "note", text: "No expression for now." }],
          MARK),
        leaveStep(
          "The adjuster has three buttons. For which buttons should the claim not carry on to Settlement?",
          "Only one of the three means \"go ahead and pay\".",
          "Two of the three buttons pull a claim out of Review:",
          [
            { what: "Reject", goes: "Denied", chapter: 3 },
            { what: "RequestInformation", goes: "Pending Customer", chapter: 2 }
          ])
      ],
      check: [
        "Review has one human task, titled **Review the claim and decide**, assigned to you.",
        "All eleven inputs are filled."
      ]
    },

    /* ============================ SETTLEMENT ============================ */
    settlement: {
      title: "Settlement",
      tagline: "Work out the money. Pay it once.",
      story: [
        "The adjuster approved. Now the money. The payable amount is the smallest of three numbers (the claim amount, the damage estimate and the policy's cover limit), minus the deductible, never below zero.",
        "Big payouts get a second pair of eyes. Above **175,000**, a senior approver must sign off before anything is paid. Most claims are below that, so for them the approval is skipped.",
        "Then the payment is recorded. Once. A second attempt must never pay twice."
      ],
      steps: [
        addStage("Settlement", "Calculates the payable amount (loss minus deductible, capped at cover). Above the approval threshold a senior approver must approve before payment is recorded."),
        { title: "Job 1: how much do we pay?", kind: "Which activity?",
          q: "The first job: work out the payable amount, and whether it is large enough to need a senior approver. Which activity?",
          hint: "Money is arithmetic, not judgement. The same input must give the same answer.",
          answer: { lead: "A **function**. Plain code, always the same answer.",
            tasks: [{ act: "CalculateSettlement", required: true, rule: { name: "Start settlement calculation", type: SEQ } }] },
          build: [
            { t: "text", text: "Add a task to Settlement." },
            { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "CalculateSettlement"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["PolicyNumber", "vars.response?.PolicyNumber"],
              ["ClaimAmount", "vars.response?.ClaimAmount"],
              ["DamageEstimate", "vars.damageEstimate"]
            ] },
            { t: "kv", rows: [["Task rule name", "Start settlement calculation"], ["Task rule type", "Runs sequentially"]] }
          ] },
        { title: "Job 2: a second opinion for big amounts", kind: "Which activity?",
          q: "Large payouts need a senior person to approve them first. Which activity, and should every claim wait for it?",
          hint: "Another person, in Action Center. Would it be right to make every small claim wait?",
          answer: { lead: "A **human task**, and it is **not required**: for most claims it never runs. If it were required and skipped, the stage would wait forever.",
            tasks: [{ act: "SeniorApproval", required: false }] },
          build: [
            { t: "text", text: "Add a task to Settlement, after the calculation." },
            { t: "kv", rows: [["Type", "Action (human task)"], ["App", "SeniorApproval"], ["Required", "No"], ["Task title", "Approve a settlement above the threshold"], ["Assign to", "A specific user: yourself"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["SettlementAmount", "vars.settlementAmount"],
              ["DamageEstimate", "vars.damageEstimate"]
            ] }
          ] },
        { title: "Job 3: record the payment", kind: "Which activity?",
          q: "The last job: record the payment, once per claim, and get a payment reference back. Which activity?",
          hint: "Code that must never pay twice.",
          answer: { lead: "A **function**. It records the payment once, and a second attempt returns the same payment.",
            tasks: [{ act: "ProcessSettlement", required: true }] },
          build: [
            { t: "text", text: "Add a third task to Settlement." },
            { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "ProcessSettlement"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["CustomerName", "vars.response?.CustomerName"],
              ["PolicyNumber", "vars.response?.PolicyNumber"],
              ["SettlementAmount", "vars.settlementAmount"],
              ["SeniorApprovalRequired", "vars.seniorApprovalRequired"],
              ["SeniorApprovalDecision", "vars.decision2"]
            ] }
          ] },
        { title: "Which tasks should wait, and for what?", kind: "Task rules",
          q: "Two of these tasks should not simply start with the stage. What should the senior approval wait for? And what must be true before the payment is recorded?",
          hint: "One waits for a need. The other waits for permission.",
          answer: { lead: "**SeniorApproval** runs only when the calculation says approval is needed. **ProcessSettlement** pays only if no approval was needed, or it was granted. Nothing is paid before approval.",
            rules: [
              { label: "Task rule on SeniorApproval", name: "Only if senior approval is required", type: SEQ,
                plain: "Run the senior approval only when the settlement is large enough to need it.",
                expr: "vars.seniorApprovalRequired === true", why: "This decides whether an approval is needed." },
              { label: "Task rule on ProcessSettlement", name: "Pay only if no approval needed or approved", type: SEQ,
                plain: "Pay when no approval was needed, or when the senior approver said yes.",
                expr: "vars.seniorApprovalRequired === false || vars.decision2 === 'Approved'",
                why: "This makes sure nothing is paid before approval. The function itself also refuses to pay without approval, so there are two safety nets." }
            ] },
          build: [
            { t: "kv", rows: [["Rule on SeniorApproval", "Only if senior approval is required"], ["Type", "Runs sequentially"], ["Expression", "vars.seniorApprovalRequired === true"]] },
            { t: "kv", rows: [["Rule on ProcessSettlement", "Pay only if no approval needed or approved"], ["Type", "Runs sequentially"], ["Expression", "vars.seniorApprovalRequired === false || vars.decision2 === 'Approved'"]] }
          ] },
        entryStep(
          "When should Settlement start?",
          "After the person has had their say.",
          "When Review is completed.",
          { label: "Entry rule", name: "Adjuster approved the claim", type: "Selected stage completed", plain: "Start Settlement when Review has completed.", expr: null, stage: "Review",
            why: "Later, only an Approve will let a claim in here." },
          [{ t: "kv", rows: [["Name", "Adjuster approved the claim"], ["Type", "Selected stage completed"], ["Stage", "Review"]] },
           { t: "note", text: "No expression for now." }]),
        doneStep(
          "When can you say Settlement is completely fine?",
          "What proves the money has been dealt with?",
          "When the payment has been recorded.",
          { label: "Completion rule", name: "Settlement paid", type: "Required tasks completed",
            plain: "Settlement is done when the required tasks are finished and the payment status says Paid.",
            expr: "vars.settlementStatus === \"Paid\"", why: "The payment status comes back from ProcessSettlement." },
          [{ t: "kv", rows: [["Name", "Settlement paid"], ["Completes the stage when", "Required tasks completed"], ["Expression", "vars.settlementStatus === \"Paid\""]] }],
          MARK),
        leaveStep(
          "What could happen at Settlement that should stop the payment and end the claim?",
          "Think about the senior approver's buttons.",
          "One thing can pull a claim out of Settlement:",
          [{ what: "The senior approver rejects", goes: "Denied", chapter: 3 }])
      ],
      check: [
        "Settlement has three tasks. Only SeniorApproval is not required.",
        "The two task rules carry their expressions."
      ]
    },

    /* ============================ CLOSURE ============================ */
    closure: {
      title: "Closure",
      tagline: "Wrap up. Tell the customer.",
      story: [
        "The customer has been paid. Two loose ends remain. The file needs a **claim packet**: one reference that ties the evidence and the result together. And the customer needs to be **told the outcome** in words that make sense to them.",
        "Both are small and independent. When they are done the case has nothing left to do, so it closes."
      ],
      steps: [
        addStage("Closure", "Creates the claim packet and prepares the customer notification, then the case closes."),
        { title: "Job 1: close the file", kind: "Which activity?",
          q: "The first job: produce one reference that ties the claim's evidence and result together, for the file. Which activity?",
          hint: "A small, fixed piece of work. No judgement.",
          answer: { lead: "An **API workflow**, a tiny automation that creates the claim packet reference.",
            tasks: [{ act: "GenerateClaimPacket", required: true }] },
          build: [
            { t: "text", text: "Add a task to Closure." },
            { t: "kv", rows: [["Type", "API workflow"], ["Resource", "GenerateClaimPacket"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [["ClaimId", "vars.response?.ClaimId"]] }
          ] },
        { title: "Job 2: tell the customer", kind: "Which activity?",
          q: "The second job: write the outcome message for the customer, based on how the claim ended. Which activity?",
          hint: "Another small automation. It writes the text. Sending it by email comes later.",
          answer: { lead: "An **API workflow** that writes the outcome message.",
            tasks: [{ act: "CreateCustomerNotification", required: true }] },
          build: [
            { t: "text", text: "Add a second task to Closure." },
            { t: "kv", rows: [["Type", "API workflow"], ["Resource", "CreateCustomerNotification"], ["Required", "Yes"]] },
            { t: "table", head: ["Input", "Value"], rows: [
              ["ClaimId", "vars.response?.ClaimId"],
              ["CustomerName", "vars.response?.CustomerName"],
              ["SettlementStatus", "vars.settlementStatus"],
              ["SettlementAmount", "vars.settlementAmount"]
            ] },
            { t: "note", text: "Leave **FraudInvestigationResult** empty for now. Chapter 4 fills it in." }
          ] },
        { title: "Can we make it faster?", kind: "Faster?",
          q: "Does the notification need the claim packet, or the other way round? Can they run at the same time?",
          hint: "Look at their inputs.",
          answer: { lead: "Yes. They are independent, so they run **in parallel**.",
            tasks: [
              { act: "GenerateClaimPacket", required: true, rule: { name: "Start claim packet", type: SEQ } },
              { act: "CreateCustomerNotification", required: true, rule: { name: "Start customer notification", type: SEQ } }
            ] },
          build: [
            { t: "text", text: "Place the two tasks side by side, then give each its start rule:" },
            { t: "kv", rows: [["Rule on GenerateClaimPacket", "Start claim packet"], ["Rule on CreateCustomerNotification", "Start customer notification"], ["Type (both)", "Runs sequentially"]] }
          ] },
        entryStep(
          "When should Closure start?",
          "After the money has moved.",
          "When Settlement is completed.",
          { label: "Entry rule", name: "Settlement completed", type: "Selected stage completed", plain: "Start Closure when Settlement has completed.", expr: null, stage: "Settlement",
            why: "There is nothing to close until the payment is recorded." },
          [{ t: "kv", rows: [["Name", "Settlement completed"], ["Type", "Selected stage completed"], ["Stage", "Settlement"]] }]),
        doneStep(
          "When can you say Closure is done?",
          "The usual way.",
          "When both required tasks have finished.",
          { label: "Completion rule", name: "Packet and notification done", type: "Required tasks completed",
            plain: "Closure is done when both required tasks have finished.", expr: null },
          [{ t: "kv", rows: [["Name", "Packet and notification done"], ["Completes the stage when", "Required tasks completed"]] }],
          MARK),
        { title: "When does the whole case finish?", kind: "The whole case",
          q: "Stages know when they are done. How does the whole case know it is finished?",
          hint: "It is a setting of the case, not of a stage.",
          answer: { lead: "A case completion rule. The case finishes when every required stage is done.",
            rules: [{ label: "Case completion rule", name: "All required stages completed", type: "All required stages completed",
              plain: "Finish the case when every required (main road) stage is done.", expr: null,
              why: "Without it the case keeps waiting after Closure." }] },
          build: [
            { t: "text", text: "Open **Case plan properties > Completion rules** (click an empty part of the canvas) and add one rule." },
            { t: "kv", rows: [["Name", "All required stages completed"], ["Completes the case when", "All required stages are completed"]] },
            { t: "note", text: "The exact option label can differ a little between releases. Look for the nearest match." }
          ] }
      ],
      check: [
        "Closure shows two required tasks, side by side.",
        "Case plan properties has the rule **All required stages completed**.",
        "You now have five stages in a line. Next: run it."
      ]
    }
  };

  /* ---------- Chapter 1: the trigger (before any stage) ---------- */
  var TRIGGER_STEPS = [
    { title: "What starts a case?", kind: "The trigger",
      q: "Nothing happens in a case until something starts it. In the business, what event starts the handling of a claim?",
      hint: "The customer does something in the Intake App, and a record appears.",
      answer: { lead: "A new **claim record**. When the customer registers a claim, a row is created in the `MotorInsuranceClaim` table in Data Fabric. That row is the trigger: it starts the case." },
      build: [
        { t: "ol", items: [
          "In **Studio Web**, open **MotorInsuranceClaimManagement**, then the project **MyClaimsCase**.",
          "You see one circle. That is the trigger, named MotorInsuranceClaim. It is already there, and it is the only thing in your blank case.",
          "If the designer shows a note about connections, bind **Data Fabric** to your connection."
        ] },
        { t: "why", text: "A case always starts from an event. Yours is \"a claim row was created\". Everything you build hangs off this one circle." }
      ] },
    { title: "How do you find a case later?", kind: "The case ID",
      q: "A thousand cases will be running. What should identify each one, so that anyone can find the case for a claim?",
      hint: "Something unique that the customer and the staff already use.",
      answer: { lead: "The **claim number**. One claim, one case, and a duplicate claim number cannot start two cases." },
      build: [
        { t: "ol", items: [
          "Click an empty part of the canvas to open **Case plan properties**.",
          "Set **Case ID** to **External key** with this value:"
        ] },
        { t: "code", text: "vars.response?.ClaimId" }
      ] }
  ];

  return {
    TYPES: TYPES, ACTIVITIES: ACTIVITIES, STAGES: STAGES, CHAPTERS: CHAPTERS, STAGE_PAGES: STAGE_PAGES, TRIGGER_STEPS: TRIGGER_STEPS,
    ORDER: ["home", "scenario", "setup", "c1", "intake", "assessment", "review", "settlement", "closure", "deploy"]
  };
})();
