# Build the Motor Claims Case yourself

- **What you will build:** a Maestro case that runs a motor insurance claim from the moment a customer registers it to payment (or denial), using building blocks that are already made for you.
- **What you need to know first:** nothing about Maestro. Everything is explained when you need it.
- **How to use this guide:** read sections 1 to 5 once (about 25 minutes). Then follow section 6 in order. Sections 7 to 12 are for looking things up.

> Boxes marked **Why** explain the reason behind a step. Boxes marked **Check** tell you how to know it worked. Boxes marked **Stuck?** tell you which example case to open to catch up.

| Part | You build | Time (first time) | Example case |
|---|---|---|---|
| 6A | Case settings | 10 min | (nothing yet) |
| 6B | **Happy path**: 5 stages in a line | 90 min | `1_HappyPath` |
| 6C | Pending Customer (documents missing) | 45 min | `2_PendingCustomer` |
| 6D | Denied (three ways to a "no") | 35 min | `3_Denied` |
| 6E | Fraud Investigation | 30 min | `4_FraudInvestigation` |
| 6F | Keep the claim record up to date (optional) | 40 min | `5_Complete` |
| 6G | Emails to the customer (optional) | 20 min | `5_Complete` |
| 6H | Time limits, called SLAs (optional) | 20 min | `5_Complete` |

A half-day session covers 6A to 6D comfortably. Parts 6E to 6H are for the faster pace or for homework. Open the matching example case to compare with yours, or to catch up.

---

## Contents
1. The business scenario
2. What is already built for you
3. Import and set up
4. The business rules (your design brief)
5. Five ideas you need before you start
6. Build it, step by step (6A to 6I)
7. Appendix A: variable dictionary
8. Appendix B: every rule on one page
9. Appendix C: claim status values
10. Appendix D: test matrix
11. Appendix E: troubleshooting
12. Appendix F: glossary

---

## 1. The business scenario

**The company.** A motor insurer settles accident claims. Today a clerk reads every document by hand, checks the policy in a spreadsheet, emails people, and chases approvals. Claims take days and nobody can say where a claim is.

**The goal.** One digital process that:
- reads the documents and checks the policy by itself,
- asks a person only when a human decision is really needed,
- never pays more than the policy allows, and never pays without the right approval,
- tells the customer what is happening, and
- always shows the current status of every claim.

**The people**

| Who | What they do in the process |
|---|---|
| **Customer** | Registers the claim and uploads documents in the Intake App. Receives emails. Adds a missing document later |
| **Claims adjuster** | Reviews each claim and decides: approve, reject, or ask the customer for more information |
| **Senior approver** | Approves large settlements before they are paid |
| **Fraud investigator** | Looks at claims the system flags as high risk |
| **Operations** | Watches the claim record and the time limits |

**The three customers you will test with**

| Customer | Story | What should happen |
|---|---|---|
| **Rahul Sharma** | Rear-ended at a traffic light. All 7 documents, clean history, claim 185,000 | Straight through. Paid 162,400. No senior approval |
| **Priya Nair** | Side collision. She forgot the repair estimate | Case pauses, emails her, waits for the estimate, then continues |
| **Arjun Mehta** | Head-on collision, 240,000. The documents contradict each other and he has 3 earlier claims | Flagged as high fraud risk. An investigator decides. If cleared, the payout is 230,000 and needs a senior approver |

**The journey of a claim**

```
 Customer registers claim (Intake App)
              |
              v
   INTAKE ----> ASSESSMENT ----> REVIEW ----> SETTLEMENT ----> CLOSURE      (the main road)
     |   \          |              |  \             |
     |    \         |              |   \            |
     |     \        v              |    \           v
     |      \   FRAUD INVESTIGATION|     \       DENIED  (ends the case)
     |       \      |  Cleared: back to Assessment
     v        v     |  Confirmed: Denied
  DENIED   PENDING CUSTOMER  <------+   (customer must send something; then back to where it left)
```

**Two kinds of stage.** The five on the main road are *primary* stages: a claim normally passes through all of them. Pending Customer, Fraud Investigation and Denied are *secondary* stages: a claim only enters them when something unusual happens (an exception).

---

## 2. What is already built for you

You build the **case**: the conductor that decides what happens, in which order, under which rules. Everything else is a **worker** that already exists and is already deployed. You will only *call* the workers.

### 2.1 Data and storage

| Item | What it is | Notes |
|---|---|---|
| **MotorInsuranceClaim** (Data Fabric entity) | One row per claim. The case is built around it | Your case starts when a row is created |
| **PolicyMaster** | One row per policy: status, vehicle, dates, coverage limit, customer email | Seeded by the setup |
| **ClaimHistory** | Earlier claims per policy | Seeded by the setup |
| **SettlementRegister** | The payment ledger, one row per paid claim | Written by ProcessSettlement |
| **Bucket** `MotorInsuranceClaims-Documents` | The uploaded PDFs | The claim row stores only file names |
| **Assets** `ClaimsDeductible` = 10,000 and `ClaimsSeniorApprovalThreshold` = 175,000 | Business numbers that can change | Edited in Orchestrator, not in code |

### 2.2 Workers you will call (the "operations" available)

**Agents (AI that reads and judges)**

| Name | Input | Output (variable you get) | Used in |
|---|---|---|---|
| **ClaimDocumentIntelligence** | ClaimId, DocumentReferences | `documentIngestionStatus` (Complete / Inconsistent / Incomplete), `documentsComplete`, `missingDocuments`, `documentInconsistencies`, `extractedCustomerName`, `extractedPolicyNumber`, `extractedVehicleRegistration`, `extractedIncidentDate`, `extractedDocumentTypes`, `extractedRepairEstimate` | Intake |
| **FraudRiskAssessment** | ClaimId, PolicyNumber, ClaimAmount, IncidentDate, IncidentDescription, ExtractedRepairEstimate, DocumentInconsistencies | `fraudScore` (0 to 100), `riskLevel` (Low under 30, Medium 30 to 69, High 70 and over), `fraudFlag` (true only for High), `fraudReasons` | Assessment |

**Functions (plain code, always the same answer)**

| Name | Input | Output | Used in |
|---|---|---|---|
| **ValidatePolicy** | PolicyNumber, VehicleRegistration, IncidentDate | `policyValid`, `policyValidationReason`, `customerEmail` | Intake |
| **CalculateSettlement** | PolicyNumber, ClaimAmount, DamageEstimate | `settlementAmount`, `seniorApprovalRequired` | Settlement |
| **ProcessSettlement** | ClaimId, CustomerName, PolicyNumber, SettlementAmount, SeniorApprovalRequired, SeniorApprovalDecision | `settlementStatus`, `paymentReference`, `settlementDate` | Settlement |
| **UpdateClaim** | ClaimId, Stage, ClaimStatus, plus the fields of that stage | `Updated` | Part 6F |

**API workflows (tiny calculations)**

| Name | Input | Output | Used in |
|---|---|---|---|
| **AssessDamage** | ExtractedRepairEstimate | `damageEstimate` | Assessment |
| **GenerateClaimPacket** | ClaimId | `claimPacketReference` | Closure |
| **CreateCustomerNotification** | ClaimId, CustomerName, SettlementStatus, FraudInvestigationResult, SettlementAmount | `notificationStatus`, `claimOutcome`, `notificationText` | Closure, Denied |

**Human task screens (appear in Action Center)**

| Name | The person sees | Buttons | Returns |
|---|---|---|---|
| **AdjusterReview** | Claim, amounts, policy result, document status and conflicts, fraud score and reasons | Approve, Reject, RequestInformation | `decision`, `comments` (comment is required for Reject and RequestInformation) |
| **SeniorApproval** | Claim, settlement amount, damage estimate | Approved, Rejected | `decision2`, `comments2` |
| **FraudInvestigation** | Claim, fraud score and reasons, document conflicts | Cleared, Confirmed | `fraudResult`, `comments3` |

**Connectors (Integration Service)**

| Connector | Used for |
|---|---|
| **UiPath Data Fabric** | Starting the case when a claim row is created, and waiting for the customer's document (Part 6C) |
| **Gmail** | Sending real emails to the customer (Parts 6C and 6G) |

> **Why workers and a conductor?** Each worker does one thing and does it the same way every time, and each can be tested alone. The case only decides *when* to call a worker and *what to do with the answer*. That is the whole skill of this workshop.

> **Not used:** the app **RequestCustomerInformation** also exists. It is the manual alternative to Part 6C (a person confirms that the customer was asked). You will use an automatic email and an event instead.

---

## 3. Set up (about 15 minutes)

You do not install anything on your computer. One small automation, **Setup**, prepares your UiPath account and puts the whole workshop solution into Studio Web for you.

### 3.1 What you need
- A UiPath Community account.
- The file `MotorClaimsWorkshop_Setup.uis` (it is in the workshop folder, inside `Starter_Solution`).
- Two connections, which you create once under **Integration Service > Connections > Add connection**: **Gmail** and **UiPath Data Fabric**. You need them in Part 6C and when you deploy.

### 3.2 Import the Setup solution
1. Sign in to UiPath and open **Studio Web**.
2. Use **Import** on the Studio Web home page (next to **Create New**; the exact label can differ). Choose `MotorClaimsWorkshop_Setup.uis`.
3. Open the solution **MotorClaimsWorkshop_Setup**. It has one project, **SetupWorkshop**.

### 3.3 Run Setup
1. In **SetupWorkshop**, press **Debug**. A small form opens.
2. Set **Action** to `InstallWorkshop`. Leave every other field empty.
3. Press run and **wait for the result**. It takes a minute or two.
4. The last line says **Done** and gives you the address of your **Intake App**. Write it down. It also names your environment, normally `ClaimsSolution`.

> **Check:** the result ends with `Done. Intake App: https://<your-org>.uipath.host/claims-<your-org>` and a line saying Debug was linked to the deployed resources.

> **If the screen looks stuck:** Studio Web sometimes shows only the first lines. Open a second Debug of **SetupWorkshop** with **Action** = `Status`. It takes a few seconds and tells you how far Setup got, ending with **FINISHED** or **NOT FINISHED**.

> **If it says the name cannot be used:** a leftover from an earlier try is blocking it. Run Setup again with **DeploymentName** set to a new name, for example `ClaimsSolutionNew`. Use that name wherever this guide says `ClaimsSolution`.

### 3.4 What Setup just created for you

| What | Where |
|---|---|
| A sign-in client for the approval screens and the Intake App | Your organization |
| The environment: the claim tables, the document bucket, the two number assets, every worker, the approval screens and the **Intake App** | Orchestrator folder `Shared/ClaimsSolution` |
| Demo policies and claim history, with `CustomerEmail` set to **your own address** | The `PolicyMaster` and `ClaimHistory` tables |
| The workshop solution **MotorInsuranceClaimManagement**, linked to that environment | Your Studio Web |

No claims exist yet. You create them when you want to test.

### 3.5 Your solution in Studio Web
Open **MotorInsuranceClaimManagement** in Studio Web. It is one solution that holds everything:

| Project | What it is |
|---|---|
| **MyClaimsCase** | Your case. It is **empty**: one circle, the trigger, and nothing else. **You build here.** |
| `1_HappyPath` to `5_Complete` | **Example cases** at five stages, to compare with or to jump in from |
| The workers (`ValidatePolicy`, `AssessDamage`, `FraudRiskAssessment` and the others) | Already built. Your case calls them |
| The approval screens and the **Intake App** | Already built |

1. Open the project **MyClaimsCase**. You see one circle (the trigger, named MotorInsuranceClaim). That is your blank case.
2. If the designer shows a note about connections, bind **UiPath Data Fabric** to your connection, and **Gmail** when you reach Part 6C.
3. Press **Debug** to test. Because Setup linked the solution to your environment, Debug uses the workers already deployed and does not create its own.

> **Why a trigger already exists:** a case always starts from an event. Yours is "a claim row was created". Everything you build hangs off this one circle.

> **Stuck?** Open the matching example case (the table at the top of this guide says which) and compare. If you are far behind, you can keep building straight in that example case.

### 3.6 Test your case with a claim
Debug starts a case from a claim, so you need one.
1. Open **MotorClaimsWorkshop_Setup > SetupWorkshop** and press **Debug** with **Action** = `RegisterClaim` and **Customer** = `Rahul` (or `Priya` or `Arjun`). It uploads that customer's PDFs and adds one claim: CLM-1001 for Rahul, CLM-1002 for Priya, CLM-1003 for Arjun.
2. In your solution, press **Debug** on your case and pick that claim.
3. Human steps appear in **Action Center > Tasks**. They are assigned to you, so you play every role. Customer emails arrive in your inbox, and the claim row is in **Data Fabric > MotorInsuranceClaim**.

### 3.7 Deploy it and see it in Maestro
When your case works in Debug:
1. **Remove the example cases.** In Studio Web, open the three-dot menu of each of `1_HappyPath`, `2_PendingCustomer`, `3_Denied`, `4_FraudInvestigation` and `5_Complete` and remove it from the solution. Keep **MyClaimsCase**, the workers, the approval screens and the Intake App. Otherwise every claim would start up to six cases.
2. Press **Publish** on **MotorInsuranceClaimManagement**. This makes a new version of the solution.
3. In **Orchestrator > Solutions > Deployments**, open your environment (`ClaimsSolution`), choose the three-dot menu, and **Upgrade** to the new version. Your case is added to the same folder as the Intake App, tables and workers. Nothing is duplicated.
4. Choose **Set up activation**, bind your **Gmail** and **UiPath Data Fabric** connections, then **Activate**.
5. Open your **Intake App** address, sign in, register a claim with its documents, and open **Maestro > Case management**. Your case runs.

> **Why activation is needed:** the case starts from a claim row, and that start event runs through your Data Fabric connection. Until you bind it and activate, the case does not start.

> **Note:** whatever cases are still in the solution when you Publish get deployed, and each starts on every new claim. That is why step 1 removes the examples. To try a finished example instead of your own, keep that one and remove the rest.

### 3.8 Start over
If something goes wrong and you want a clean start:
1. In **Studio Web**, delete the solution **MotorInsuranceClaimManagement**.
2. In **Orchestrator > Solutions > Deployments**, open `ClaimsSolution`, choose the three-dot menu, and **Uninstall**. Wait until it shows successful. **Do not delete the folder by hand**: the name stays blocked.
3. Run Setup again (3.3).

If you had already used **Upgrade**, finish **Set up activation** and **Activate** first. A deployment with unactivated cases cannot be uninstalled.

If a reset is still blocked, run Setup with **DeploymentName** set to a new name.

---

## 4. The business rules (your design brief)

These are the rules the business gave you. Your job is to turn each one into something the case does. **Before you read section 6, try the exercise below.**

| ID | The rule | Why it exists |
|---|---|---|
| BR-01 | A case starts when a customer registers a claim, and the claim number identifies the case | One claim, one case, traceable |
| BR-02 | The documents are read by AI. The result is **Complete**, **Inconsistent** (all there, but they contradict each other) or **Incomplete** (something is missing) | People should not read every PDF |
| BR-03 | A policy is valid only if it exists, is Active, matches the vehicle registration, and the incident date is inside the cover period. If not, the claim is denied | Never pay on a policy that does not cover the loss |
| BR-04 | If documents are missing, tell the customer, wait for them to add the document, then read everything again | The customer can fix this; nobody else can |
| BR-05 | Contradicting documents do not stop the claim. They feed the fraud assessment and are shown to the adjuster | A contradiction is a signal, not a verdict |
| BR-06 | A High fraud risk (score 70 or more) sends the claim to a fraud investigator before anything else happens. **Cleared**: carry on. **Confirmed**: deny | Do not spend effort on a claim that may be fraud |
| BR-07 | The damage estimate is taken from the repair estimate in the documents | The estimate is the evidence of the loss |
| BR-08 | The adjuster decides. **Approve**: go to settlement. **Reject** (comment required): deny. **Request information**: ask the customer, then review again | A person owns the decision |
| BR-09 | Settlement = the smallest of (claim amount, damage estimate, coverage limit) minus the deductible, never below zero. Deductible = 10,000 | Money is arithmetic, not judgment |
| BR-10 | If the settlement is above 175,000, a senior approver must approve first. **Rejected**: deny. Nothing is paid before approval | Four-eyes control on large amounts |
| BR-11 | Payment is recorded once per claim with the reference `PAY-<claim number>`. A second attempt returns the same payment | No double payments |
| BR-12 | At the end the case creates the claim packet and tells the customer the outcome | Closing the loop |
| BR-13 | A denial tells the customer, gives the reason where one is known, and ends the case. Fraud is never named to the customer | Fair, safe wording |
| BR-14 | The claim record always shows the current status and every result so far | Anyone can see where a claim is |
| BR-15 | Every step has a time limit. At 80% of it, notify. If it runs out, notify again (table in section 6H) | Claims must not get stuck unseen |
| BR-16 | The customer's email comes from the policy, not from the claim form | One place to maintain contact data |
| BR-17 | No business number is written into the case. They live in assets and data | Change a rule without touching the case |

### Exercise (10 minutes, on paper)
For each rule, decide: is it a **task** (someone does work), a **rule** (a condition that moves the claim), a **stage**, or a **setting**? Then predict which stage handles it. Compare with this table:

| Rules | Becomes |
|---|---|
| BR-01 | Case setting (Case ID) and the trigger |
| BR-02, BR-03, BR-16 | Tasks in **Intake** (a worker each) |
| BR-04 | Stage **Pending Customer**, entered by a rule from Intake and from Review |
| BR-05, BR-07 | Tasks in **Assessment** and what the adjuster sees in **Review** |
| BR-06 | Stage **Fraud Investigation**, entered by a rule from Assessment |
| BR-08 | Task in **Review** plus three rules out of Review |
| BR-09, BR-10, BR-11 | Tasks in **Settlement** plus gating rules |
| BR-12 | **Closure** |
| BR-03, BR-08, BR-10, BR-06 (Confirmed), BR-13 | Stage **Denied**, entered by four rules |
| BR-14 | A "save" task at the end of each stage (Part 6F) |
| BR-15 | SLAs (Part 6H) |
| BR-17 | Nothing in the case; it is why the workers read assets and data |

---

## 5. Five ideas you need before you start

**1. Stage.** A phase of the process. The case moves from stage to stage. Every stage has a name, tasks, and rules.

**2. Task.** One piece of work inside a stage: run an agent, call a function, run a workflow, or ask a person. A task has **inputs** (what you give it) and **outputs** (what it gives back).

**3. Variable.** When a task finishes, its outputs are stored as case **variables**, for example `vars.policyValid`. Later tasks and rules read them. Your claim as it was when the case started is `vars.response` (write `vars.response?.ClaimId` for the claim number).

> **Why `?.`** If the value is missing, `?.` returns nothing instead of causing an error. Use it for `vars.response`.

**4. Rules.** Rules decide *when* things happen. There are four places you will use them:

| Where | Question it answers | Example |
|---|---|---|
| **Stage entry rule** | When does this stage start? | "When Assessment is completed, start Review" |
| **Stage completion rule** | When is this stage done and where does the case go next? | "Review is done when the decision is Approve" |
| **Stage exit rule** (a detour) | When must the case leave this stage early, and for where? | "If the adjuster rejects, go to Denied" |
| **Task rule** | When does this task run? | "Run SeniorApproval only if senior approval is required" |

**5. The detour pattern (the most important idea).** Every detour is **two halves that match**:

```
 ORIGIN stage                                    TARGET stage
 Exit rule:                                      Entry rule:
   after the deciding task completes,              type: Selected stage exited
   if the condition is true,              <--->    stage: the origin stage
   leave and go to the TARGET                      condition: the SAME condition
   (Marks stage complete = off)                    Interrupting = on
```

And the origin stage's **normal completion rule is the exact opposite condition**. Example for Review:

| Rule | Condition |
|---|---|
| Completion (normal) | `decision === 'Approve'` |
| Detour to Denied | `decision === 'Reject'` |
| Detour to Pending Customer | `decision === 'RequestInformation'` |

> **Why the opposite?** Exactly one of the rules must be true. If two are true, two stages start at once. If none is true, the case waits forever.

**Two traps** (both found while building this):
- A secondary stage entry rule must be **Selected stage exited**. Not "Case entered" with a condition (that is only checked once, when the case starts, so the stage either starts immediately or never). Not "Ad hoc" (that only exists for tasks).
- If the origin stage *completes* (rather than exits) toward the target, the target must use **Selected stage completed**. This only happens once, in Fraud Investigation: Confirmed.

**Task rule vs required.** A task marked **required** (shown with a `*`) must finish before the stage can complete. A task that only sometimes runs (SeniorApproval) is **not required**. If a required task is skipped, the stage waits forever.

---

## 6. Build it, step by step

Conventions used below:
- **Resource** is the worker you pick when you add a task.
- **Inputs** tables show `Input name = what to put`. Click the field and press `@` (or type `/`) to pick a variable, or type the expression directly.
- Names are given so that rule names stay unique. Rule names must be unique across the whole case, and must not contain a colon.
- Button and field names in Studio Web can differ slightly between releases. Look for the nearest match.
- For each stage, **write its Description**. It helps the next person, and the Case Manager.

### 6A. Case settings (10 min)

1. Open **MotorInsuranceClaimCase** and click an empty part of the canvas (or the case icon) to open **Case plan properties**.
2. **Case ID**: choose **External key** and set the value to `vars.response?.ClaimId`.
3. Leave **Completion rules** for later (6B step 7).

> **Why:** the case is identified by the claim number. Anyone searching for a claim finds its case. And a duplicate claim number cannot start two cases.

### 6B. Happy path: five stages in a line (90 min)

Goal: Rahul goes from registered to paid with no human step except the adjuster.

#### Stage 1: Intake

**Add the stage.** Name `Intake`. Description: *Reads the claim documents with an AI agent and checks the policy is valid.*

**Why:** this stage answers two questions that need no human: *what do the documents say?* and *is the policy valid?*

| # | Task | Type | Resource | Run | Required |
|---|---|---|---|---|---|
| 1 | ClaimDocumentIntelligence | Agent | ClaimDocumentIntelligence | In parallel with 2 | Yes |
| 2 | ValidatePolicy | Function (process) | ValidatePolicy | In parallel with 1 | Yes |

> **Why parallel:** neither needs the other's answer. Running them together saves time.

**Inputs**

| Task | Input | Value |
|---|---|---|
| ClaimDocumentIntelligence | ClaimId | `vars.response?.ClaimId` |
| | DocumentReferences | `vars.response?.DocumentReferences` |
| ValidatePolicy | PolicyNumber | `vars.response?.PolicyNumber` |
| | VehicleRegistration | `vars.response?.VehicleRegistration` |
| | IncidentDate | `vars.response?.IncidentDate` |

Leave the optional input **DataFolder** empty. The workers find the data themselves.

**Outputs you get:** see section 2.2. Keep the default variable names (they are `camelCase` versions of the output names).

**Task rules** (names must be unique)
- ClaimDocumentIntelligence: *Start document analysis*, type **Runs sequentially** (starts when the stage starts).
- ValidatePolicy: *Start policy validation*, type **Runs sequentially**.

**Stage entry rule.** Name `Case started`, type **Case entered**. *Why: this is the first stage, so it starts when the case starts.*

**Stage completion rule.** Name `Documents analysed and policy checked`, completes the stage when **Required tasks completed**, with this expression:
```
(vars.documentIngestionStatus === 'Complete' || vars.documentIngestionStatus === 'Inconsistent') && vars.policyValid === true
```
> **Why:** *Inconsistent* is allowed through (BR-05: contradictions go to the fraud check and the adjuster). *Incomplete* is not (BR-04: that is a detour, added in 6C). An invalid policy is not (BR-03: detour, added in 6D).

#### Stage 2: Assessment

**Add the stage.** Name `Assessment`. Description: *Scores the fraud risk with an AI agent and works out the damage estimate from the repair estimate. Both run together.*

| # | Task | Type | Resource | Run | Required |
|---|---|---|---|---|---|
| 1 | FraudRiskAssessment | Agent | FraudRiskAssessment | Parallel with 2 | Yes |
| 2 | AssessDamage | API workflow | AssessDamage | Parallel with 1 | Yes |

| Task | Input | Value |
|---|---|---|
| FraudRiskAssessment | ClaimId | `vars.response?.ClaimId` |
| | PolicyNumber | `vars.response?.PolicyNumber` |
| | ClaimAmount | `vars.response?.ClaimAmount` |
| | IncidentDate | `vars.response?.IncidentDate` |
| | IncidentDescription | `vars.response?.IncidentDescription` |
| | ExtractedRepairEstimate | `vars.extractedRepairEstimate` |
| | DocumentInconsistencies | `vars.documentInconsistencies` |
| AssessDamage | ExtractedRepairEstimate | `vars.extractedRepairEstimate` |

Task rules: *Start fraud risk assessment* and *Start damage assessment*, both **Runs sequentially**.

**Stage entry rule.** Name `Intake completed`, type **Selected stage completed**, stage **Intake**.

**Stage completion rule.** Name `Fraud score and damage estimate ready`, **Required tasks completed**. No expression for now.

> **Why:** the agents need what Intake produced (`extractedRepairEstimate`, `documentInconsistencies`). That is why Assessment is *after* Intake and not beside it.

#### Stage 3: Review

**Add the stage.** Name `Review`. Description: *A claims adjuster reviews the documents, policy result and fraud assessment, then approves, rejects or asks the customer for more information.*

Task: **AdjusterReview**, type **Action** (human task), app `AdjusterReview` in folder `Shared/ClaimsSolution`. Required.
- **Task title:** `Review the claim and decide`.
- **Assign to:** *a specific user*: yourself. (You will play the adjuster.)

| Input | Value |
|---|---|
| ClaimId | `vars.response?.ClaimId` |
| CustomerName | `vars.response?.CustomerName` |
| ClaimAmount | `vars.response?.ClaimAmount` |
| DamageEstimate | `vars.damageEstimate` |
| PolicyValid | `vars.policyValid` |
| PolicyValidationReason | `vars.policyValidationReason` |
| DocumentIngestionStatus | `vars.documentIngestionStatus` |
| DocumentInconsistencies | `vars.documentInconsistencies` |
| RiskLevel | `vars.riskLevel` |
| FraudScore | `vars.fraudScore` |
| FraudReasons | `vars.fraudReasons` |

Outputs: `decision` (the button pressed) and `comments`.
Task rule: *Start adjuster review*, **Runs sequentially**.

**Stage entry rule.** Name `Assessment completed`, **Selected stage completed**, stage **Assessment**.

**Stage completion rule.** Name `Adjuster decision recorded`, **Required tasks completed**, expression:
```
vars.decision === 'Approve'
```
> **Why:** the adjuster is shown everything the machines found, so they decide with full information (BR-05, BR-08). Only *Approve* completes the stage; the other two buttons are detours (6C, 6D).

#### Stage 4: Settlement

**Add the stage.** Name `Settlement`. Description: *Calculates the payable amount (loss minus deductible, capped at cover). Above the approval threshold a senior approver must approve before payment is recorded.*

| # | Task | Type | Resource | Required | Task rule |
|---|---|---|---|---|---|
| 1 | CalculateSettlement | Function | CalculateSettlement | Yes | *Start settlement calculation*: Runs sequentially |
| 2 | SeniorApproval | Action | SeniorApproval | **No** | *Only if senior approval is required*: Runs sequentially, expression `vars.seniorApprovalRequired === true` |
| 3 | ProcessSettlement | Function | ProcessSettlement | Yes | *Pay only if no approval needed or approved*: Runs sequentially, expression `vars.seniorApprovalRequired === false \|\| vars.decision2 === 'Approved'` |

For SeniorApproval: task title `Approve a settlement above the threshold`, assigned to you.

| Task | Input | Value |
|---|---|---|
| CalculateSettlement | PolicyNumber | `vars.response?.PolicyNumber` |
| | ClaimAmount | `vars.response?.ClaimAmount` |
| | DamageEstimate | `vars.damageEstimate` |
| SeniorApproval | ClaimId | `vars.response?.ClaimId` |
| | SettlementAmount | `vars.settlementAmount` |
| | DamageEstimate | `vars.damageEstimate` |
| ProcessSettlement | ClaimId | `vars.response?.ClaimId` |
| | CustomerName | `vars.response?.CustomerName` |
| | PolicyNumber | `vars.response?.PolicyNumber` |
| | SettlementAmount | `vars.settlementAmount` |
| | SeniorApprovalRequired | `vars.seniorApprovalRequired` |
| | SeniorApprovalDecision | `vars.decision2` |

**Stage entry rule.** Name `Adjuster approved the claim`, **Selected stage completed**, stage **Review**, expression `vars.decision === "Approve"`.

**Stage completion rule.** Name `Settlement paid`, **Required tasks completed**, expression `vars.settlementStatus === "Paid"`.

> **Why SeniorApproval is not required:** for Rahul (162,400) it never runs. If it were required and skipped, the stage would wait forever.
> **Why two gates:** the SeniorApproval rule decides whether an approval is needed (BR-10). The ProcessSettlement rule makes sure *nothing is paid before approval*. The function itself also refuses to pay without approval, so there are two safety nets.

#### Stage 5: Closure

**Add the stage.** Name `Closure`. Description: *Creates the claim packet and prepares the customer notification, then the case closes.*

| # | Task | Type | Resource | Run | Task rule |
|---|---|---|---|---|---|
| 1 | GenerateClaimPacket | API workflow | GenerateClaimPacket | Parallel | *Start claim packet* |
| 2 | CreateCustomerNotification | API workflow | CreateCustomerNotification | Parallel | *Start customer notification* |

| Task | Input | Value |
|---|---|---|
| GenerateClaimPacket | ClaimId | `vars.response?.ClaimId` |
| CreateCustomerNotification | ClaimId | `vars.response?.ClaimId` |
| | CustomerName | `vars.response?.CustomerName` |
| | SettlementStatus | `vars.settlementStatus` |
| | FraudInvestigationResult | leave empty for now (6E fills it) |
| | SettlementAmount | `vars.settlementAmount` |

**Stage entry rule.** Name `Settlement completed`, **Selected stage completed**, stage **Settlement**.
**Stage completion rule.** Name `Packet and notification done`, **Required tasks completed**.

#### Step 7: Case completion rules (back in Case plan properties)

In **Case plan properties > Completion rules**, add one rule: name `All required stages completed`, and choose the option that completes the case when all required stages are completed. (The exact option label can differ by release.)

> **Why:** this tells the case when it is finished: when every required (primary) stage is done.

#### Test the happy path
1. In Studio Web press **Debug**, and pick the Rahul claim (or register a new one, see 3.4).
2. When **Review the claim and decide** appears in Action Center > Tasks, open it and press **Approve**.
3. Watch the case move Intake, Assessment, Review, Settlement, Closure.

> **Check:** the instance reaches **Completed**, and the trail is `Intake > Assessment > Review > Settlement > Closure`. Rahul's settlement is **162,400** with payment reference `PAY-CLM-<number>`.
> **Stuck?** Open the example case `1_HappyPath` and compare.

### 6C. Pending Customer: documents are missing (45 min)

Goal: when something is missing, tell the customer, wait for them, and carry on with no human step.

**Add the stage.** Name `Pending Customer`. Switch on **Secondary stage**. Switch off **Required for case completion**. Description: *Exception path. Entered when documents are missing or the adjuster asks for more information. The case emails the customer, waits until they add the document, then returns to where it came from.*

#### Tasks

| # | Task | Type | Notes |
|---|---|---|---|
| 1 | Email the customer about the missing documents | Connector activity: **Gmail > Send Email** | Required. Task rule *Send the customer request email*, **Runs sequentially** |

Pick your **Gmail** connection. Fill in:

| Field | Value |
|---|---|
| To | `vars.customerEmail` |
| Subject | `'Action needed: documents required for claim ' + vars.response?.ClaimId` |
| Body | see the text below |
| **Save as draft** | **false** (important: the default is *true*, which saves a draft and sends nothing) |

Body expression:
```
'Dear ' + vars.response?.CustomerName + ',\n\nWe are processing your motor insurance claim ' + vars.response?.ClaimId + ' but we still need the following before we can continue:\n\n' + (vars.missingDocuments || 'additional supporting documents') + '\n\nPlease add them to your claim in the claims portal. We will carry on automatically as soon as they arrive.\n\nThank you,\nMotor Claims Team'
```

> **Why the email comes from the policy:** `vars.customerEmail` was produced by ValidatePolicy from PolicyMaster (BR-16).

#### Entry rules (two detours into this stage)

| Rule name | Type | Stage | Interrupting | Condition |
|---|---|---|---|---|
| `Documents incomplete at Intake` | **Selected stage exited** | Intake | On | `vars.documentIngestionStatus === 'Incomplete' && vars.policyValid === true` |
| `Adjuster requested more information` | **Selected stage exited** | Review | On | `vars.decision === 'RequestInformation'` |

#### The matching exit rules on the origin stages (the other half of each detour)

On **Intake**, add an exit rule:
- Name `Documents incomplete so customer is contacted`. Type **Selected tasks completed**: ClaimDocumentIntelligence and ValidatePolicy. **Marks stage complete: off**. **Exit to stage: Pending Customer**. Condition: `vars.documentIngestionStatus === 'Incomplete' && vars.policyValid === true`.

On **Review**, add an exit rule:
- Name `Exit to Pending Customer after adjuster information request`. **Selected tasks completed**: AdjusterReview. **Exit to stage: Pending Customer**. Condition: `vars.decision === 'RequestInformation'`.

#### The wait for the customer (the completion rule of Pending Customer)

Add a **Completion rule**:
1. Name `Customer information received and back to Intake`. Completion rule type: **Return to origin stage**.
2. **Complete stage when:** **Connector event occurs**.
3. **Select activity:** *UiPath Data Fabric: Record Updated*.
4. **Connection:** your Data Fabric connection. **Entity Scope:** Folder. **Entity:** MotorInsuranceClaim (choose it under *Defined resources*).
5. **Filter** (All of the following):
   - `ClaimId` **equals** the case's claim number. In the value box press `@`, expand `trigger_1` with the small arrow next to it, and pick the claim number. Do not click the `trigger_1` name itself, which would pick the whole object.
   - `CustomerInformationStatus` **equals** `Received`.

> **Why an event instead of a person:** the Intake App's *Add document* button already sets `CustomerInformationStatus = Received` on the claim. The case just listens for that change. Nobody has to confirm anything (BR-04).
> **Why return to origin:** the stage goes back to where the claim came from. If Intake sent it here, Intake runs again and reads all documents, including the new one. If Review sent it here, Review runs again.
> **Why the filter has two conditions:** other claims are updated all the time. Only *this* claim's change to *Received* may wake this case.

#### Adjust the opposite conditions
Intake's normal completion rule already excludes *Incomplete* (6B), so nothing to change there. Review's already requires `Approve`.

#### Test
1. Register **Priya** in the Intake App (6 files, no repair estimate), then Debug that claim.
2. The case should reach **Pending Customer** and send the email. Check your inbox.
3. In the Intake App, choose **Add document** for her claim and upload `02_Documents/Priya_Nair/SUPPLEMENTAL_RepairEstimate.pdf`.
4. The case should go back to Intake, then Assessment, Review. Approve it in Action Center.

> **Check:** trail `Intake > Pending Customer > Intake > Assessment > Review > Settlement > Closure`. Priya's settlement is **84,600**.
> **Stuck?** Open the example case `2_PendingCustomer` and compare.

### 6D. Denied: three ways to "no" (35 min)

**Add the stage.** Name `Denied`. **Secondary stage** on, **Required for case completion** off. Description: *Exception path that ends the case. Entered when the policy is invalid, the adjuster or senior approver rejects the claim, or fraud is confirmed. Prepares the denial notification.*

Task: **Notify customer of denial**, API workflow `CreateCustomerNotification`. Required. Task rule *Start denial notification*, **Runs sequentially**.

| Input | Value |
|---|---|
| ClaimId | `vars.response?.ClaimId` |
| CustomerName | `vars.response?.CustomerName` |
| SettlementStatus | `vars.settlementStatus` |
| FraudInvestigationResult | leave empty until 6E |
| SettlementAmount | `vars.settlementAmount` |

(Its outputs get new variable names such as `notificationStatus2`. That is fine.)

**Stage completion rule.** Name `Denial notification sent`, **Required tasks completed**.

**Entry rules** (all type **Selected stage exited**, Interrupting on):

| Rule name | Stage | Condition |
|---|---|---|
| `Policy found invalid at Intake` | Intake | `!!vars.policyValidationReason && vars.policyValid === false` |
| `Adjuster rejected the claim` | Review | `vars.decision === 'Reject'` |
| `Senior approver rejected the settlement` | Settlement | `vars.decision2 === 'Rejected'` |

> **Why `!!vars.policyValidationReason`:** `policyValid` starts as *false* before ValidatePolicy has run. Without this guard the case would deny every claim instantly at the start. The reason text is only filled once the policy has actually been checked.

**The matching exit rules on the origin stages** (each: **Selected tasks completed**, **Marks stage complete: off**, **Exit to stage: Denied**):

| On stage | Rule name | After tasks | Condition |
|---|---|---|---|
| Intake | `Policy invalid so claim is denied` | ValidatePolicy | `!!vars.policyValidationReason && vars.policyValid === false` |
| Review | `Exit to Denied after adjuster rejection` | AdjusterReview | `vars.decision === 'Reject'` |
| Settlement | `Exit to Denied after senior approver rejection` | SeniorApproval | `vars.decision2 === 'Rejected'` |

**Case completion rule (second one).** In Case plan properties add: name `Claim denied and case closed`, type **Selected stage completed**, stage **Denied**.

> **Why:** a denied case never completes the five primary stages, so *All required stages completed* would never happen. This rule ends it when Denied is done (BR-13).

#### Test
- Rahul's claim with the adjuster pressing **Reject** (enter a comment). Expected trail: `Intake > Assessment > Review > Denied`.
- Arjun with the senior approver pressing **Rejected** (after the fraud question in 6E).
- A claim for policy `POL-000001` (Meera Iyer, expired policy): `Intake > Denied`.

> **Stuck?** Open the example case `3_Denied` and compare.

### 6E. Fraud Investigation (30 min)

**Add the stage.** Name `Fraud Investigation`. **Secondary** on, **Required** off. Description: *Exception path. Starts as soon as the fraud agent flags a High risk and interrupts normal work. An investigator clears the claim (the case resumes) or confirms fraud (the claim is denied).*

Task: **FraudInvestigation**, type **Action**, app `FraudInvestigation`. Required. Title `Investigate the flagged claim`. Assign to yourself. Task rule *Start fraud investigation*, **Runs sequentially**.

| Input | Value |
|---|---|
| ClaimId | `vars.response?.ClaimId` |
| FraudScore | `vars.fraudScore` |
| FraudReasons | `vars.fraudReasons` |
| DocumentInconsistencies | `vars.documentInconsistencies` |

Outputs: `fraudResult` (Cleared or Confirmed) and `comments3`.

> **Do not rename the output** `InvestigationResult` in the designer. Its name must match the app exactly, or the variable stays empty and the stage never finishes.

**Entry rule.** Name `Assessment found high fraud risk`, **Selected stage exited**, stage **Assessment**, Interrupting on, condition `vars.fraudFlag === true && !vars.fraudResult`.

**Exit rule on Assessment** (the other half): name `High fraud risk so investigation starts`, **Selected tasks completed**: FraudRiskAssessment and AssessDamage, **Exit to stage: Fraud Investigation**, condition `vars.fraudFlag === true && !vars.fraudResult`.

**Change Assessment's normal completion rule** to add the opposite condition:
```
!(vars.fraudFlag === true && !vars.fraudResult)
```
> **Why `&& !vars.fraudResult`:** after the investigator clears the claim, `fraudResult` is filled and the claim must be allowed through Assessment, not sent to the investigator again.

**Two completion rules on Fraud Investigation**

| Rule name | Completion rule type | Complete stage when | Condition |
|---|---|---|---|
| `Investigation cleared and case resumes` | **Return to origin stage** | Required tasks completed | `vars.fraudResult === 'Cleared'` |
| `Fraud confirmed and claim denied` | (normal completion) | Required tasks completed | `vars.fraudResult === 'Confirmed'` |

**Add a fourth entry rule to Denied:** name `Fraud confirmed by investigator`, type **Selected stage completed** (this is the one case where it is *completed*, not *exited*), stage **Fraud Investigation**, Interrupting on, condition `vars.fraudResult === 'Confirmed'`.

**Fill the empty mapping** in Denied's CreateCustomerNotification: `FraudInvestigationResult = vars.fraudResult`.

> **Why Fraud Investigation completes (not exits) for Confirmed:** both Cleared and Confirmed finish the investigator's task. Confirmed *completes* the stage; that is why Denied waits for the stage to be *completed*.
> **Why return to origin for Cleared:** the case goes back to Assessment and reruns it. That costs two more agent calls but gives a clean result.

#### Test
Debug **Arjun** twice: once with the investigator pressing **Cleared** (then adjuster **Approve**, senior approver **Approved**), once with **Confirmed**.
- Cleared: `Intake > Assessment > Fraud Investigation > Assessment > Review > Settlement > Closure`. Settlement **230,000**, senior approval needed.
- Confirmed: `Intake > Assessment > Fraud Investigation > Denied`.

> **Stuck?** Open the example case `4_FraudInvestigation` and compare.

### 6F. Keep the claim record up to date (optional, 40 min)

Goal (BR-14): after each stage, write its results to the claim row, so anyone can see where a claim is.

You add **one task at the end of each stage**: the function **UpdateClaim**. It is the same worker every time. You tell it *which stage you are in* and give it that stage's values. It writes only that stage's fields.

Every call has: `ClaimId = vars.response?.ClaimId`, `Stage = <the stage name below>`, `ClaimStatus = <label below>`. Task rule: **Runs sequentially**. Required.

| Task name | Placed in | Stage value | ClaimStatus | Fields to fill |
|---|---|---|---|---|
| Save intake results to the claim record | Intake, last | `Intake` | `vars.policyValid === false ? 'Policy invalid' : (vars.documentIngestionStatus === 'Incomplete' ? 'Documents incomplete' : 'Intake complete')` | DocumentIngestionStatus, DocumentsComplete, MissingDocuments, DocumentInconsistencies, PolicyValid, PolicyValidationReason, ExtractedCustomerName, ExtractedPolicyNumber, ExtractedVehicleRegistration, ExtractedIncidentDate, ExtractedDocumentTypes, ExtractedRepairEstimate (each `vars.` + the same name with a lowercase first letter) |
| Save assessment results to the claim record | Assessment, last | `Assessment` | `(vars.fraudFlag === true && !vars.fraudResult) ? 'High fraud risk' : 'Assessment complete'` | FraudScore, RiskLevel, FraudFlag, FraudReasons, DamageEstimate |
| Save adjuster decision to the claim record | Review, last | `Review` | `vars.decision === 'Approve' ? 'Approved by adjuster' : (vars.decision === 'Reject' ? 'Rejected by adjuster' : 'Information requested')` | AdjusterDecision = `vars.decision`, AdjusterComments = `vars.comments` |
| Save settlement calculation to the claim record | Settlement, right after CalculateSettlement | `SettlementCalculation` | `vars.seniorApprovalRequired === true ? 'Awaiting senior approval' : 'Settlement calculated'` | SettlementAmount, SeniorApprovalRequired |
| Save payment details to the claim record | Settlement, last. Task rule expression: `vars.settlementStatus === 'Paid'` | `Settlement` | `Settled` | SeniorApprovalDecision = `vars.seniorApprovalRequired === true ? vars.decision2 : 'NotRequired'`, SeniorApprovalComments = `vars.comments2`, SettlementStatus, PaymentReference, SettlementDate |
| Save closure results to the claim record | Closure, last | `Closure` | `Closed` | ClaimPacketReference, NotificationStatus, ClaimOutcome |
| Save customer request status to the claim record | Pending Customer, after the email | `PendingCustomer` | `Awaiting customer information` | CustomerInformationStatus = `Requested` (plain text) |
| Save fraud investigation result to the claim record | Fraud Investigation, last | `FraudInvestigation` | `vars.fraudResult === 'Confirmed' ? 'Fraud confirmed' : 'Fraud cleared'` | FraudInvestigationResult = `vars.fraudResult`, FraudInvestigationComments = `vars.comments3` |
| Save denial to the claim record | Denied, last | `Denied` | `Denied` | NotificationStatus = `vars.notificationStatus2`, ClaimOutcome = `vars.claimOutcome2`, SeniorApprovalDecision = `vars.decision2`, SeniorApprovalComments = `vars.comments2` |

**Then update every detour so it waits for the save step.** In each exit rule on Intake, Assessment and Review, add the stage's save task to the *Selected tasks completed* list. For example, Review's rules become *AdjusterReview and Save adjuster decision to the claim record*.

> **Why:** a detour leaves the stage as soon as its deciding task completes. Without this, a rejected claim would leave Review *before* its decision was saved, and the record would miss it.

> **Why one worker for all stages:** one place to maintain how claims are written, and the case stays readable. The worker only writes fields that belong to the stage you name, so a mistake in one stage cannot overwrite another stage's data.

> **Check:** after a full run, open the claim row in Data Fabric. `ClaimStatus` is **Closed**, and the fraud score, adjuster decision, payment reference and notification are filled.

### 6G. Emails to the customer at the end (optional, 20 min)

Same pattern as the email in 6C (Gmail **Send Email**, Save as draft **false**). Add one in **Closure** and one in **Denied**, **before** the save task of that stage. Make both **not required**, with task rule **Runs sequentially** and the expression `!!vars.customerEmail` (so a missing address never blocks the case).

| Stage | Task name | Rule name | Subject | Body (expression) |
|---|---|---|---|---|
| Closure | Email the customer that the claim is settled | `Send the settlement email` | `'Your claim ' + vars.response?.ClaimId + ' has been settled'` | `'Dear ' + vars.response?.CustomerName + ',\n\nGood news: your motor insurance claim ' + vars.response?.ClaimId + ' has been settled.\n\nSettlement amount: INR ' + vars.settlementAmount + '\nPayment reference: ' + vars.paymentReference + '\n\nThank you for choosing us.\nMotor Claims Team'` |
| Denied | Email the customer that the claim is declined | `Send the denial email` | `'Update on your claim ' + vars.response?.ClaimId` | `'Dear ' + vars.response?.CustomerName + ',\n\nWe have reviewed your motor insurance claim ' + vars.response?.ClaimId + ' and we are sorry to tell you that we cannot approve it.\n\n' + ((vars.policyValid === false && vars.policyValidationReason) ? ('Reason: ' + vars.policyValidationReason) : 'The decision was made after review by our claims team.') + '\n\nIf you believe this is a mistake, please reply to this email or contact us with any additional information.\nMotor Claims Team'` |

> **Why not required:** the stage must not wait on an email that has no address to go to.
> **Why the denial never says "fraud":** BR-13. A customer is told only the reason that is safe to tell.

### 6H. Time limits: SLAs (optional, 20 min)

For each stage open **SLA and escalations**, add an SLA with an *at risk* notification at **80%** and a *breached* notification, to yourself. Add one SLA to the **case** itself.

| Where | Name | Limit |
|---|---|---|
| Case | Claim resolution SLA | 5 days |
| Intake | Intake SLA | 2 hours |
| Assessment | Assessment SLA | 2 hours |
| Review | Adjuster review SLA | 2 days |
| Settlement | Settlement SLA | 1 day |
| Closure | Closure SLA | 2 hours |
| Pending Customer | Pending customer SLA | 2 days |
| Fraud Investigation | Fraud investigation SLA | 1 day |
| Denied | Denied SLA | 2 hours |

Escalation names must be unique, for example `Intake at risk` and `Intake breached`.

> **Why:** the clock starts when the stage starts. People are slower than machines, so the limits for human stages (Review, Fraud, Pending) are in days, and the machine stages are in hours. At 80% someone is warned; at 100% someone is told it is late (BR-15).

### 6I. Final test (20 min)

Run every row of Appendix D. Tick each.

---

## 7. Appendix A: variable dictionary

| Variable | Produced by | Type | Values / meaning |
|---|---|---|---|
| `response` | The trigger | object | The claim row as it was when created. Read with `vars.response?.Field` |
| `documentIngestionStatus` | ClaimDocumentIntelligence | text | Complete, Inconsistent, Incomplete |
| `documentsComplete` | ClaimDocumentIntelligence | true/false | All 7 documents present |
| `missingDocuments` | ClaimDocumentIntelligence | text | Names of missing documents |
| `documentInconsistencies` | ClaimDocumentIntelligence | text | Contradictions found |
| `extractedCustomerName`, `extractedPolicyNumber`, `extractedVehicleRegistration`, `extractedIncidentDate`, `extractedDocumentTypes` | ClaimDocumentIntelligence | text | What the documents say |
| `extractedRepairEstimate` | ClaimDocumentIntelligence | number | Total on the repair estimate |
| `policyValid` | ValidatePolicy | true/false | |
| `policyValidationReason` | ValidatePolicy | text | Why valid or invalid. Always filled once checked |
| `customerEmail` | ValidatePolicy | text | From PolicyMaster |
| `fraudScore` | FraudRiskAssessment | number | 0 to 100 |
| `riskLevel` | FraudRiskAssessment | text | Low, Medium, High |
| `fraudFlag` | FraudRiskAssessment | true/false | True only for High |
| `fraudReasons` | FraudRiskAssessment | text | |
| `damageEstimate` | AssessDamage | number | |
| `decision` | AdjusterReview | text | Approve, Reject, RequestInformation |
| `comments` | AdjusterReview | text | |
| `settlementAmount` | CalculateSettlement | number | After deductible |
| `seniorApprovalRequired` | CalculateSettlement | true/false | Above 175,000 |
| `decision2` | SeniorApproval | text | Approved, Rejected |
| `comments2` | SeniorApproval | text | |
| `settlementStatus` | ProcessSettlement | text | Paid |
| `paymentReference` | ProcessSettlement | text | PAY-<claim number> |
| `settlementDate` | ProcessSettlement | text | |
| `claimPacketReference` | GenerateClaimPacket | text | PACKET-<claim number> |
| `notificationStatus`, `claimOutcome`, `notificationText` | CreateCustomerNotification (Closure) | text | Outcome Settled |
| `notificationStatus2`, `claimOutcome2`, `notificationText2` | CreateCustomerNotification (Denied) | text | Outcome Denied or FraudRejected |
| `fraudResult` | FraudInvestigation | text | Cleared, Confirmed |
| `comments3` | FraudInvestigation | text | |

## 8. Appendix B: every rule on one page

**Case settings**
| Item | Value |
|---|---|
| Case ID | External key: `vars.response?.ClaimId` |
| Completion rule 1 | `All required stages completed` |
| Completion rule 2 | `Claim denied and case closed`: Denied completed |

**Stage entry rules**
| Stage | Rule name | Type | From | Condition | Interrupting |
|---|---|---|---|---|---|
| Intake | Case started | Case entered | | | |
| Assessment | Intake completed | Stage completed | Intake | | |
| Review | Assessment completed | Stage completed | Assessment | | |
| Settlement | Adjuster approved the claim | Stage completed | Review | `vars.decision === "Approve"` | |
| Closure | Settlement completed | Stage completed | Settlement | | |
| Pending Customer | Documents incomplete at Intake | Stage exited | Intake | `vars.documentIngestionStatus === 'Incomplete' && vars.policyValid === true` | On |
| Pending Customer | Adjuster requested more information | Stage exited | Review | `vars.decision === 'RequestInformation'` | On |
| Denied | Policy found invalid at Intake | Stage exited | Intake | `!!vars.policyValidationReason && vars.policyValid === false` | On |
| Denied | Adjuster rejected the claim | Stage exited | Review | `vars.decision === 'Reject'` | On |
| Denied | Senior approver rejected the settlement | Stage exited | Settlement | `vars.decision2 === 'Rejected'` | On |
| Denied | Fraud confirmed by investigator | Stage **completed** | Fraud Investigation | `vars.fraudResult === 'Confirmed'` | On |
| Fraud Investigation | Assessment found high fraud risk | Stage exited | Assessment | `vars.fraudFlag === true && !vars.fraudResult` | On |

**Stage completion rules (normal finish)**
| Stage | Rule name | Condition |
|---|---|---|
| Intake | Documents analysed and policy checked | `(vars.documentIngestionStatus === 'Complete' \|\| vars.documentIngestionStatus === 'Inconsistent') && vars.policyValid === true` |
| Assessment | Fraud score and damage estimate ready | `!(vars.fraudFlag === true && !vars.fraudResult)` |
| Review | Adjuster decision recorded | `vars.decision === 'Approve'` |
| Settlement | Settlement paid | `vars.settlementStatus === "Paid"` |
| Closure | Packet and notification done | none |
| Denied | Denial notification sent | none |
| Fraud Investigation | Investigation cleared and case resumes (return to origin) | `vars.fraudResult === 'Cleared'` |
| Fraud Investigation | Fraud confirmed and claim denied | `vars.fraudResult === 'Confirmed'` |
| Pending Customer | Customer information received and back to Intake (return to origin) | Event: Data Fabric record updated, ClaimId equals this claim and CustomerInformationStatus equals Received |

**Stage exit rules (detours)**
| On stage | Rule name | After tasks | Goes to | Condition |
|---|---|---|---|---|
| Intake | Policy invalid so claim is denied | ValidatePolicy | Denied | `!!vars.policyValidationReason && vars.policyValid === false` |
| Intake | Documents incomplete so customer is contacted | ClaimDocumentIntelligence, ValidatePolicy | Pending Customer | `vars.documentIngestionStatus === 'Incomplete' && vars.policyValid === true` |
| Assessment | High fraud risk so investigation starts | FraudRiskAssessment, AssessDamage | Fraud Investigation | `vars.fraudFlag === true && !vars.fraudResult` |
| Review | Exit to Denied after adjuster rejection | AdjusterReview | Denied | `vars.decision === 'Reject'` |
| Review | Exit to Pending Customer after adjuster information request | AdjusterReview | Pending Customer | `vars.decision === 'RequestInformation'` |
| Settlement | Exit to Denied after senior approver rejection | SeniorApproval | Denied | `vars.decision2 === 'Rejected'` |

(If you built 6F, each "After tasks" list also contains that stage's save task.)

**Task rules that have a condition**
| Task | Rule | Condition |
|---|---|---|
| SeniorApproval | Only if senior approval is required | `vars.seniorApprovalRequired === true` |
| ProcessSettlement | Pay only if no approval needed or approved | `vars.seniorApprovalRequired === false \|\| vars.decision2 === 'Approved'` |
| Save payment details to the claim record | | `vars.settlementStatus === 'Paid'` |
| Email at Closure / Denied | | `!!vars.customerEmail` |

## 9. Appendix C: claim status values (what the claim row shows)

| Status | Set by | Meaning |
|---|---|---|
| Registered | The Intake App | Just created |
| Intake complete / Documents incomplete / Policy invalid | Intake save step | |
| Assessment complete / High fraud risk | Assessment save step | |
| Awaiting customer information | Pending Customer save step | Waiting for the customer |
| Fraud cleared / Fraud confirmed | Fraud save step | |
| Approved by adjuster / Rejected by adjuster / Information requested | Review save step | |
| Settlement calculated / Awaiting senior approval | Settlement calculation save step | |
| Settled | Payment save step | Paid |
| Closed | Closure save step | Final, paid |
| Denied | Denied save step | Final, not paid |

## 10. Appendix D: test matrix

Run one claim at a time. Press the buttons as shown.

| # | Claim | Your clicks | Expected trail | Check afterwards |
|---|---|---|---|---|
| T1 | Rahul | Adjuster **Approve** | Intake, Assessment, Review, Settlement, Closure | Paid 162,400 |
| T2 | Rahul | Adjuster **Reject** (comment) | Intake, Assessment, Review, Denied | Denial email. Claim status Denied |
| T3 | Rahul | Adjuster **Request information**, then add a document in the Intake App, then **Approve** | Intake, Assessment, Review, Pending Customer, Review, Settlement, Closure | Email received |
| T4 | Priya | Add the estimate in the Intake App, then adjuster **Approve** | Intake, Pending Customer, Intake, Assessment, Review, Settlement, Closure | Paid 84,600 |
| T5 | Arjun | Fraud **Cleared**, adjuster **Approve**, senior **Approved** | Intake, Assessment, Fraud Investigation, Assessment, Review, Settlement, Closure | Paid 230,000 |
| T6 | Arjun | Fraud **Confirmed** | Intake, Assessment, Fraud Investigation, Denied | Denial email does not say fraud |
| T7 | Arjun | Fraud **Cleared**, adjuster **Approve**, senior **Rejected** | ... Settlement, Denied | Nothing paid |
| T8 | Meera (policy POL-000001, expired) | none | Intake, Denied | Claim status Denied. No email is sent, because the expired policy has no email address on it (this is the "missing address never blocks the case" rule) |

## 11. Appendix E: troubleshooting

| What you see | Likely cause | What to do |
|---|---|---|
| The case jumps to **Denied** at the very start | A Denied entry rule uses `policyValid === false` without the guard | Use `!!vars.policyValidationReason && vars.policyValid === false` |
| A secondary stage never starts | Its entry rule is *Case entered* or *Ad hoc*, or there is no matching exit rule on the origin stage | Entry type must be **Selected stage exited**, and the origin stage needs the matching exit rule |
| The case waits after a human task | Output renamed in the designer, so the variable stays empty | Do not rename outputs. The name must match the app |
| Stuck in Fraud Investigation after **Confirmed** | Denied's entry rule from Fraud is *exited* instead of *completed* | Change it to **Selected stage completed** |
| A stage never finishes | A required task was skipped | Mark tasks that only sometimes run as **not required** |
| Two stages start at once | The normal completion rule and a detour are both true | Make the completion condition the opposite of the detour conditions |
| The email does not arrive | *Save as draft* is on, or the policy has no email | Set Save as draft to false. Check `customerEmail` in the run |
| Rule name rejected | Not unique, or contains a colon | Rename |
| Setup says the name cannot be used | A leftover deployment or a folder deleted by hand blocks `ClaimsSolution` | Run Setup with **DeploymentName** set to a new name, for example `ClaimsSolutionNew`, and use that name later |
| The Setup screen looks stuck | Studio Web shows only the first lines until the run ends | Run Setup again with **Action** = `Status`; it prints how far Setup got and says FINISHED or NOT FINISHED |
| Debug asks you to pick a Gmail or Data Fabric connection | The connection does not exist yet | Create it in Integration Service > Connections, then bind it when the designer asks |
| Debug cannot find an app or worker | The Debug links were not created (Setup did not finish) | Run Setup with **Action** = `Status`. If it did not finish, delete the solution **MotorInsuranceClaimManagement** and run Setup again |
| After Upgrade the deployment says *Needs setup to activate* | The cases need your connections | **Set up activation**, bind your Gmail and Data Fabric connections, then **Activate** |
| The case does not start when a claim is registered | The deployment is not activated, or the Data Fabric connection is not bound | Finish **Set up activation** and **Activate** (3.7) |
| Two copies of the solution appear in Studio Web | Setup was run twice | Delete the extra copy of **MotorInsuranceClaimManagement** |
| Settlement step fails for a claim you already ran | The payment was already recorded | This is safe: the worker returns the same payment |

## 12. Appendix F: glossary

| Term | Meaning |
|---|---|
| **Case** | One running claim, from start to end |
| **Case plan** | The design of the process (what you build) |
| **Stage** | A phase of the process |
| **Primary / secondary stage** | Main road / exception path |
| **Task** | One unit of work in a stage |
| **Variable** | A value stored from a task's output, read as `vars.name` |
| **Entry rule** | When a stage starts |
| **Completion rule** | When a stage is done |
| **Exit rule** | When the case must leave a stage early |
| **Return to origin** | Go back to the stage the case came from |
| **Interrupting** | A stage that takes over even while another is active |
| **SLA** | A time limit with warnings |
| **Action task** | A task a person completes in Action Center |
| **Connector** | A link to another system (Gmail, Data Fabric) |
| **Entity** | A Data Fabric table |
| **Asset** | A named setting kept in Orchestrator |
| **Example case** | One of the five finished cases (`1_HappyPath` to `5_Complete`) inside your solution, to compare with or to jump in from |
