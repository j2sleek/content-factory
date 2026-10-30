# Content Factory - African Startup Funding Pipeline

Cloud-first, event-driven pipeline to scrape African startup funding news, normalize it, and generate engaging short-form scripts + weekly roundups using AI. Built for voiceover-readiness. **100% Free** using GitHub Actions + Apps Script + Google Sheets.

## Architecture

```
[GitHub Actions Cron (6AM UTC)] -> [Scraper Script]
                                        |-- webhook --> [Apps Script Pub/Sub Router]
                                                          |-- writes to Google Sheets (raw_deals)
                                                          |-- triggers next stage
                                                          v
                                                    [Normalizer Script]
                                                          |-- writes to Google Sheets (normalized_deals)
                                                          |-- webhook --> [Router]
                                                          v
                                                    [AI Content Generator (GitHub Actions)]
                                                          |-- pulls from Sheets, generates voiceover-ready scripts
                                                          v
                                                    [Google Sheets (shorts_scripts, weekly_roundup)]
```

## Stages
1. **Scraper** - RSS-first with BeautifulSoup fallback, runs daily via GitHub Actions cron
2. **Apps Script Router** - Webhook orchestrator, ensures stage chaining (with direct Sheets fallback)
3. **Normalizer** - Extracts amounts, countries, sectors, rounds, filters funding deals only, deduplicates
4. **AI Generator** - Generates voiceover-ready shorts scripts and weekly roundups using enriched prompts
5. **Storage** - Google Sheets as single source of truth

## Quick Start
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for full deployment instructions.
