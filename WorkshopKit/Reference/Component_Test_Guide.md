# How to test each component

Every expected value below was produced by a real run against the test claims CLM-1001 (Rahul), CLM-1002 (Priya) and CLM-1003 (Arjun), or follows directly from the code. Test in this order: data, Intake App, functions, API workflows, agents, human tasks.

**Verified by a live run on the deployed solution (version 1.0.6):** every ValidatePolicy, GetClaimHistory, CalculateSettlement (except the asset-change test), AssessDamage, CreateCustomerNotification and FetchClaimDocumentText case below, the ProcessSettlement approval refusal, and all the claim results for the agents. **Derived from the code but not run:** the asset-change test, ProcessSettlement with Approved (it writes data), GenerateClaimPacket and the Intake App checks, and the human-task checks.

## 0. How to run a process by hand

**In the UI (menu names may differ slightly):** Orchestrator > Solutions > Deployments > `ClaimsSolution` > **Start job**, pick the process, paste the input JSON, and run. The job's **Output** appears when it finishes. You can also reach the same processes under the `MotorInsuranceClaims/ClaimsSolution` folder in Orchestrator.

**From the command line (works as tested):**
```
uip or processes list --folder-path "MotorInsuranceClaims/ClaimsSolution" --output json
uip or jobs start <PROCESS-KEY> --folder-path "MotorInsuranceClaims/ClaimsSolution" --input-arguments '{"PolicyNumber":"POL-982341"}'
uip or jobs get <JOB-KEY> --output json
```
Look at `State` (Successful) and `OutputArguments`. On Windows PowerShell, put the JSON in a file or escape the quotes.

**Rule for every test:** a function that cannot finish normally still ends as Successful but sets `error_type` and `error_message`. Always read those two fields, not just the job state.

## 1. Data layer

| Test | How | Expected |
|---|---|---|
| Entities exist | Solutions > deployment > Resources, or `uip df entities list --folder-key <FOLDER-KEY>` | ClaimHistory, SettlementRegister, PolicyMaster, MotorInsuranceClaim |
| Reference data seeded | `uip df records query <PolicyMaster-id> --folder-key <FOLDER-KEY> --body '{}'` | 4 policies (POL-982341, POL-764512, POL-551209, POL-000001 Expired) |
| History seeded | same on ClaimHistory | 3 rows (Rahul 0 prior, Priya 1, Arjun 3 with 2 recent) |
| Claims exist | query MotorInsuranceClaim | CLM-1001, CLM-1002, CLM-1003 with `DocumentReferences` filled |
| Long text fits | Intake App submits 7 files | Row saved (the field allows 9000 characters) |
| Assets | Orchestrator > folder > Assets | ClaimsDeductible 10000, ClaimsSeniorApprovalThreshold 175000 |
| Bucket | Orchestrator > folder > Storage Buckets > MotorInsuranceClaims-Documents | A file per upload, each with a unique prefix |

## 2. Intake App
Open `https://<org>.uipath.host/<slug>` and sign in.
1. **Workspace line:** the top shows "Storing claims in folder ...". No dropdown means one workspace was found.
2. **Required fields:** try Submit with a document slot empty. It should tell you which required documents are missing.
3. **Remove button:** pick a file, press Remove next to it; the slot returns to "No file chosen".
4. **Submit:** a message gives the claim number (next CLM-n). Check the row and the bucket (section 1).
5. **Add document:** open Add document, choose the claim, attach a file. On the row, `ReceivedDocumentReference` is set, `CustomerInformationStatus = Received`, `CustomerResponseDate` is today, and the file name is appended to `DocumentReferences`.

## 3. Python functions

### ValidatePolicy
| Input | Expected output |
|---|---|
| `{"PolicyNumber":"POL-982341","VehicleRegistration":"KA01AB1234","IncidentDate":"2026-09-28"}` | `PolicyValid: true`, "Policy active, vehicle matches, incident within coverage period." |
| `{"PolicyNumber":"POL-000001","VehicleRegistration":"KA02XY9999","IncidentDate":"2026-09-30"}` | `PolicyValid: false`, reason "Policy status is Expired; Incident date is outside the coverage period" (every failed check is listed) |
| `{"PolicyNumber":"POL-982341","VehicleRegistration":"KA99ZZ0000","IncidentDate":"2026-09-28"}` | false, "Vehicle registration does not match the policy" |
| `{"PolicyNumber":"POL-982341","VehicleRegistration":"KA01AB1234","IncidentDate":"2027-06-01"}` | false, "Incident date is outside the coverage period" |
| `{"PolicyNumber":"POL-NOPE","VehicleRegistration":"X","IncidentDate":"2026-09-28"}` | false, "Policy not found" |

### GetClaimHistory
| Input | Expected |
|---|---|
| `{"PolicyNumber":"POL-982341"}` | PriorClaimCount 0, RecentSimilarClaimCount 0, note "No prior claims identified." |
| `{"PolicyNumber":"POL-551209"}` | 3, 2, LastClaimDate 2026-08-16, the three-claims note |
| `{"PolicyNumber":"POL-NOPE"}` | zeros, note "No claim history record found for this policy." |
| `{"PolicyNumber":""}` | `error_type: NO_POLICY_NUMBER` |

### CalculateSettlement
| Input | Expected |
|---|---|
| `{"PolicyNumber":"POL-982341","ClaimAmount":185000,"DamageEstimate":172400}` | SettlementAmount **162400**, SeniorApprovalRequired false |
| `{"PolicyNumber":"POL-551209","ClaimAmount":240000,"DamageEstimate":240000}` | **230000**, SeniorApprovalRequired **true** |
| `{"PolicyNumber":"POL-764512","ClaimAmount":98000,"DamageEstimate":0}` | 0, false (no estimate, nothing to pay) |
| `{"PolicyNumber":"POL-982341","ClaimAmount":5000,"DamageEstimate":5000}` | 0 (deductible exceeds the loss) |
| Change the asset ClaimsDeductible to 20000 and rerun the first test | **152400**. This proves the value comes from the asset. Set it back to 10000. |
| `{"PolicyNumber":"POL-NOPE","ClaimAmount":1,"DamageEstimate":1}` | `error_type: POLICY_NOT_FOUND` |

### ProcessSettlement (this one writes data)
| Input | Expected |
|---|---|
| Arjun, no decision: `{"ClaimId":"CLM-1003","CustomerName":"Arjun Mehta","PolicyNumber":"POL-551209","SettlementAmount":230000,"SeniorApprovalRequired":true,"SeniorApprovalDecision":""}` | `error_type: APPROVAL_REQUIRED`, nothing paid, no register row. **Safe to run any time.** |
| Same with `"SeniorApprovalDecision":"Rejected"` | APPROVAL_REQUIRED again |
| Same with `"SeniorApprovalDecision":"Approved"` | Paid, `PAY-CLM-1003`, **one row is written to SettlementRegister** |
| Rahul with `SeniorApprovalRequired:false` | Paid, `PAY-CLM-1001`, one row written |

Warning: a paid result creates a real register row. Run paid tests only on a claim you intend to settle, or you will have an extra row to delete.

### FetchClaimDocumentText
Copy the claim's `DocumentReferences` value from its row.
| Input | Expected |
|---|---|
| `{"document_references":"<value from CLM-1001>"}` | `document_count` 7, `combined_text` with seven `=== FILE: ... ===` sections containing the text of each PDF, `failed_files` empty |
| `{"document_references":"<one real name>,missing.pdf"}` | document_count 1, `failed_files` names missing.pdf |
| `{"document_references":""}` | `error_type: NO_DOCUMENTS` |

## 4. API workflows

| Workflow | Input | Expected |
|---|---|---|
| AssessDamage | `{"ExtractedRepairEstimate":172400}` | DamageEstimate 172400 |
| AssessDamage | `{"ExtractedRepairEstimate":0}` | 0 |
| GenerateClaimPacket | `{"ClaimId":"CLM-1001"}` | `PACKET-CLM-1001` |
| CreateCustomerNotification | `{"ClaimId":"CLM-1001","CustomerName":"Rahul Sharma","SettlementStatus":"Paid","FraudInvestigationResult":"","SettlementAmount":162400}` | ClaimOutcome Settled, text "...settled for INR 162400." |
| CreateCustomerNotification | `{"ClaimId":"CLM-1003","CustomerName":"Arjun Mehta","SettlementStatus":"","FraudInvestigationResult":"Confirmed","SettlementAmount":230000}` | FraudRejected |
| CreateCustomerNotification | `{"ClaimId":"CLM-1002","CustomerName":"Priya Nair","SettlementStatus":"","FraudInvestigationResult":"","SettlementAmount":0}` | Denied |

## 5. Agents
Agents use the model, so wording can vary. Judge the fields, not the sentences. Each run uses model quota.

### ClaimDocumentIntelligence
Input: `{"ClaimId":"CLM-1001","DocumentReferences":"<value from the row>"}`
| Claim | Expected |
|---|---|
| CLM-1001 Rahul | DocumentsComplete true, 7 document types, ExtractedRepairEstimate 172400, status Complete, no inconsistencies |
| CLM-1002 Priya, before the supplemental file | DocumentsComplete false, MissingDocuments "Repair Estimate", ExtractedRepairEstimate 0, status Incomplete |
| CLM-1002 after Add document | Complete, estimate 94600 |
| CLM-1003 Arjun | All 7 present, status Inconsistent, four conflicts: incident date 27 vs 25 Sep, high-speed collision vs parking scrape, evidence photos vs claim, estimate vs evidence |
Also check ExtractedCustomerName, ExtractedPolicyNumber, ExtractedVehicleRegistration and ExtractedIncidentDate match the claim.

### FraudRiskAssessment
Input needs ClaimId, PolicyNumber, ClaimAmount, IncidentDate, IncidentDescription, ExtractedRepairEstimate, DocumentInconsistencies (copy these from the row).
| Claim | Expected |
|---|---|
| Rahul | Score under 30, Low, FraudFlag false |
| Priya (no estimate) | Medium (we saw 62), FraudFlag false |
| Priya (with estimate) | Low (we saw 12) |
| Arjun | Score 70+ (we saw 96), High, FraudFlag true |
Acceptable score drift is a few points. A change of band for the same input is a problem.

## 6. Human task apps
These cannot be started from the command line. A task is created by the case when it reaches the human step, or by a test task you create in Action Center. Test each when the case exists:
1. The task appears in Action Center with the right title and assignee.
2. The details are shown and read-only (the inputs list in the Component Guide).
3. **AdjusterReview:** Reject and RequestInformation stay disabled until you type a comment; Approve works without one. After completing, `Decision` equals the button name.
4. **FraudInvestigation:** both buttons need a comment. **SeniorApproval:** Rejected needs a comment. **RequestCustomerInformation:** one button, no comment.
5. Dark mode toggle works; a completed task opens read-only.
6. After completion, the case variable holds the outcome and the case moves to the next stage.

## 7. End-to-end acceptance (the three claims)
| Claim | Path | Expected end state |
|---|---|---|
| CLM-1001 Rahul | Intake, Assessment, Review (Approve), Settlement, Closure | Paid 162400, `PAY-CLM-1001`, ClaimOutcome Settled |
| CLM-1002 Priya | Assessment finds missing estimate, Review RequestInformation, Pending Customer, Add document, back to Assessment | Documents complete, settlement 84600, Paid, Settled |
| CLM-1003 Arjun | Assessment flags High fraud, Fraud Investigation | Confirmed gives FraudRejected, nothing paid. Cleared goes on to Settlement, senior approval required (230000), Approved gives Paid |

## 8. What to do when a test fails
| Symptom | Likely cause |
|---|---|
| Job Faulted | Open the job's logs. For agents: model quota or a tool call failing |
| `error_type` filled | Read `error_message`; usually missing data (policy, entity, bucket file) |
| A value is 0 where money is expected | The asset is unreadable or the estimate is 0 |
| A processes list is empty | The deployment is not Active |
| Wrong folder data | Several folders hold the same entities; keep one workspace |
