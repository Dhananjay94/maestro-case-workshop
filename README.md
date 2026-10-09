# Motor Insurance Claims: build a Maestro case

A hands-on workshop. You build a UiPath Maestro **case** that runs a motor insurance claim from registration to payment (or denial), using workers that are already built: AI agents read the documents, code checks the rules, and people decide only when they must.

You need **only a UiPath Community account**. Nothing to install.

## Start here

Read the guide as a web page: **https://dhananjay94.github.io/maestro-case-workshop/**

1. Download [`WorkshopKit/Starter_Solution/MotorClaimsWorkshop_Setup.uis`](WorkshopKit/Starter_Solution/MotorClaimsWorkshop_Setup.uis).
2. In **Studio Web**, use **Import** and choose that file. Open **SetupWorkshop**, press **Debug**, set **Action** to `InstallWorkshop`, and wait for **Done**.
3. Open the solution **MotorInsuranceClaimManagement** that Setup put into your Studio Web, and follow the guide.

Setup creates your environment (tables, bucket, workers, approval screens and the Intake App) in the folder `Shared/ClaimsSolution`, loads demo policies, and imports the workshop solution with Debug already linked to it.

## The guide

| | |
|---|---|
| [`WorkshopKit/Participant_Build_Guide.md`](WorkshopKit/Participant_Build_Guide.md) | The full step-by-step guide (setup, business rules, build, deploy) |
| [`WorkshopKit/Guide_Site/index.html`](WorkshopKit/Guide_Site/index.html) | The same guide as web pages (open it in a browser) |
| [`WorkshopKit/CASE_FLOW_PLAN.md`](WorkshopKit/CASE_FLOW_PLAN.md) | The routing plan: every transition and the rule behind it |
| `WorkshopKit/02_Documents/` | The PDFs for the sample customers |
| `WorkshopKit/01_Data/` | Seed data and the claim values for the test customers |

## What is in here

| Folder | What it is |
|---|---|
| `WorkshopKit/` | Everything a participant uses |
| `WorkshopKit/Starter_Solution/` | `MotorClaimsWorkshop_Setup.uis` (import and run it) and `MotorClaims_Workshop.uis` (the workshop solution, for reference) |
| `Build/WorkshopSetup/` | Source of the Setup function (`SetupWorkshop`, Python) |
| `Build/MotorInsuranceClaimManagement/` | Source of the workers, approval screens and the Intake App |
| `Build/tools/` | The scripts that build the `.uis` files and the web guide |

## Rebuild the files

```
python Build/tools/build_solutions.py <finished solution folder> <output folder>
python Build/tools/build_site.py WorkshopKit/Participant_Build_Guide.md WorkshopKit/Guide_Site
```

The finished case itself lives in Studio Web; the build script prunes it into the empty `MyClaimsCase` and the example cases.

## If something goes wrong

Run **SetupWorkshop** with **Action** = `Status` to see how far Setup got. The guide has a **Start over** section and a troubleshooting table.
