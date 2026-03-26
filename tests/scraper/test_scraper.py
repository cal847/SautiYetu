# # tests/test_scraper.py
# import pytest
# from unittest.mock import patch, Mock
# from app.scraper.scraper import ParliamentScraper

# MOCK_HTML = """
# <table>
#   <tbody>
#     <tr>
#       <td><a href="/bill/1">Finance Bill 2024</a></td>
#       <td><a href="/pdf/finance-bill-2024.pdf">PDF</a></td>
#     </tr>
#     <tr>
#       <td><a href="/bill/2">Energy Amendment Bill</a></td>
#       <td><a href="/pdf/energy-bill.pdf">PDF</a></td>
#     </tr>
#   </tbody>
# </table>
# """

# @patch("requests.get")
# def test_scrape_bills(mock_get):
#     # Mock successful HTTP response
#     mock_resp = Mock()
#     mock_resp.status_code = 200
#     mock_resp.text = MOCK_HTML
#     mock_get.return_value = mock_resp

#     scraper = ParliamentScraper()
#     results = scraper.scrape_bills(limit=2)

#     assert len(results) == 2
#     assert results[0]["title"] == "Finance Bill 2024"
#     assert results[0]["pdf_url"] == "https://www.parliament.go.ke/pdf/finance-bill-2024.pdf"
#     assert results[1]["title"] == "Energy Amendment Bill"



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