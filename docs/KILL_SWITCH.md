# The billing kill switch (Google Cloud)

> **Version 4.7.1:** FridgeChef no longer uses a cloud server. The recipe catalogue is a plain file on
> GitHub Pages (see `tools/export_catalog.py` and `.github/workflows/publish-catalog.yml`), and all
> recipe matching happens on the phone. This kill switch stays because it protects the **other**
> services in the same Google Cloud project (for example the HitCounter API).
>
> Account and project details are **not** stored in this public repository. Wherever you see
> `<PROJECT_ID>`, `<BILLING_ACCOUNT_ID>` or `<BUDGET_ID>`, use the real values from the
> [Google Cloud console](https://console.cloud.google.com/).

## What it does

A budget only sends emails; it does not stop spending. The **kill switch** stops spending automatically:
the budget posts its status to a Pub/Sub topic (a mailbox for programs) several times a day, and a small
function (`killswitch/main.py`) **removes billing from the project** as soon as this month's cost is
over the budget. Without billing, Google stops the project's paid services, so the bill cannot keep growing.

## How it was set up

```powershell
gcloud services enable pubsub.googleapis.com cloudfunctions.googleapis.com eventarc.googleapis.com cloudbilling.googleapis.com   # the services it uses
gcloud pubsub topics create billing-alerts                                   # the mailbox
gcloud iam service-accounts create billing-killswitch --display-name "Billing kill switch"   # a robot account used ONLY by the kill switch
$sa = "billing-killswitch@<PROJECT_ID>.iam.gserviceaccount.com"              # its e-mail-style name
gcloud billing accounts add-iam-policy-binding <BILLING_ACCOUNT_ID> --member "serviceAccount:$sa" --role roles/billing.admin   # may change billing
gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$sa" --role roles/billing.projectManager   # may unlink billing from THIS project
gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$sa" --role roles/browser                 # may SEE the project
gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$sa" --role roles/run.invoker             # may receive the mailbox messages
gcloud projects add-iam-policy-binding <PROJECT_ID> --member "serviceAccount:$sa" --role roles/eventarc.eventReceiver  # (same, for the trigger)
gcloud billing budgets update <BUDGET_ID> --billing-account <BILLING_ACCOUNT_ID> --notifications-rule-pubsub-topic projects/<PROJECT_ID>/topics/billing-alerts   # budget -> mailbox
```

The function is deployed with:

```powershell
gcloud functions deploy stop-billing --gen2 --runtime python312 --region asia-south1 --source killswitch --entry-point stop_billing --trigger-topic billing-alerts --service-account $sa --trigger-service-account $sa --set-env-vars SIMULATE=false,TARGET_PROJECT_ID=<PROJECT_ID> --max-instances 1 --memory 256Mi
```

- **Test mode:** `SIMULATE=true` makes it only write "SIMULATION: would disable billing" in its log.
- **Testing in real mode:** only send **under-budget** messages. An over-budget test would really switch billing off.

## If it ever fires

```powershell
gcloud functions logs read stop-billing --region asia-south1 --limit 20   # 1. see what happened (cost vs budget)
# 2. open https://console.cloud.google.com/billing -> Reports to see WHAT cost the money
gcloud billing projects link <PROJECT_ID> --billing-account <BILLING_ACCOUNT_ID>   # 3. switch billing back on
```

**Limitation:** Google updates cost data with a delay of up to several hours, so the spend can go somewhat
over the budget before the switch fires. It turns an *unlimited* risk into a *small* one.

## Retiring the old FridgeChef recipe server (one time)

Older app versions (4.0.0 and 4.7.0) called a Cloud Run service named `fridgechef-api`. After 4.7.1 is
released it can be deleted; those older apps then simply use their saved (offline) recipes.

1. Open [Cloud Run](https://console.cloud.google.com/run) in the console (with the right project selected).
2. Tick **fridgechef-api** (only that one - leave HitCounter alone) and click **Delete**.
