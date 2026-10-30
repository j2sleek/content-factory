# Complete Step-by-Step Deployment Guide

This guide is for deploying the African Startup Funding Pipeline using **GitHub Actions + Apps Script + Google Sheets (100% Free)**. No GCP billing required.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Variables & Secrets](#environment-variables--secrets)
3. [Step 1: Google Sheets Setup](#step-1-google-sheets-setup)
4. [Step 2: Google Apps Script Router Setup](#step-2-google-apps-script-router-setup)
5. [Step 3: GitHub Secrets Configuration](#step-3-github-secrets-configuration)
6. [Step 4: Test the Pipeline](#step-4-test-the-pipeline)
7. [Step 5: Enable Daily Automation](#step-5-enable-daily-automation)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

Before starting, ensure you have:
- [ ] Google Account (for Sheets & Apps Script)
- [ ] GitHub Account with access to [j2sleek/content-factory](https://github.com/j2sleek/content-factory)
- [ ] Repository already cloned/pushed (done)
- [ ] SSH access to GitHub configured (done)

---

## Environment Variables & Secrets

### GitHub Secrets (Required)
Go to: `https://github.com/j2sleek/content-factory/settings/secrets/actions`

| Secret Name | Where to Get | Description |
|-------------|---------------|-------------|
| `APPS_SCRIPT_ROUTER_URL` | Step 2.7 | Apps Script Web App URL (ends with `/exec`) |
| `SHEET_ID` | Step 1.3 | Google Sheet ID from URL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Step 1.6 | Entire contents of service account JSON file |

### GitHub Variables (Optional)
Go to: `https://github.com/j2sleek/content-factory/settings/variables/actions`

| Variable Name | Value | Description |
|---------------|-------|-------------|
| `OPENCODE_MODEL` | `big-pickle` | Model for AI content generation |

### Apps Script Properties (Required)
Go to: Apps Script Project > Project Settings > Script Properties

| Property | Where to Get | Description |
|----------|---------------|-------------|
| `SHEET_ID` | Step 1.3 | Same as GitHub secret |

### Local Environment (.env for testing)
Create `.env` in project root (never commit):

```bash
APPS_SCRIPT_ROUTER_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
SHEET_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

---

## Step 1: Google Sheets Setup

### 1.1 Create Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com)
2. Click `+ Blank` to create new spreadsheet
3. Rename to: `Content Factory - African Funding`

### 1.2 Get Sheet ID
Copy from URL:
```
https://docs.google.com/spreadsheets/d/[SHEET_ID_HERE]/edit
```
Save this ID for later steps.

### 1.3 Create Service Account
1. Go to [console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Select your project (or create one - no billing required for this)
3. Click `+ CREATE SERVICE ACCOUNT`
4. Fill in:
   - Service account name: `content-factory-scraper`
   - Service account ID: (auto-filled)
   - Description: `Service account for Content Factory pipeline`
5. Click `CREATE AND CONTINUE` (skip roles/permissions)
6. Click `DONE`

### 1.4 Download Service Account Key
1. Click on the service account you just created
2. Go to `Keys` tab
3. Click `ADD KEY` > `Create new key`
4. Key type: `JSON`
5. Click `CREATE`
6. Save the downloaded JSON file securely - **NEVER commit this to Git**

### 1.5 Share Sheet with Service Account
1. Open your Google Sheet
2. Click `Share` button (top right)
3. Paste the service account email (e.g., `content-factory-scraper@project-id.iam.gserviceaccount.com`)
4. Set permission to `Editor`
5. Uncheck `Notify people`
6. Click `Share`

---

## Step 2: Google Apps Script Router Setup

### 2.1 Create Apps Script Project
1. Go to [script.google.com](https://script.google.com)
2. Click `+ New project`
3. Rename project to: `Content Factory Router`

### 2.2 Add Code Files
1. Delete default content in `Code.gs`
2. Copy entire contents from `apps-script/Code.gs` in your repo and paste
3. Click gear icon (`Project Settings`) bottom left
4. Check `Show "appsscript.json" manifest file in editor`
5. Go back to editor, click `appsscript.json` tab
6. Replace contents with `apps-script/appsscript.json` from repo

### 2.3 Set Script Properties
1. Go to `Project Settings` > `Script Properties`
2. Click `Add script property`
3. Add:
   - Property: `SHEET_ID`
   - Value: Your Sheet ID from Step 1.2
4. Click `Save script properties`

### 2.4 Deploy as Web App
1. Click `Deploy` > `New deployment`
2. Click gear icon next to "Type" > Select `Web app`
3. Fill in:
   - Description: `Content Factory Pub/Sub Router v1`
   - Execute as: `Me (your-email@gmail.com)`
   - Who has access: `Anyone`
4. Click `Deploy`
5. Click `Authorize access` and complete OAuth flow
6. **Copy the Web app URL** - this is your `APPS_SCRIPT_ROUTER_URL`
   - Format: `https://script.google.com/macros/s/AKfyc.../exec`

### 2.5 Initialize Sheets
1. In Apps Script editor, select function `setupSheets` from dropdown (top toolbar)
2. Click `Run` button
3. Check your Google Sheet - you should now see tabs: `raw_deals`, `normalized_deals`, `shorts_scripts`, `weekly_roundup`, `pipeline_state`, `errors`
4. Check `Executions` tab for any errors

---

## Step 3: GitHub Secrets Configuration

### 3.1 Add Secrets
Go to: `https://github.com/j2sleek/content-factory/settings/secrets/actions`

Click `New repository secret` for each:

| Name | Value |
|------|-------|
| `APPS_SCRIPT_ROUTER_URL` | Web app URL from Step 2.4 |
| `SHEET_ID` | Sheet ID from Step 1.2 |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Open downloaded JSON file, copy entire contents (including `{}`), paste as-is |

### 3.2 Verify
All three secrets should appear in the list (values hidden).

---

## Step 4: Test the Pipeline

### 4.1 Test Scraper Locally (Optional but Recommended)
```bash
cd /home/projects/content-factory
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export APPS_SCRIPT_ROUTER_URL="YOUR_ROUTER_URL"
PYTHONPATH=. python scripts/run_scraper.py
```

Expected output:
- Should scrape deals from RSS feeds
- Should show "Router response: 200"
- Check Google Sheet `raw_deals` tab for new rows
- Check `pipeline_state` tab for log entry

### 4.2 Test via GitHub Actions
1. Go to: `https://github.com/j2sleek/content-factory/actions`
2. Click `Daily Funding Scrape` workflow (left sidebar)
3. Click `Run workflow` dropdown > `Run workflow`
4. Wait 1-2 minutes, click on the running workflow to see logs
5. Check logs for success - should see "Scrape completed" and router response

### 4.3 Verify Data Flow
1. **raw_deals tab** - Should have new rows with deal data
2. **pipeline_state tab** - Should show entries: stage=scraper, status=completed
3. **Apps Script should auto-trigger normalizer** - The router will call normalizer if items exist
4. **normalized_deals tab** - Should populate after normalizer runs
5. **pipeline_state** - Should show normalizer entry

### 4.4 Test Normalizer via GitHub Actions
If normalizer doesn't auto-trigger, run it manually:
1. Go to Actions > Create a quick test or trigger via workflow_dispatch
2. Or run locally: `PYTHONPATH=. python scripts/run_normalizer.py`

### 4.5 Test AI Content Generation
1. Go to Actions > `AI Content Generation` > `Run workflow`
2. Fill inputs if desired (optional)
3. Click `Run workflow`
4. Check `shorts_scripts` and `weekly_roundup` tabs for generated content

---

## Step 5: Enable Daily Automation

The scraper already runs daily at 6:00 AM UTC via the cron schedule in `.github/workflows/scrape-trigger.yml`:
```yaml
schedule:
  - cron: '0 6 * * *'
```

No action needed - it's already configured. GitHub Actions will run it automatically.

To change time, edit the cron expression. Use [crontab.guru](https://crontab.guru) for help.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "APPS_SCRIPT_ROUTER_URL not set" | Missing GitHub secret | Add secret in GitHub Settings > Secrets |
| "Permission denied" on Google Sheets | Service account not shared | Share sheet with service account email as Editor |
| Apps Script "Cannot read properties of null" | SHEET_ID not in Script Properties | Add SHEET_ID to Apps Script Project Settings > Script Properties |
| Router returns 404 | Wrong URL or not deployed | Redeploy Apps Script as Web App, copy correct URL |
| No deals scraped | All feeds filtered out or down | Check logs - our test showed 43 deals, should be fine |
| Normalizer finds 0 items | raw_deals all have status 'normalized' | Reset statuses to 'new' for testing |
| GitHub Actions fails on pip install | Requirements issue | Check requirements.txt, Python version is 3.11 |

---

## Monitoring & Maintenance

### Daily Checks
- Check `pipeline_state` tab for errors
- Check GitHub Actions runs (should show daily success)
- Review `shorts_scripts` for generated content

### Weekly Checks
- Review `weekly_roundup` tab
- Check for failed workflows in GitHub Actions
- Monitor sheet size (Google Sheets has 10M cell limit, more than enough)

### Tips
- **Proxy not needed**: We tested - RSS scraping works fine from GitHub Actions IPs
- **Costs**: Everything is free (GitHub Actions 2000 min/month, Google Sheets free, Apps Script free)
- **Voiceover ready**: All scripts in `shorts_scripts` have `Voiceover Text`, `Duration (sec)`, `Visual Cues` fields
- **Idempotency**: Deduplication by ID prevents duplicates
- **Chaining**: Apps Script ensures each stage triggers only after previous completes

---

## Quick Reference

**Files Modified/Created:**
- `scripts/run_scraper.py` - GitHub Actions scraper runner
- `scripts/run_normalizer.py` - Production normalizer with Sheets integration
- `.github/workflows/scrape-trigger.yml` - Updated to run scraper directly
- `apps-script/Code.gs` - Fixed setupSheets to use properties

**Test Commands:**
```bash
# Local test scraper
PYTHONPATH=. APPS_SCRIPT_ROUTER_URL=YOUR_URL python scripts/run_scraper.py

# Local test normalizer
PYTHONPATH=. APPS_SCRIPT_ROUTER_URL=YOUR_URL SHEET_ID=YOUR_ID GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json python scripts/run_normalizer.py
``` 

All code is pushed to GitHub. Follow steps in order for successful deployment.