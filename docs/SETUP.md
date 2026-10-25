# Setup Guide - Content Factory Pipeline

Complete step-by-step guide to deploy the entire cloud-first pipeline.

## Prerequisites
- Google Cloud Platform account (free tier)
- GitHub account with repo connected via SSH
- Google account for Sheets & Apps Script
- Render account (optional, for remote opencode)

## Step 1: Google Sheets Setup
1. Create a new Google Sheet
2. Name it "Content Factory - African Funding"
3. Copy the Sheet ID from URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`
4. Create service account in Google Cloud Console
5. Download service account JSON key
6. Share the sheet with service account email (Editor access)

## Step 2: Google Apps Script Router
1. Go to [script.google.com](https://script.google.com)
2. Create new project
3. Copy contents of `apps-script/Code.gs` to Code.gs
4. Copy `apps-script/appsscript.json` to Project Settings > Show appsscript.json
5. Set Script Properties:
   - `SHEET_ID`: Your Google Sheet ID
   - `SCRAPER_WEBHOOK_URL`: Cloud Function URL (set later)
   - `NORMALIZER_WEBHOOK_URL`: Normalizer CF URL
   - `OPENCODE_TRIGGER_URL`: GitHub Actions dispatch URL or Render URL
6. Deploy as Web App:
   - Execute as: Me
   - Who has access: Anyone
7. Copy the Web App URL - this is your `APPS_SCRIPT_ROUTER_URL`
8. Run `setupSheets()` function once

## Step 3: Google Cloud Functions
1. Install [gcloud CLI](https://cloud.google.com/sdk/docs/install)
2. Create/select GCP project
3. Enable Cloud Functions, Cloud Build APIs
4. Deploy scraper:
```bash
cd functions/scraper
gcloud functions deploy scraper \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point scrape_handler \
  --set-env-vars APPS_SCRIPT_ROUTER_URL=[ROUTER_URL] \
  --region us-central1
```
5. Deploy normalizer similarly
6. Copy function URLs

## Step 4: Google Cloud Scheduler
1. Go to Cloud Scheduler
2. Create job:
   - Name: `daily-funding-scrape`
   - Frequency: `0 6 * * *` (6 AM UTC)
   - Target: HTTP
   - URL: [Scraper CF URL]
   - HTTP method: POST
   - Body: `{"triggered_by": "cloud_scheduler"}`

## Step 5: GitHub Setup
1. Add secrets to GitHub repo (Settings > Secrets and variables > Actions):
   - `SCRAPER_CF_URL`
   - `SHEET_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON` (entire JSON content)
   - `OPENCODE_MODEL` (optional, defaults to big-pickle)

2. Push code to GitHub via SSH (already configured)

## Step 6: Test the Pipeline
1. Manually trigger scraper CF or run `testScraper()` in Apps Script
2. Check Google Sheet for data in `raw_deals`
3. Monitor `pipeline_state` tab
4. Trigger AI generation via GitHub Actions workflow_dispatch

## Environment Variables Summary

### Cloud Functions
- `APPS_SCRIPT_ROUTER_URL` - Apps Script web app URL

### GitHub Actions
- `SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SCRAPER_CF_URL`

### Apps Script Properties
- `SHEET_ID`
- `SCRAPER_WEBHOOK_URL`
- `NORMALIZER_WEBHOOK_URL`
- `OPENCODE_TRIGGER_URL`

## Troubleshooting
- Check Cloud Function logs in GCP Console
- Check Apps Script Executions log
- Check GitHub Actions logs
- Verify service account has access to sheet
- Check pipeline_state for errors

## Voiceover Readiness
All generated scripts are optimized for:
- AI voice (natural phrasing, pauses)
- Human voiceover (conversational, short sentences)
- Numbers written for speech
- Visual cues included
- Proper pacing markers
