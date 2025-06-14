#!/usr/bin/env python3
"""Run the scraping phase for already queued December 2024 games."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.scrapers.test_december_2024 import December2024TestScraper

if __name__ == "__main__":
    scraper = December2024TestScraper()
    
    # Skip URL collection since games are already in DB
    # Just run the scraping and report generation
    
    print("Executing scraping on queued games...")
    scraper.execute_test_scraping([])  # Empty list since we'll query from DB
    
    print("\nGenerating summary report...")
    report = scraper.generate_summary_report()
    
    # Save report
    with open('december_2024_test_report.md', 'w') as f:
        f.write(report)
    
    print(report)