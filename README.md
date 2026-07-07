# web_scraper_FA

Automated daily revenue tracker. A scheduled headless browser logs into a creator payments dashboard, scrapes wallet balances, cleans the values, and appends them to a Google Sheet — producing a clean daily time series of revenue metrics with zero manual effort.

Built to answer a simple problem: the platform displays current balances but keeps no history. Without a record of levels over time, there's no way to compute flows — daily revenue, growth rates, or payout timing. This script constructs that dataset.

## How it works

Every day at midnight UTC, a GitHub Actions runner:

1. **Launches a headless Chromium browser** (Playwright) and navigates to the platform login page
2. **Authenticates** — types the phone number character-by-character to trigger the site's input validation, then fills a segmented OTP field cell-by-cell
3. **Scrapes** the two wallet balance elements from the dashboard once the page reaches network idle
4. **Cleans** the raw strings — strips currency symbols (₦), thousands separators, and whitespace — and casts to floats
5. **Appends a timestamped row** to a Google Sheet via the Sheets API (`gspread` + a service account), where the data feeds downstream analysis

The result is a panel of `(timestamp, wallet_1, wallet_2)` observations, one row per day. Daily flows are then just first differences.

## Design notes

- **Credentials never touch the code.** Login parameters and API credentials are injected at runtime as environment variables from GitHub's encrypted secret store. The Google service account key exists only inside the ephemeral Actions runner and is destroyed when the run ends.
- **Failures are observable.** Each stage (login, OTP, scrape, write) is isolated with its own error handling. On failure, the script captures a screenshot of the page state, which the workflow uploads as a debug artifact — so a broken selector or changed page layout is diagnosable from the run log without rerunning locally.
- **Defensive parsing.** If the balance string fails to parse as a float, the raw value is written instead of being silently dropped — bad data is visible in the sheet rather than lost.
- **Human-like interaction.** Typing with per-keystroke delays and a realistic user agent, because the site's front-end logic (and bot detection) doesn't respond to programmatic `fill` events on some fields.

## Stack

| Component | Tool |
|---|---|
| Browser automation | Playwright (async, headless Chromium) |
| Scheduling / compute | GitHub Actions (cron) |
| Data store | Google Sheets via `gspread` |
| Auth to Google | Service account (JSON key via secret store) |

## Files

- `pullscript.py` — the scraper
- `.github/workflows/daily.yml` — the schedule and runtime environment
- `requirements.txt` — Python dependencies

## Running it yourself

Fork, then set five repository secrets under **Settings → Secrets and variables → Actions**: `PHONE_NUM`, `STATIC_OTP`, `SHEET_NAME`, `LOGIN_URL`, and `GOOGLE_CREDS_JSON` (the full service-account JSON). Share the target sheet with the service account's email. Trigger manually from the Actions tab or wait for the nightly run.
