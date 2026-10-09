# How to open the Intake App after deploying (participant guide)

The Intake App is a Coded Web App. UiPath Community has no "Apps" page that lists it and no Open button on the solution page. You open it by its web address.

## 1. Check it is deployed
Orchestrator > **Solutions** > **Deployments** > click your deployment > **Resources** tab. Under "Others" you should see **MotorInsuranceClaim_Intake - App (Coded App)** and the deployment status **Active**. If the status says "Ready to activate", activate it first (Orchestrator > Solutions > Deployments > your deployment > Activate).

## 2. Build the address
```
https://<your-org-name>.uipath.host/<your-app-slug>
```
- **your-org-name**: the organization name in your cloud address (`cloud.uipath.com/<org>/...`). Write underscores as hyphens. Example: org `dj_personal` gives `dj-personal`.
- **your-app-slug**: the routing name you set when deploying (the package default is `claims-intake`; the facilitator's first deployment used `default-app`).

Facilitator example: https://dj-personal.uipath.host/default-app

## 3. Open it and sign in
Open the address, press **Sign in with UiPath**, and sign in with the account you deployed with. The app finds your claims workspace automatically when only one exists. If a dropdown appears, pick the workspace that ends in your deployment folder name.

## 4. One slug per organization
App slugs are unique across the whole organization. If two people deploy into the same org with `default-app`, the second deploy fails. Give each deployment its own slug in the deploy config before running `deploy run`:
```
uip solution deploy config set config.json MotorInsuranceClaim_Intake routingName <your-unique-slug>
```
Use something like `claims-<yourname>`.

## 5. Confirm which app owns a slug
```
uip codedapp validate --path-name <slug>
```
`Available: false` plus `OccupiedBy` shows which app and folder holds it.

## Known limits (be honest with participants)
- The Apps product page is blank on this Community tenant, so there is no app tile. The address above is the only way in.
- The sign-in uses the External Application client id baked into the solution. A participant in a different organization needs their own External Application (confidential, scopes listed in the app's `uipath.json`) and must set its client id in the deploy config:
  `uip solution deploy config set config.json MotorInsuranceClaim_Intake externalClientId <their-client-id>`
  and register `https://<their-org>.uipath.host/<their-slug>` as a redirect URL on it. This path has not been tested outside the facilitator's organization.
