# Content Factory - African Startup Funding Pipeline

Cloud-first, event-driven pipeline to scrape African startup funding news, normalize it, and generate engaging short-form scripts + weekly roundups using AI. Built for voiceover-readiness.

## Architecture

```
[Cloud Scheduler] -> [GCP Cloud Function (Scraper)] 
                            |-- webhook --> [Apps Script Pub/Sub Router]
                                              |-- writes to Google Sheets
                                              |-- triggers next stage
                                              v
                                        [Normalizer CF]
                                              |-- webhook --> [Router]
                                              v
                                        [opencode Trigger (GitHub Actions)]
                                              |-- pulls from Sheets, generates content
                                              v
                                        [Google Sheets (Content Queue)]
```

## Stages
1. **Scraper** - RSS-first with BeautifulSoup fallback, runs on Cloud Scheduler
2. **Apps Script Router** - Pub/Sub webhook orchestrator, ensures stage chaining
3. **Normalizer** - Extracts amounts, countries, sectors, rounds, deduplicates
4. **AI Generator** - opencode via GitHub Actions, creates voiceover-ready scripts
5. **Storage** - Google Sheets as single source of truth

## Quick Start
See [docs/SETUP.md](docs/SETUP.md) for full deployment instructions.
