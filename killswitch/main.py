"""
killswitch/main.py
------------------
WHY THIS FILE EXISTS:
    The ₹50 budget only sends emails - it does not stop spending. This small cloud function is the
    automatic "kill switch": Google Cloud Billing sends the budget's status to a Pub/Sub topic
    (a mailbox for programs) several times a day; this function reads every message and, if the
    money spent this month is MORE than the budget, it removes billing from the project.
    Without billing, Google stops the project's paid services - so the bill cannot keep growing.

    Based on Google's official guide "Disable billing usage with notifications".

SAFETY SWITCH:
    The environment variable SIMULATE=true makes the function only WRITE IN THE LOG what it would
    do. We test with SIMULATE=true first, then switch it to false.

TO TURN THINGS BACK ON after it fired (once you know why the cost went up):
    gcloud billing projects link fridgechef-56971 --billing-account=0186B2-561432-FDA3ED
"""

import base64                                     # Pub/Sub message bodies arrive base64-encoded
import json                                       # ...and contain JSON text
import os                                         # read settings from environment variables

import functions_framework                         # Google's library that turns a function into a cloud function
from google.cloud import billing_v1                # Google's library for the Cloud Billing API

PROJECT_ID = os.environ.get("TARGET_PROJECT_ID", "fridgechef-56971")    # the project to protect
PROJECT_NAME = f"projects/{PROJECT_ID}"                                  # the API's name for it
SIMULATE = os.environ.get("SIMULATE", "true").lower() != "false"        # anything but "false" = only pretend

billing_client = billing_v1.CloudBillingClient()   # created once, reused for every message


@functions_framework.cloud_event                    # "call this for every message on the trigger topic"
def stop_billing(cloud_event):
    """Read one budget message; disable billing if this month's cost is over the budget."""
    raw = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")   # bytes -> text
    budget = json.loads(raw)                        # text -> dict, e.g. {"costAmount": 12.3, ...}
    cost = float(budget["costAmount"])              # money spent so far in this budget period
    limit = float(budget["budgetAmount"])           # the budget, e.g. 50 (rupees)
    print(f"Budget check: cost {cost} of budget {limit} {budget.get('currencyCode', '')}")   # goes to the logs

    if cost <= limit:                               # still within budget -> nothing to do
        print("Within budget - no action.")
        return

    info = billing_client.get_project_billing_info(name=PROJECT_NAME)   # is billing still on?
    if not info.billing_enabled:                    # already switched off earlier -> nothing to do
        print(f"Billing is already disabled for {PROJECT_ID}.")
        return

    if SIMULATE:                                    # test mode: only say what would happen
        print(f"SIMULATION: cost {cost} > budget {limit} -> would now disable billing for {PROJECT_ID}.")
        return

    # Real mode: an empty billing account name = "remove billing from this project".
    billing_client.update_project_billing_info(
        name=PROJECT_NAME,
        project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
    )
    print(f"Cost {cost} exceeded budget {limit}: billing DISABLED for {PROJECT_ID}.")
