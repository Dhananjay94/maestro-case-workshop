# Starter solution

Two files, no installs.

| File | What it is |
|---|---|
| `MotorClaimsWorkshop_Setup.uis` | **Import this in Studio Web, then run it.** One project, `SetupWorkshop`. It prepares your account and puts the workshop solution into your Studio Web |
| `MotorClaims_Workshop.uis` | The workshop solution itself (`MotorInsuranceClaimManagement`: workers, Intake App, empty `MyClaimsCase`, example cases `1_` to `5_`). Setup imports it for you; this copy is for reference |

## Run Setup
1. Studio Web > **Import** > choose `MotorClaimsWorkshop_Setup.uis`.
2. Open **SetupWorkshop**, press **Debug**, set **Action** = `InstallWorkshop`, leave the rest empty, and wait for **Done**.

Other actions: `Status` (shows how far Setup got), `LoadData` (reload the demo policies), `RegisterClaim` with `Customer` = Rahul, Priya or Arjun (adds a test claim). Optional input `DeploymentName` if the default name `ClaimsSolution` is blocked.

Full steps: section 3 of `../Participant_Build_Guide.md`.

## Rebuild these files
`python Build/tools/build_solutions.py Build/_backups/Rv25/S <output folder>` produces both. The Setup function source is in `Build/WorkshopSetup/SetupWorkshop`.
