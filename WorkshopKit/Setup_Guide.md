# Setup guide: get ready and run Rahul's claim

- **What you will do:** prepare your own UiPath account with one import and one run, configure your Gmail and Data Fabric connections, and run a finished claim case end to end for the customer **Rahul**.
- **What you need:** a UiPath Community account and the file `MotorClaimsWorkshop_Setup.uis` from the workshop folder. Nothing to install on your computer.
- **Time:** about 25 minutes.
- **Where we stop:** after Rahul's claim has run. Building your own case comes next in the workshop, and deploying comes after that.

> Boxes marked **Check** tell you how to know a step worked. Boxes marked **Why** explain the reason. Boxes marked **Stuck?** tell you what to do if it did not.

---

## 1. Import and run Setup (about 5 minutes)

Setup prepares everything the case needs, so you do not have to build any of it.

### 1.1 Import the Setup solution
1. Open **Studio Web** and go to the home page.
2. Use **Import** (next to **Create New**; the exact label can differ).
3. Choose the file `MotorClaimsWorkshop_Setup.uis`.
4. Open the solution **MotorClaimsWorkshop_Setup**. It has one project, **SetupWorkshop**.

### 1.2 Run Setup
1. Open **SetupWorkshop** and press **Debug**. A small form opens.
2. Set **Action** to `InstallWorkshop`. **Leave every other field empty.**
3. Run it, and **wait for the result**. It takes about a minute.

> **Check:** the result ends with **Done** and gives your **Intake App** address, for example `https://<your-organization>.uipath.host/claims-<your-organization>`. Copy it somewhere. You will use it later in the workshop.

> **If the screen looks stuck:** Studio Web sometimes shows only the first lines until the run ends. Open a second Debug of **SetupWorkshop** with **Action** = `Status`. It takes a few seconds and tells you how far Setup got. It ends with **FINISHED** or **NOT FINISHED**.

> **If it says a name cannot be used:** a leftover from an earlier try is in your account. Run Setup again with **DeploymentName** set to another name, for example `ClaimsSolutionB`. Leave the rest as it was.

### 1.3 What Setup just created for you

| What | Where |
|---|---|
| A sign-in client for the approval screens and the Intake App | Your organization |
| The **environment**: the claim tables, the document bucket, the two business-number assets, every worker, the approval screens and the Intake App | Orchestrator folder `Shared/ClaimsSolution` |
| Demo **policies** and **claim history**, with the customer email set to **your own address** | The `PolicyMaster` and `ClaimHistory` tables |
| The workshop solution **MotorInsuranceClaimManagement**, linked to that environment | Your Studio Web |

No claims exist yet. You create one in the next part.

---

## 2. Configure your connections (about 5 minutes)

The case sends real emails through **Gmail** and starts from a row in **Data Fabric**. Both need a connection that belongs to you. You set them up from inside the workshop solution that Setup just put into your Studio Web.

### 2.1 Open the solution and its connections
1. In **Studio Web**, open the solution **MotorInsuranceClaimManagement**.
2. Open the **Connections** item of the solution. It lists the two connections the case needs: **Data Fabric connection** and **Gmail connection**. If a connection is not set up yet, it is marked as needing attention.

### 2.2 Configure the Data Fabric connection
1. Click **Data Fabric connection**.
2. Choose to connect (or add a new connection), and follow the prompt. It uses your UiPath sign-in, so there is nothing to type.

> **Check:** the Data Fabric connection now shows as connected, with no warning.

### 2.3 Configure the Gmail connection
1. Click **Gmail connection**.
2. Choose to connect (or add a new connection). A Google window opens. Choose a Google account **whose inbox you can open**, and allow access.

> **Check:** the Gmail connection now shows as connected, with no warning.

> **Why:** the customer emails in this workshop are sent from your Gmail connection to **your own email address**, so you can see exactly what a customer would receive. You can use any Gmail address you can read.

> **Stuck?** If a connection says **expired** or asks you to sign in again, open it and use **Login** (or **Reconnect**) once more.

---

## 3. Run Rahul's claim

Rahul is the clean case: a valid policy, all seven documents, no fraud signs. You run the **finished** case once, so you see what you are going to build.

### 3.1 Register Rahul's claim
1. Go back to **MotorClaimsWorkshop_Setup > SetupWorkshop** and press **Debug**.
2. Set **Action** to `RegisterClaim` and **Customer** to `Rahul`. Leave the rest empty.
3. Run it.

> **Check:** the result says **CLM-1001 (Rahul Sharma): 7 documents uploaded, claim registered**.

> **Why:** a claim is a row in the `MotorInsuranceClaim` table, plus the customer's documents in the document bucket. The case starts from that row. Normally the Intake App creates it. Here, Setup does it for you.

### 3.2 Open the finished case
1. In Studio Web, open the solution **MotorInsuranceClaimManagement**.
2. In the project list, open **5_Complete**. This is the complete case: Intake, Assessment, Review, Settlement, Closure, plus the exception paths.

### 3.3 Debug it
1. Press **Debug**.
2. When it asks which claim to start with, choose **CLM-1001**.
3. If it asks you to choose a connection, pick the **Data Fabric** and **Gmail** connections you configured in part 2.
4. Let it run. The case moves through its stages by itself. The agents read Rahul's documents, which takes a minute or two.

### 3.4 The one human step
The case stops at **Review** and waits for the adjuster. That is you.
1. Open **Action Center > Tasks**.
2. Open the task **Review the claim and decide**.
3. Read the summary, choose **Approve**, and submit.

The case continues on its own: it calculates the settlement, records the payment, writes the claim packet, and sends the customer a notification.

### 3.5 Check the result
- **In Studio Web:** the case shows every stage completed.
- **In Data Fabric > MotorInsuranceClaim:** the row **CLM-1001** shows the claim status **Closed**, with the settlement amount and a payment reference.
- **In your email inbox:** a customer notification about the settlement.

> **Check:** all three are true. You have now run a complete claim, from registration to payment, with agents, code and one human decision.

> **Stuck?**
> - **Nothing happens, or Debug cannot find the claim:** run Setup with `RegisterClaim` for Rahul again, and then Debug.
> - **The case reports a policy problem:** the policies may not have loaded. Run Setup with **Action** = `LoadData`, then Debug again.
> - **No task appears in Action Center:** wait a minute and refresh the page. The agents take time to read the documents.
> - **The Gmail step fails or the email does not arrive:** check that your Gmail connection is **Enabled** (part 2) and look in the spam folder.
> - **Anything else:** run Setup with **Action** = `Status`, and send the facilitator the full text of what you see.

---

## You are ready

You have a working environment, your own connections, and you have seen a finished case run end to end. Next in the workshop you build your own case in **MyClaimsCase**, starting from the empty trigger, and you can jump in from any of the example cases `1_HappyPath` to `5_Complete`.

**Start over, if you ever need to:** in Studio Web delete the solution **MotorInsuranceClaimManagement**, ask the facilitator to remove the environment, then run Setup again.
