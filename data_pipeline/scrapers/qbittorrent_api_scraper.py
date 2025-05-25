import logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from typing import Optional

from ..config import RAW_DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QBittorrentAPIScraper:
    def __init__(self, output_dir: Path = RAW_DATA_DIR):
        self.url = "https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)"
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def fetch_documentation(self) -> Optional[str]:
        try:
            logger.info(f"Fetching documentation from {self.url}")
            response = requests.get(self.url)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch documentation: {str(e)}")
            return None

    def parse_documentation(self, html_content: str) -> Optional[str]:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            main_content = soup.find(id="wiki-content")
            
            if not main_content:
                logger.error("Could not find main content on the page")
                return None
                
            return main_content.get_text(strip=True)
        except Exception as e:
            logger.error(f"Error parsing documentation: {str(e)}")
            return None

    def save_documentation(self, content: str) -> bool:
        try:
            output_file = self.output_dir / "qbittorrent_api_documentation.txt"
            output_file.write_text(content, encoding="utf-8")
            logger.info(f"Documentation saved successfully to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving documentation: {str(e)}")
            return False

    def scrape(self) -> bool:
        html_content = self.fetch_documentation()
        if not html_content:
            return False

        parsed_content = self.parse_documentation(html_content)
        if not parsed_content:
            return False

        return self.save_documentation(parsed_content)

def main():
    scraper = QBittorrentAPIScraper()
    if not scraper.scrape():
        logger.error("Failed to complete scraping process")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())
