import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import requests



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

SCRAPER_API_KEY = os.getenv("SCRAPERAPI_KEY")
if not SCRAPER_API_KEY:
    raise RuntimeError("SCRAPERAPI_KEY environment variable is not set.")

SCRAPER_API_URL = "https://api.scraperapi.com/"
IST = pytz.timezone("Asia/Kolkata")


def fetch_csv(url: str) -> str | None:
    """Fetch a CSV file through ScraperAPI."""

    logging.info("Fetching: %s", url)

    response = requests.get(
        SCRAPER_API_URL,
        params={
            "api_key": SCRAPER_API_KEY,
            "url": url,
            "country_code": "in",
            "device_type": "desktop",
            "keep_headers": "true",
        },
        timeout=30,
    )

    # File not yet available
    if response.status_code == 404:
        logging.info("CSV not found.")
        return None

    response.raise_for_status()

    csv_header = response.text.splitlines()[0].strip().upper()
    logging.info("CSV Header: %s", csv_header)

    if not csv_header.startswith("SYMBOL"):
        raise ValueError("Downloaded file is not a valid NSE securities CSV.")
    return response.text

def save_csv(filename: str, csv_text: str) -> None:
    """Save latest CSV and keep only the newest two files."""

    directory = Path("price_band_data")
    directory.mkdir(exist_ok=True)

    csv_path = directory / f"{filename}.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    logging.info("Saved %s", csv_path)

    # Keep only the latest two CSVs
    csv_files = sorted(
        directory.glob("*.csv"),
        key=lambda f: datetime.strptime(f.stem, "%d%m%Y"),
    )

    while len(csv_files) > 2:
        oldest = csv_files.pop(0)
        logging.info("Deleting %s", oldest.name)
        oldest.unlink()


def main() -> None:
    today = datetime.now(IST)

    for days_back in range(7):
        check_date = today - timedelta(days=days_back)

        # Skip weekends
        if check_date.weekday() >= 5:
            logging.info(
                "Skipping weekend: %s",
                check_date.strftime("%A %d-%m-%Y"),
            )
            continue

        date_str = check_date.strftime("%d%m%Y")

        url = (
            "https://nsearchives.nseindia.com/content/equities/"
            f"sec_list_{date_str}.csv"
        )

        csv_text = fetch_csv(url)

        if csv_text:
            save_csv(date_str, csv_text)
            logging.info("Latest Price Band CSV downloaded successfully.")
            return

    raise RuntimeError("No NSE Price Band CSV found in the last 7 days.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Script failed.")
        raise