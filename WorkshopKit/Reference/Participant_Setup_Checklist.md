# Participant setup: 5 minutes, one command

Everything is created in **your own UiPath Community account**, in a folder only you can use. Nothing is shared with anyone.

## You need
- A UiPath Community account (you sign in once).
- Node.js 18 or newer (https://nodejs.org).
- The `Starter_Solution` folder from the workshop (it contains `setup.mjs`, the solution `.zip` and a `data` folder).

## Steps
1. Install the UiPath command line tool, once:
   ```
   npm install -g @uipath/cli
   ```
2. Sign in. A browser window opens; sign in with your Community account:
   ```
   uip login
   ```
3. Open a terminal **inside the `Starter_Solution` folder** and run the setup. Pick any short name of your own for `<your-name>` (letters, numbers, dashes):
   ```
   node setup.mjs --slug claims-<your-name>
   ```
   It takes a few minutes. It sets up your sign-in client, installs the solution into your own `Shared/ClaimsSolution` folder, and loads the policy and claim-history data. When it says **DONE** it prints your Intake App address.

## Open the Intake App
Open the address it printed, for example `https://<your-org>.uipath.host/claims-<your-name>`. Press **Sign in with UiPath**, then register a claim and attach the PDFs from the `02_Documents` folder (use the values from `claims_intake_values.csv`).

## Run things in Studio Web
Open your solution in Studio Web and run or debug any function, API workflow or agent. They find the data in your `ClaimsSolution` folder automatically. Leave the optional `DataFolder` input empty. Only if you deploy a second copy will they ask you to fill it in with the folder to use.

## If something goes wrong
| Message | What to do |
|---|---|
| `You are not signed in` | Run `uip login`, then run the setup again. |
| `The slug ... is already used` | Pick a different `--slug` value. |
| `FAILED: ...` | Run the same command again; it skips what is already done. If it fails twice, send the whole message to the facilitator. |
| The Intake App page shows an error after sign-in | Check the address matches the one printed, exactly. |

Run the setup command again at any time. It is safe to repeat, except that it will not redeploy a deployment that already exists: to start over, uninstall the old deployment in Orchestrator > Solutions first.
