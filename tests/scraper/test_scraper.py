"without mocking"
import pytest
from app.scraper.scraper import ParliamentScraper

def test_scrape_50_bills_real():
    scraper = ParliamentScraper()
    
    # Fetch 50 bills
    results = scraper.scrape_bills(limit=50)
    
    # Assert we got 50 results
    assert len(results) == 50
    
    # Check that each bill has the required fields
    for bill in results:
        assert "title" in bill
        assert "pdf_url" in bill
        assert bill["pdf_url"].startswith("https://")
    
    # Optional: print first 3 bills for inspection
    for bill in results[:3]:
        print(bill)