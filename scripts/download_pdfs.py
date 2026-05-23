from __future__ import annotations

import os
from pathlib import Path
import urllib.request
from utils.logger import get_logger

logger = get_logger(__name__)

PDF_URLS = {
    "it_act.pdf": "https://prsindia.org/files/bills_acts/acts_parliament/2000/act21of2000.pdf",
    "constitution.pdf": "https://sansad.in/uploads/Constitution_of_India_in_English_c58f05786a.pdf",
    "dpdp.pdf": "https://prsindia.org/files/bills_acts/acts_parliament/2023/Act%2022%20of%202023.pdf",
}

def download_file(url: str, dest_path: Path) -> bool:
    try:
        logger.info(f"Downloading {url} to {dest_path}...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            with open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
        logger.info(f"Successfully downloaded {dest_path.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def main() -> None:
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    success = True
    for filename, url in PDF_URLS.items():
        dest = raw_dir / filename
        if dest.exists() and dest.stat().st_size > 1000:
            logger.info(f"{filename} already exists, skipping download.")
            continue
        if not download_file(url, dest):
            success = False
            
    if success:
        print("\nAll legal documents successfully downloaded to data/raw/")
    else:
        print("\nSome downloads failed. Please check the logs.")

if __name__ == "__main__":
    main()
