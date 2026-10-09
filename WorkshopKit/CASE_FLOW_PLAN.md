# Case flow plan: what flows where, then the rules

This plan is the single source of truth. The current Studio Web draft was checked against it rule by rule and matches. If you change a rule, change this plan first.

## 1. Principles

1. **Primary stages are the normal road**: Intake, Assessment, Review, Settlement, Closure. A primary stage finishes only on its *completion exit*.
2. **A detour is two matching halves.** The origin stage has a *divert exit* (selected tasks completed, Marks stage complete off, Exit to stage = the secondary stage). The secondary stage has an entry rule *Selected stage exited* for that origin with the same condition.
3. **Completion exit is the exact opposite of the diversions**, so exactly one of them can fire. Two firing means both stages start; none firing means the case hangs.
4. **Secondary stage entry rule type is *Selected stage exited* when the origin leaves with a divert exit, and *Selected stage completed* when the origin leaves through a completion exit (only Fraud Investigation Confirmed).** In this engine a stage that completes is not counted as exited. Never *Ad hoc* (tasks only) and never *Case entered* with a condition (checked once at case start).
5. **Rules read case variables written by task outputs** (`vars.<name>`), never `vars.response` (the trigger snapshot).
6. **The ways a stage returns:** Pending Customer and Fraud *Cleared* use *Return to origin* (origin runs again, now with the new data). Denied ends the case.

## 2. Data: who writes it, who reads it

| Variable | Written by (task) | Values | Read by (rule) |
|---|---|---|---|
| `documentIngestionStatus` | ClaimDocumentIntelligence | Complete / Inconsistent / Incomplete | Intake exits |
| `policyValid, policyValidationReason` | ValidatePolicy | true/false, text (always filled once it ran) | Intake exits, Denied/Pending entry |
| `fraudFlag` | FraudRiskAssessment | true/false | Assessment exits, Fraud entry |
| `fraudResult` | FraudInvestigation output `InvestigationResult` | Cleared / Confirmed | Assessment exit, Fraud exits, Denied entry |
| `decision` | AdjusterReview | Approve / Reject / RequestInformation | Review exits, Settlement entry |
| `seniorApprovalRequired` | CalculateSettlement | true/false | SeniorApproval and ProcessSettlement task rules |
| `decision2` | SeniorApproval | Approved / Rejected | ProcessSettlement task rule, Settlement divert |
| `settlementStatus` | ProcessSettlement | Paid | Settlement completion |

## 3. Every transition

| # | From | Decided by | Condition | Goes to | Comes back |
|---|---|---|---|---|---|
| 1 | Intake | ValidatePolicy | `!!vars.policyValidationReason && vars.policyValid === false` | Denied | ends case |
| 2 | Intake | ClaimDocumentIntelligence + ValidatePolicy | `vars.documentIngestionStatus === 'Incomplete' && vars.policyValid === true` | Pending Customer | return to Intake |
| 3 | Assessment | FraudRiskAssessment + AssessDamage | `vars.fraudFlag === true && !vars.fraudResult` | Fraud Investigation | Cleared: return to Assessment |
| 4 | Review | AdjusterReview | `vars.decision === 'Reject'` | Denied | ends case |
| 5 | Review | AdjusterReview | `vars.decision === 'RequestInformation'` | Pending Customer | return to Review |
| 6 | Settlement | SeniorApproval | `vars.decision2 === 'Rejected'` | Denied | ends case |
| 7 | Fraud Investigation | FraudInvestigation | `vars.fraudResult === 'Confirmed'` | Denied (entry rule is *Selected stage completed*, because this exit completes the stage) | ends case |

Normal path: Intake > Assessment > Review > Settlement > Closure > case complete.

## 4. Rule register

### Primary stage entry
| Stage | Rule | Condition |
|---|---|---|
| Intake | Case entered | none |
| Assessment | selected-stage-completed: Intake | none |
| Review | selected-stage-completed: Assessment | none |
| Settlement | selected-stage-completed: Review | `vars.decision === 'Approve'` |
| Closure | selected-stage-completed: Settlement | none |

### Primary stage completion exit (marks stage complete, required tasks completed)
| Stage | Condition |
|---|---|
| Intake | `(vars.documentIngestionStatus === 'Complete' || vars.documentIngestionStatus === 'Inconsistent') && vars.policyValid === true` |
| Assessment | `!(vars.fraudFlag === true && !vars.fraudResult)` |
| Review | `vars.decision === 'Approve'` |
| Settlement | `vars.settlementStatus === 'Paid'` |
| Closure | none (all tasks done) |

### Divert exits (origin side) and secondary entries (target side)
One row in section 3 = one divert exit on the origin and one *Selected stage exited* entry on the target, Interrupting on, same condition.

### Secondary stage exits
| Stage | Exit | Condition |
|---|---|---|
| Fraud Investigation | Return to origin | `vars.fraudResult === 'Cleared'` |
| Fraud Investigation | Exit | `vars.fraudResult === 'Confirmed'` |
| Pending Customer | Return to origin | required task done (RequestCustomerInformation) |
| Denied | Exit | notification sent; case exit rule *Claim denied and case closed* ends the case |

### Case exit rules
1. *All required stages completed* (normal finish).
2. *Claim denied and case closed*: Denied completed.

## 5. Test matrix (run one claim at a time; expected stage trail)

| # | Claim / choices | Expected trail |
|---|---|---|
| T1 | Rahul, adjuster Approve | Intake, Assessment, Review, Settlement (no senior approval), Closure, complete |
| T2 | Rahul, adjuster Reject | Intake, Assessment, Review, Denied, complete |
| T3 | Rahul, adjuster RequestInformation, then Approve | Review, Pending Customer, Review again, Settlement, Closure |
| T4 | Priya (incomplete documents), complete the customer request | Intake, Pending Customer, Intake again, Assessment, ... |
| T5 | Arjun, fraud Cleared, adjuster Approve, senior Approved | Assessment, Fraud, Assessment again, Review, Settlement + SeniorApproval, Closure |
| T6 | Arjun, fraud Confirmed | Assessment, Fraud, Denied, complete |
| T7 | Arjun, fraud Cleared, adjuster Approve, senior Rejected | ... Settlement, Denied, complete |
| T8 | Claim with an invalid policy (create it in the Intake app with an unknown policy number) | Intake, Denied, complete |

## 6. Known unknowns (watch for these)

1. **Stale values on return.** After Pending Customer or Fraud Cleared, the origin stage runs again but old variable values are still set. If a returned stage immediately diverts again without waiting for its task, tell me; the fix is a reset step or a different return exit.
2. **Assessment runs twice** after Fraud Cleared (two more agent calls).
3. **Pending Customer is completed by an operator** after the customer replies (documented in the guide); it does not auto-detect new documents.
4. **T7 and T8 need data/choices** that have not been exercised yet (senior rejection; an invalid-policy claim).
