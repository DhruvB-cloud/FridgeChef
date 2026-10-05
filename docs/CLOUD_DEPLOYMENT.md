# Putting the FridgeChef server in the cloud (Google Cloud Run)

While you develop, the recipe server runs on your own PC. When you start the desktop app, it now starts the server for you (`main.py → _ensure_local_server`). Once you put the app on GitHub, publish it in an app store or send the APK to a friend, their phones can't reach your PC. The server then has to run on the internet. This guide puts it on **Google Cloud Run** step by step.

---

## 1. Why Google Cloud Run?

| Option | Monthly cost for an app like this | Problem |
|---|---|---|
| **Google Cloud Run** ✅ | **$0** inside the free tier: 2 million requests, 180,000 vCPU-seconds and 360,000 GiB-seconds per month | Needs a payment card to open the account; the first request after a quiet period takes ~1–3 s while it wakes up |
| PythonAnywhere (free) | $0 | Since Jan 2026 a free web app stops after **1 month** unless you log in and click "extend"; paid plans start at $10/month |
| Render (free) | $0 | Sleeps after 15 min without traffic; waking up takes **30–60 s**, so the app would show "Offline" almost every time |
| Fly.io / Railway | ~$2–5+ | No real free tier any more |
| A virtual machine (Oracle/AWS/GCP) | $0–5 | You'd have to maintain a Linux server yourself (updates, security, HTTPS certificates) |

**Why Cloud Run is the best fit:**
- **It costs nothing for this app.** One Recipes-tab request takes a fraction of a second of CPU, so even thousands of users per month stay far inside the free tier.
- **It scales to zero.** When nobody uses the app, nothing runs and nothing is billed. If the app becomes popular, Google starts more copies automatically.
- **HTTPS is included automatically.** Android blocks plain `http://` connections, so this matters.
- **It never needs a manual "extend" click,** and you don't maintain a server.
- **It runs the code you already have.** The repository includes a `Dockerfile`, and Google builds it for you. You don't need Docker on your PC.
- **It has a region in Mumbai (`asia-south1`).** That's close to Indian users and in Google's cheapest price tier.

The free tier is applied as a monthly discount and works in every region. You only pay for usage above it. The settings below also cap the number of running copies at 2, so a bug or a traffic spike can't run up a large bill.

---

## 2. Create your Google Cloud account (one time, ~10 minutes)

1. Open **https://cloud.google.com** and click **Get started for free** (or **Start free**).
2. Sign in with a Google account (Gmail). Use the account you want to own the project.
3. Choose your **country**, accept the terms and click **Continue**.
4. Enter a **payment card**. Google uses it to verify that you're a real person. New customers usually also get free trial credit.
   - During the trial, nothing is charged automatically.
   - When the trial ends, Google asks you to **activate a full (paid) account**. Do this, or Google pauses your server. Activating doesn't cost anything by itself: usage inside the Cloud Run free tier stays free.
5. You land on the **Google Cloud console** (https://console.cloud.google.com).

### 2a. Create a project
A "project" is a folder that holds everything for one app.

1. At the top of the console, click the **project picker** (next to "Google Cloud"), then **New project**.
2. Project name: `fridgechef`. Google shows a **Project ID** underneath, e.g. `fridgechef-471205`. **Write it down**, because you'll need it later.
3. Click **Create** and wait a few seconds. Make sure the new project is selected at the top.

### 2b. Set a budget alert (strongly recommended)
This emails you if costs ever go above the amount you choose.

1. Menu (☰) → **Billing** → **Budgets & alerts** → **Create budget**.
2. Name: `FridgeChef safety net`. Projects: `fridgechef`.
3. Amount: **₹100** (or $1). Keep the alert thresholds at 50%, 90% and 100%.
4. Click **Finish**. A budget only sends warnings; it doesn't stop anything. The `--max-instances 2` setting in step 4 is what limits how much can run.

---

## 3. Install the Google Cloud command-line tool on Windows (one time)

1. Download the installer from **https://cloud.google.com/sdk/docs/install** (Windows → `GoogleCloudSDKInstaller.exe`).
2. Run it with the default options. On the last page, keep **"Run gcloud init"** ticked and click **Finish**.
3. A terminal opens. Follow it (or open a new PowerShell window and run the commands below):

```powershell
gcloud init                                     # opens your browser: log in with the same Google account, then pick the "fridgechef" project
gcloud config set project YOUR_PROJECT_ID       # e.g. fridgechef-471205 - makes every following command use this project
gcloud config set run/region asia-south1        # default region = Mumbai (choose the region closest to your users)
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com   # switch on Cloud Run (runs the server), Cloud Build (builds it) and Artifact Registry (stores the built image)
```

> Other regions close to common users: `asia-south1` (Mumbai), `me-central1` (Doha), `europe-west2` (London), `us-central1` (Iowa). The full list is at https://cloud.google.com/run/docs/locations

---

## 3b. (Optional, skipped for this project) Test the server container locally with Docker

**You don't need this section.** Google's servers build the container during `gcloud run deploy`, so Docker isn't required on your PC. We tried Docker Desktop, but on this laptop its Linux engine reported "no virtualization available", and for a project this small it wasn't worth the 2 GB of disk and RAM, so it was uninstalled. The commands below are kept for later, in case you want to try local container testing on a PC where Docker works.

With Docker you can build and run **exactly the container Cloud Run will run** before uploading anything:

```powershell
cd F:\Projects\FridgeChef                                  # the folder that contains the Dockerfile
docker build -t fridgechef-api .                           # build the container image and name it "fridgechef-api" (first time: a few minutes)
docker run --rm -d -p 8080:8080 --name fridgechef-test fridgechef-api   # start it in the background; --rm = delete it when stopped; -p = make port 8080 reachable from this PC
Invoke-RestMethod http://127.0.0.1:8080/api/health         # ask it "are you alive?" - expect: status ok, recipes 21
docker logs fridgechef-test                                # show what gunicorn printed (useful if something failed)
docker stop fridgechef-test                                # stop the test container (it is deleted automatically because of --rm)
```

If this works on your PC, the same image will work on Cloud Run.

---

## 4. Deploy the server (a few minutes)

Run these commands **from the FridgeChef folder**. The comments explain every line. In PowerShell, a command can be written as a list of arguments (`@(...)`), which lets each line have its own comment.

```powershell
cd F:\Projects\FridgeChef                       # the project folder - it contains the Dockerfile
$deployArgs = @(                                # collect all settings in a list (one per line, so each can be explained)
  "run", "deploy", "fridgechef-api",            # create (or update) a Cloud Run service named "fridgechef-api"
  "--source", ".",                              # upload THIS folder; Google builds it using our Dockerfile
  "--region", "asia-south1",                    # where it runs - Mumbai (same as step 3)
  "--allow-unauthenticated",                    # anyone with the app may call the API (it has no login)
  "--memory", "512Mi",                          # 512 MB of memory per copy - plenty for Flask + 21 recipes
  "--cpu", "1",                                 # one virtual CPU per copy
  "--min-instances", "0",                       # scale to zero when unused -> nothing is billed while idle
  "--max-instances", "2",                       # never more than 2 copies -> caps the cost even with heavy traffic
  "--cpu-boost",                                # extra CPU while starting -> the first request after a quiet time is faster
  "--port", "8080"                              # the port gunicorn listens on inside the container (see Dockerfile)
)                                               # end of the list
gcloud @deployArgs                              # run "gcloud" with every argument from the list above
```

**What happens next:**
1. The first time, gcloud asks: *"Deploying from source requires an Artifact Registry Docker repository… Do you want to continue (Y/n)?"* Type **Y** and press Enter. It creates a storage area for the built server.
2. It uploads the folder (files listed in `.gcloudignore` are skipped) and builds the container, which takes 2–4 minutes.
3. It finishes with a line like this:
   ```
   Service URL: https://fridgechef-api-abc123xyz-el.a.run.app
   ```
   **That's your cloud server address.**

### 4a. Check that it works
Open these addresses in a browser, using your own URL:
- `https://fridgechef-api-abc123xyz-el.a.run.app/` → *FridgeChef API is running. Try /api/health*
- `https://fridgechef-api-abc123xyz-el.a.run.app/api/health` → `{"api_version":1,"recipes":21,"status":"ok"}`

Or from PowerShell:
```powershell
$url = "https://fridgechef-api-abc123xyz-el.a.run.app"      # paste YOUR service URL here
Invoke-RestMethod "$url/api/health"                          # calls the health endpoint and prints the JSON answer
```

---

## 5. Point the app at the cloud server

1. Open `app/config.py` and paste your URL:
   ```python
   CLOUD_SERVER = "https://fridgechef-api-abc123xyz-el.a.run.app"   # your Service URL from step 4 - no "/" at the end
   ```
   `DEFAULT_SERVER` now uses the cloud address automatically, so every **new** install talks to the cloud.
2. **On your own PC/phone,** if you ever typed an address in **Profile → Recipe server**, that saved address still wins. Paste the cloud URL there too, then tap **Test connection**. It should say *Connected – 21 recipes available*.
3. **Rebuild the APK** (`buildozer android debug`) and send it to your friends. Because the address is `https://`, Android allows the connection without any extra settings.
4. **To keep developing locally,** clear `CLOUD_SERVER` again, or set Profile → Recipe server to `http://127.0.0.1:5000`. On a PC the app starts the local server by itself.

---

## 6. Everyday tasks

```powershell
gcloud @deployArgs                                                     # UPDATE: after changing server code or recipes, run step 4 again - same URL, new version
gcloud run services describe fridgechef-api --region asia-south1 --format "value(status.url)"   # FIND URL: prints the service address again if you lost it
gcloud run services logs read fridgechef-api --region asia-south1 --limit 50   # LOGS: the last 50 log lines (errors, requests) of the server
gcloud run revisions list --service fridgechef-api --region asia-south1         # HISTORY: every deployed version ("revision")
gcloud run services delete fridgechef-api --region asia-south1                  # REMOVE: deletes the server completely (stops all costs)
```

### Keep image storage inside the free tier
Every deploy stores a new copy of the built server (about 200 MB) in Artifact Registry. The free storage is about 0.5 GB, so delete old copies now and then:

1. Console → **Artifact Registry** → repository **cloud-run-source-deploy** → **fridgechef-api**.
2. Tick all images **except the newest** → **Delete**.

You can also set this up once so it happens automatically: on the repository page → **Edit** → **Cleanup policies** → *Keep most recent versions: 2*.

---

## 7. What it costs, honestly

| Item | Free each month | This app's typical use |
|---|---|---|
| Requests | 2,000,000 | 1 per Recipes-tab visit (+ a few image downloads, once per phone) |
| CPU time | 180,000 vCPU-seconds | ~0.05–0.2 s per request → about 1 million+ visits before paying |
| Memory | 360,000 GiB-seconds | Well inside the free amount at this usage |
| Data sent out | 1 GB (North America) | Each Recipes answer is ~40 KB, so 1 GB ≈ 25,000 visits; beyond that, about $0.12 per GB |
| Build + image storage | Free allowance | A few builds per month; delete old images (section 6) |

At the scale of you and your friends, the expected bill is **₹0**. The budget alert from step 2b warns you long before anything noticeable is charged.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `PERMISSION_DENIED` / `billing account` during deploy | The project has no billing account linked: Console → Billing → **Link a billing account** |
| The app shows **Offline** but the URL works in a browser | The address in Profile → Recipe server is different, or has a `/` at the end; paste exactly the Service URL |
| The first request after a long pause is slow | The server was asleep (scaled to zero). The app waits up to 8 s (`REQUEST_TIMEOUT_SECONDS` in `app/config.py`). For no waiting at all use `--min-instances 1`, but that is **not free** |
| `Container failed to start` | Run `gcloud run services logs read ...` (section 6). A Python error is usually shown there |
| You changed the recipes but the phone shows old ones | Deploy again (section 6). The phone updates its offline copy the next time the Recipes tab loads from the server |

---

## 9. Which files make the cloud deployment work

| File | Role |
|---|---|
| `Dockerfile` | The recipe for the server's container: Python 3.13, install packages, copy code, start gunicorn |
| `server/requirements.txt` | Packages for the cloud server: Flask, gunicorn, Pillow |
| `server/wsgi.py` | Creates `application` - the object gunicorn serves |
| `server/app.py` | The API itself (same file you run locally) |
| `.gcloudignore` / `.dockerignore` | Files NOT uploaded/copied (your `.venv`, tests, Android build output...) |
| `app/config.py` | `CLOUD_SERVER` - the address the app uses once you've deployed |
