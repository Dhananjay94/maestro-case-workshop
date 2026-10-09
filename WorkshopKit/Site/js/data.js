/* All site content. Facts come from WorkshopKit/CASE_FLOW_PLAN.md and Participant_Build_Guide.md.
   Text supports: **bold**, `code`, [label](#/route). */
window.DATA = (function () {

  /* ---------- Activities, named exactly as in the Studio Web task picker ---------- */
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

  /* ---------- Stages ---------- */
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
    { id: "c1", no: 1, title: "The happy path", sub: "Five stages in a line, then deploy", open: true,
      adds: "Intake, Assessment, Review, Settlement, Closure" },
    { id: "c2", no: 2, title: "Missing documents", sub: "The Pending Customer stage", open: false },
    { id: "c3", no: 3, title: "Denied", sub: "Three ways to a no", open: false },
    { id: "c4", no: 4, title: "Fraud investigation", sub: "Cleared or confirmed", open: false },
    { id: "c5", no: 5, title: "The complete case", sub: "Record updates, emails, time limits", open: false }
  ];

  /* ---------- Stage pages (Chapter 1) ---------- */
  var T = { // task rule + type shortcuts
    seq: "Runs sequentially"
  };

  var STAGE_PAGES = {

    intake: {
      title: "Intake",
      tagline: "Read the paperwork. Check the cover.",
      story: [
        "Rahul Sharma was hit from behind at a traffic light. That evening he opens the Intake App, types his policy number and the claim amount, and uploads seven documents: the claim form, police report, photos, repair estimate, licence, registration and policy copy.",
        "In the old world a clerk opens every PDF, then opens a spreadsheet to see whether Rahul's policy is even live. That takes days, and nobody can say where his claim is.",
        "In your case, the moment the claim lands the case starts. The first stage has to find out two things before anyone else spends a minute on it: **what do the documents say**, and **is Rahul actually covered**."
      ],
      think: [
        { id: "tasks", kind: "Activities",
          q: "Two questions must be answered before anyone else touches this claim. Which two workers answer them? And can they work at the same time?",
          hint: "One of them reads PDFs. The other looks at the policy list. Neither needs the other's answer.",
          answer: {
            lead: "Two workers, working **in parallel**, because neither needs the other's result. Both are **required**, so the stage cannot finish without them.",
            tasks: [
              { act: "ClaimDocumentIntelligence", required: true, rule: { name: "Start document analysis", type: T.seq } },
              { act: "ValidatePolicy", required: true, rule: { name: "Start policy validation", type: T.seq } }
            ]
          } },
        { id: "entry", kind: "Way in",
          q: "This is the first stage of the case. What makes it start?",
          hint: "Nothing comes before it.",
          answer: {
            lead: "It starts when the case itself starts.",
            rules: [
              { label: "Entry rule", name: "Case started", type: "Case entered",
                plain: "Start this stage the moment the case starts.", expr: null,
                why: "Intake is the first stage. There is no earlier stage to wait for." }
            ]
          } },
        { id: "exit", kind: "Way out",
          q: "So far there is only Rahul, and everything goes right. When is Intake finished?",
          hint: "Think about the tasks. What has to be true for the stage to be done?",
          answer: {
            lead: "When both required tasks have finished. Nothing more, for now.",
            rules: [
              { label: "Completion rule", name: "Documents analysed and policy checked", type: "Required tasks completed",
                plain: "Intake is done when both required tasks have finished.", expr: null,
                why: "Keep it simple on the happy path. In later chapters this exit learns to say what a good result looks like, and that is when missing documents and invalid policies get their own paths." }
            ],
            note: "Tick **Marks stage complete** on this rule, so the case moves on to the next stage."
          } }
      ],
      build: [
        { title: "Add the stage", blocks: [
          { t: "kv", rows: [["Name", "Intake"], ["Description", "Reads the claim documents with an AI agent and checks the policy is valid."]] },
          { t: "why", text: "This stage answers two questions that need no human: what do the documents say, and is the policy valid?" }
        ] },
        { title: "Add task 1: ClaimDocumentIntelligence", blocks: [
          { t: "kv", rows: [["Type", "Agent"], ["Resource", "ClaimDocumentIntelligence"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["ClaimId", "vars.response?.ClaimId"],
            ["DocumentReferences", "vars.response?.DocumentReferences"]
          ] },
          { t: "kv", rows: [["Task rule name", "Start document analysis"], ["Task rule type", "Runs sequentially"]] },
          { t: "note", text: "Keep the default output variable names. They are the `camelCase` versions of the output names, for example `documentIngestionStatus`." }
        ] },
        { title: "Add task 2: ValidatePolicy", blocks: [
          { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "ValidatePolicy"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["PolicyNumber", "vars.response?.PolicyNumber"],
            ["VehicleRegistration", "vars.response?.VehicleRegistration"],
            ["IncidentDate", "vars.response?.IncidentDate"]
          ] },
          { t: "kv", rows: [["Task rule name", "Start policy validation"], ["Task rule type", "Runs sequentially"]] },
          { t: "note", text: "Leave the optional input **DataFolder** empty. The workers find the data themselves." },
          { t: "why", text: "Running the two together saves time, because neither needs the other's answer." }
        ] },
        { title: "Add the entry rule", blocks: [
          { t: "kv", rows: [["Name", "Case started"], ["Type", "Case entered"]] }
        ] },
        { title: "Add the completion rule", blocks: [
          { t: "kv", rows: [["Name", "Documents analysed and policy checked"], ["Completes the stage when", "Required tasks completed"]] },
          { t: "note", text: "No expression for now." }
        ] }
      ],
      check: [
        "Intake shows two tasks, both marked as required (a `*`).",
        "Intake has one entry rule (Case started) and one completion rule."
      ]
    },

    assessment: {
      title: "Assessment",
      tagline: "Judge the risk. Size the damage.",
      story: [
        "Rahul's papers have been read and his policy is confirmed. Before a person looks at the claim, the insurer wants two more answers.",
        "**Does anything look suspicious?** The amount, the history, the way the documents fit together. An AI agent can weigh that up and say why it feels the way it does. **How big is the loss?** The repair estimate is already in the documents, so this is a straightforward calculation.",
        "Both answers will be put in front of the adjuster in the next stage, so that the human decides with full information."
      ],
      think: [
        { id: "tasks", kind: "Activities",
          q: "What two things does the insurer want to know about the claim before a person looks at it?",
          hint: "One protects the insurer from paying a bad claim. The other puts a number on the loss.",
          answer: {
            lead: "A fraud score and a damage estimate. They run in parallel and both are required.",
            tasks: [
              { act: "FraudRiskAssessment", required: true, rule: { name: "Start fraud risk assessment", type: T.seq } },
              { act: "AssessDamage", required: true, rule: { name: "Start damage assessment", type: T.seq } }
            ]
          } },
        { id: "entry", kind: "Way in",
          q: "What must have finished before Assessment can start? Why can't it simply run beside Intake?",
          hint: "Look at what these two workers need as input.",
          answer: {
            lead: "Intake must be completed first. These workers use what Intake produced: the repair estimate and any conflicts between documents.",
            rules: [
              { label: "Entry rule", name: "Intake completed", type: "Selected stage completed",
                plain: "Start Assessment when Intake has completed.", expr: null, stage: "Intake",
                why: "Assessment needs `extractedRepairEstimate` and `documentInconsistencies` from Intake. That is why it comes after Intake and not beside it." }
            ]
          } },
        { id: "exit", kind: "Way out",
          q: "On the happy path, when is Assessment finished?",
          hint: "The same idea as Intake.",
          answer: {
            lead: "When both required tasks have finished.",
            rules: [
              { label: "Completion rule", name: "Fraud score and damage estimate ready", type: "Required tasks completed",
                plain: "Assessment is done when both required tasks have finished.", expr: null,
                why: "A high fraud score will later send the claim to an investigator. That detour is added in Chapter 4, not now." }
            ],
            note: "Tick **Marks stage complete** on this rule."
          } }
      ],
      build: [
        { title: "Add the stage", blocks: [
          { t: "kv", rows: [["Name", "Assessment"], ["Description", "Scores the fraud risk with an AI agent and works out the damage estimate from the repair estimate. Both run together."]] }
        ] },
        { title: "Add task 1: FraudRiskAssessment", blocks: [
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
          { t: "kv", rows: [["Task rule name", "Start fraud risk assessment"], ["Task rule type", "Runs sequentially"]] }
        ] },
        { title: "Add task 2: AssessDamage", blocks: [
          { t: "kv", rows: [["Type", "API workflow"], ["Resource", "AssessDamage"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [["ExtractedRepairEstimate", "vars.extractedRepairEstimate"]] },
          { t: "kv", rows: [["Task rule name", "Start damage assessment"], ["Task rule type", "Runs sequentially"]] }
        ] },
        { title: "Add the entry rule", blocks: [
          { t: "kv", rows: [["Name", "Intake completed"], ["Type", "Selected stage completed"], ["Stage", "Intake"]] }
        ] },
        { title: "Add the completion rule", blocks: [
          { t: "kv", rows: [["Name", "Fraud score and damage estimate ready"], ["Completes the stage when", "Required tasks completed"]] },
          { t: "note", text: "No expression for now." }
        ] }
      ],
      check: [
        "Assessment shows two required tasks.",
        "Its entry rule points at Intake."
      ]
    },

    review: {
      title: "Review",
      tagline: "A person owns the decision.",
      story: [
        "Rahul's claim now has a policy result, a damage estimate and a low fraud score. Money is about to be decided, so a person must own the decision: the claims adjuster.",
        "The adjuster does not open PDFs or spreadsheets. They get one screen in Action Center with everything the machines found, and three buttons: **Approve**, **Reject**, **RequestInformation**.",
        "On the happy path Rahul's claim is clean, so the adjuster will press Approve. You will play the adjuster yourself."
      ],
      think: [
        { id: "tasks", kind: "Activities",
          q: "Who or what makes the decision, and how does the case reach them?",
          hint: "Not an agent. A person, in Action Center.",
          answer: {
            lead: "One **human task**. The case creates a task in Action Center and waits until the person submits it.",
            tasks: [
              { act: "AdjusterReview", required: true, rule: { name: "Start adjuster review", type: T.seq } }
            ]
          } },
        { id: "entry", kind: "Way in",
          q: "When does the adjuster get the claim?",
          hint: "After the machines have finished their part.",
          answer: {
            lead: "When Assessment is completed.",
            rules: [
              { label: "Entry rule", name: "Assessment completed", type: "Selected stage completed",
                plain: "Start Review when Assessment has completed.", expr: null, stage: "Assessment",
                why: "The adjuster needs the fraud score and damage estimate on their screen." }
            ]
          } },
        { id: "exit", kind: "Way out",
          q: "When is Review finished?",
          hint: "Which task has to be done?",
          answer: {
            lead: "When the adjuster has submitted their decision.",
            rules: [
              { label: "Completion rule", name: "Adjuster decision recorded", type: "Required tasks completed",
                plain: "Review is done when the adjuster has submitted the task.", expr: null,
                why: "For now, any button finishes Review. In later chapters only Approve will complete it, and Reject and RequestInformation will get their own paths." }
            ],
            note: "Tick **Marks stage complete** on this rule."
          } }
      ],
      build: [
        { title: "Add the stage", blocks: [
          { t: "kv", rows: [["Name", "Review"], ["Description", "A claims adjuster reviews the documents, policy result and fraud assessment, then approves, rejects or asks the customer for more information."]] }
        ] },
        { title: "Add the task: AdjusterReview", blocks: [
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
        { title: "Add the entry rule", blocks: [
          { t: "kv", rows: [["Name", "Assessment completed"], ["Type", "Selected stage completed"], ["Stage", "Assessment"]] }
        ] },
        { title: "Add the completion rule", blocks: [
          { t: "kv", rows: [["Name", "Adjuster decision recorded"], ["Completes the stage when", "Required tasks completed"]] },
          { t: "note", text: "No expression for now." }
        ] }
      ],
      check: [
        "Review has one human task, titled **Review the claim and decide**, assigned to you.",
        "All eleven inputs are filled."
      ]
    },

    settlement: {
      title: "Settlement",
      tagline: "Work out the money. Pay it once.",
      story: [
        "The adjuster approved. Now the money. The payable amount is the smallest of three numbers (the claim amount, the damage estimate and the policy's cover limit), minus the deductible, never below zero. For Rahul that comes to **162,400**.",
        "Big payouts get a second pair of eyes. Above **175,000**, a senior approver must sign off before anything is paid. Rahul's is below that, so for him the approval is skipped.",
        "Then the payment is recorded. Once. A second attempt must never pay twice."
      ],
      think: [
        { id: "tasks", kind: "Activities",
          q: "Work out the money, maybe get a second opinion, then pay. Which three workers, in which order? Which one does not always run?",
          hint: "The middle one is only needed for large amounts.",
          answer: {
            lead: "Three tasks in order. **SeniorApproval is not required**, because for most claims it never runs. If it were required and skipped, the stage would wait forever.",
            tasks: [
              { act: "CalculateSettlement", required: true, rule: { name: "Start settlement calculation", type: T.seq } },
              { act: "SeniorApproval", required: false, rule: { name: "Only if senior approval is required", type: T.seq, expr: "vars.seniorApprovalRequired === true" } },
              { act: "ProcessSettlement", required: true, rule: { name: "Pay only if no approval needed or approved", type: T.seq, expr: "vars.seniorApprovalRequired === false || vars.decision2 === 'Approved'" } }
            ]
          } },
        { id: "gates", kind: "Task rules",
          q: "Two of those tasks should not simply start with the stage. What does each one wait for?",
          hint: "One waits for a need. The other waits for permission.",
          answer: {
            lead: "**SeniorApproval** runs only when the calculation says approval is needed. **ProcessSettlement** pays only if no approval was needed, or it was granted. Nothing is paid before approval.",
            rules: [
              { label: "Task rule on SeniorApproval", name: "Only if senior approval is required", type: "Runs sequentially",
                plain: "Run the senior approval only when the settlement is large enough to need it.",
                expr: "vars.seniorApprovalRequired === true",
                why: "This decides whether an approval is needed." },
              { label: "Task rule on ProcessSettlement", name: "Pay only if no approval needed or approved", type: "Runs sequentially",
                plain: "Pay when no approval was needed, or when the senior approver said yes.",
                expr: "vars.seniorApprovalRequired === false || vars.decision2 === 'Approved'",
                why: "This makes sure nothing is paid before approval. The function itself also refuses to pay without approval, so there are two safety nets." }
            ]
          } },
        { id: "entry", kind: "Way in",
          q: "When does Settlement start?",
          hint: "After the person has had their say.",
          answer: {
            lead: "When Review is completed.",
            rules: [
              { label: "Entry rule", name: "Adjuster approved the claim", type: "Selected stage completed",
                plain: "Start Settlement when Review has completed.", expr: null, stage: "Review",
                why: "Later, only an Approve will let a claim in here. Reject and RequestInformation will take other roads." }
            ]
          } },
        { id: "exit", kind: "Way out",
          q: "When is Settlement finished?",
          hint: "What proves the money has been dealt with?",
          answer: {
            lead: "When the payment has been recorded.",
            rules: [
              { label: "Completion rule", name: "Settlement paid", type: "Required tasks completed",
                plain: "Settlement is done when the required tasks are finished and the payment status says Paid.",
                expr: "vars.settlementStatus === \"Paid\"",
                why: "The payment status comes back from ProcessSettlement." }
            ],
            note: "Tick **Marks stage complete** on this rule."
          } }
      ],
      build: [
        { title: "Add the stage", blocks: [
          { t: "kv", rows: [["Name", "Settlement"], ["Description", "Calculates the payable amount (loss minus deductible, capped at cover). Above the approval threshold a senior approver must approve before payment is recorded."]] }
        ] },
        { title: "Add task 1: CalculateSettlement", blocks: [
          { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "CalculateSettlement"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["PolicyNumber", "vars.response?.PolicyNumber"],
            ["ClaimAmount", "vars.response?.ClaimAmount"],
            ["DamageEstimate", "vars.damageEstimate"]
          ] },
          { t: "kv", rows: [["Task rule name", "Start settlement calculation"], ["Task rule type", "Runs sequentially"]] }
        ] },
        { title: "Add task 2: SeniorApproval", blocks: [
          { t: "kv", rows: [["Type", "Action (human task)"], ["App", "SeniorApproval"], ["Required", "No"], ["Task title", "Approve a settlement above the threshold"], ["Assign to", "A specific user: yourself"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["ClaimId", "vars.response?.ClaimId"],
            ["SettlementAmount", "vars.settlementAmount"],
            ["DamageEstimate", "vars.damageEstimate"]
          ] },
          { t: "kv", rows: [["Task rule name", "Only if senior approval is required"], ["Task rule type", "Runs sequentially"], ["Expression", "vars.seniorApprovalRequired === true"]] },
          { t: "why", text: "SeniorApproval is not required: for Rahul (162,400) it never runs. If it were required and skipped, the stage would wait forever." }
        ] },
        { title: "Add task 3: ProcessSettlement", blocks: [
          { t: "kv", rows: [["Type", "Function (process)"], ["Resource", "ProcessSettlement"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["ClaimId", "vars.response?.ClaimId"],
            ["CustomerName", "vars.response?.CustomerName"],
            ["PolicyNumber", "vars.response?.PolicyNumber"],
            ["SettlementAmount", "vars.settlementAmount"],
            ["SeniorApprovalRequired", "vars.seniorApprovalRequired"],
            ["SeniorApprovalDecision", "vars.decision2"]
          ] },
          { t: "kv", rows: [["Task rule name", "Pay only if no approval needed or approved"], ["Task rule type", "Runs sequentially"], ["Expression", "vars.seniorApprovalRequired === false || vars.decision2 === 'Approved'"]] }
        ] },
        { title: "Add the entry rule", blocks: [
          { t: "kv", rows: [["Name", "Adjuster approved the claim"], ["Type", "Selected stage completed"], ["Stage", "Review"]] },
          { t: "note", text: "No expression for now." }
        ] },
        { title: "Add the completion rule", blocks: [
          { t: "kv", rows: [["Name", "Settlement paid"], ["Completes the stage when", "Required tasks completed"], ["Expression", "vars.settlementStatus === \"Paid\""]] }
        ] }
      ],
      check: [
        "Settlement has three tasks. Only SeniorApproval is not required.",
        "The two task rules carry their expressions."
      ]
    },

    closure: {
      title: "Closure",
      tagline: "Wrap up. Tell the customer.",
      story: [
        "Rahul has been paid. Two loose ends remain. The file needs a **claim packet**: one reference that ties the evidence and the result together. And Rahul needs to be **told the outcome** in words that make sense to a customer.",
        "Both are small and independent. When they are done the case has nothing left to do, so it closes."
      ],
      think: [
        { id: "tasks", kind: "Activities",
          q: "Two small jobs close the claim. What are they, and do they depend on each other?",
          hint: "One is for the file. The other is for the customer.",
          answer: {
            lead: "A claim packet and a customer notification. They are independent, so they run in parallel. Both are required.",
            tasks: [
              { act: "GenerateClaimPacket", required: true, rule: { name: "Start claim packet", type: T.seq } },
              { act: "CreateCustomerNotification", required: true, rule: { name: "Start customer notification", type: T.seq } }
            ]
          } },
        { id: "entry", kind: "Way in",
          q: "When does Closure start?",
          hint: "After the money has moved.",
          answer: {
            lead: "When Settlement is completed.",
            rules: [
              { label: "Entry rule", name: "Settlement completed", type: "Selected stage completed",
                plain: "Start Closure when Settlement has completed.", expr: null, stage: "Settlement",
                why: "There is nothing to close until the payment is recorded." }
            ]
          } },
        { id: "exit", kind: "Way out",
          q: "When is Closure finished?",
          hint: "The usual way.",
          answer: {
            lead: "When both required tasks have finished.",
            rules: [
              { label: "Completion rule", name: "Packet and notification done", type: "Required tasks completed",
                plain: "Closure is done when both required tasks have finished.", expr: null }
            ],
            note: "Tick **Marks stage complete** on this rule."
          } },
        { id: "case", kind: "The whole case",
          q: "Stages know when they are done. How does the whole case know it is finished?",
          hint: "It is a setting of the case, not of a stage.",
          answer: {
            lead: "A case completion rule. The case finishes when every required stage is done.",
            rules: [
              { label: "Case completion rule", name: "All required stages completed", type: "All required stages completed",
                plain: "Finish the case when every required (main road) stage is done.", expr: null,
                why: "Without it the case would keep waiting after Closure. You set it in **Case plan properties > Completion rules**." }
            ]
          } }
      ],
      build: [
        { title: "Add the stage", blocks: [
          { t: "kv", rows: [["Name", "Closure"], ["Description", "Creates the claim packet and prepares the customer notification, then the case closes."]] }
        ] },
        { title: "Add task 1: GenerateClaimPacket", blocks: [
          { t: "kv", rows: [["Type", "API workflow"], ["Resource", "GenerateClaimPacket"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [["ClaimId", "vars.response?.ClaimId"]] },
          { t: "kv", rows: [["Task rule name", "Start claim packet"], ["Task rule type", "Runs sequentially"]] }
        ] },
        { title: "Add task 2: CreateCustomerNotification", blocks: [
          { t: "kv", rows: [["Type", "API workflow"], ["Resource", "CreateCustomerNotification"], ["Required", "Yes"]] },
          { t: "table", head: ["Input", "Value"], rows: [
            ["ClaimId", "vars.response?.ClaimId"],
            ["CustomerName", "vars.response?.CustomerName"],
            ["SettlementStatus", "vars.settlementStatus"],
            ["SettlementAmount", "vars.settlementAmount"]
          ] },
          { t: "note", text: "Leave **FraudInvestigationResult** empty for now. Chapter 4 fills it in." },
          { t: "kv", rows: [["Task rule name", "Start customer notification"], ["Task rule type", "Runs sequentially"]] }
        ] },
        { title: "Add the entry rule", blocks: [
          { t: "kv", rows: [["Name", "Settlement completed"], ["Type", "Selected stage completed"], ["Stage", "Settlement"]] }
        ] },
        { title: "Add the completion rule", blocks: [
          { t: "kv", rows: [["Name", "Packet and notification done"], ["Completes the stage when", "Required tasks completed"]] }
        ] },
        { title: "Tell the case when it is finished", blocks: [
          { t: "text", text: "Open **Case plan properties > Completion rules** (click an empty part of the canvas). Add one rule." },
          { t: "kv", rows: [["Name", "All required stages completed"], ["Completes the case when", "All required stages are completed"]] },
          { t: "note", text: "The exact option label can differ a little between releases. Look for the nearest match." }
        ] }
      ],
      check: [
        "Closure shows two required tasks.",
        "Case plan properties has the rule **All required stages completed**.",
        "You now have five stages in a line. Next: run it."
      ]
    }
  };

  return {
    TYPES: TYPES, ACTIVITIES: ACTIVITIES, STAGES: STAGES, CHAPTERS: CHAPTERS, STAGE_PAGES: STAGE_PAGES,
    ORDER: ["home", "scenario", "setup", "c1", "intake", "assessment", "review", "settlement", "closure", "deploy"]
  };
})();
