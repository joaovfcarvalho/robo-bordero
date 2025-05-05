import unittest
from src.db import append_to_csv, read_csv
from src.scraper import download_pdfs
from src.gemini import analyze_pdf_with_gemini

class TestDBFunctions(unittest.TestCase):
    def test_append_to_csv(self):
        # Test appending to a CSV file
        test_file = "test.csv"
        data = [{"id": 1, "name": "Test"}]
        headers = ["id", "name"]
        append_to_csv(test_file, data, headers)
        result = read_csv(test_file)
        self.assertEqual(result, data)

    def test_read_csv(self):
        # Test reading from a CSV file
        test_file = "test.csv"
        result = read_csv(test_file)
        self.assertIsInstance(result, list)

class TestScraperFunctions(unittest.TestCase):
    def test_download_pdfs(self):
        # Test downloading PDFs (mocked)
        year = 2025
        competition_code = "142"
        download_dir = "test_pdfs"
        result = download_pdfs(year, competition_code, download_dir)
        self.assertIsInstance(result, list)

class TestGeminiFunctions(unittest.TestCase):
    def test_analyze_pdf_with_gemini(self):
        # Test analyzing a PDF (mocked)
        api_key = "test_key"
        pdf_path = "test.pdf"
        result = analyze_pdf_with_gemini(api_key, pdf_path)
        self.assertIsInstance(result, dict)

if __name__ == "__main__":
    unittest.main()