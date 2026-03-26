import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time


BASE_URL = "https://www.parliament.go.ke"
BILLS_URL = f"{BASE_URL}/the-national-assembly/house-business/bills"


class ParliamentScraper:
    def __init__(self, max_retries: int = 3, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay

    # =========================
    # HTTP FETCH WITH RETRIES
    # =========================
    def fetch_page(self, url: str) -> str:
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to fetch {url}: {e}")
                time.sleep(self.delay)

    # =========================
    # MAIN SCRAPER
    # =========================
    def scrape_bills(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Scrape bills with a limit.
        Returns: [{ "title": ..., "pdf_url": ... }]
        """

        results = []
        page = 0

        while len(results) < limit:
            url = f"{BILLS_URL}?page={page}"
            html = self.fetch_page(url)

            soup = BeautifulSoup(html, "html.parser")

            # 🔍 Adjust selectors based on actual site structure
            bill_rows = soup.select("table tbody tr")

            if not bill_rows:
                break  # no more pages

            for row in bill_rows:
                if len(results) >= limit:
                    break

                title_tag = row.select_one("td a")
                pdf_tag = row.select_one("a[href$='.pdf']")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)

                pdf_url = None
                if pdf_tag:
                    href = pdf_tag.get("href")
                    pdf_url = href if href.startswith("http") else BASE_URL + href

                results.append({
                    "title": title,
                    "pdf_url": pdf_url
                })

            page += 1
            time.sleep(self.delay)  # be polite to server

        return results