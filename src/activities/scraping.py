import logging
import hashlib
import aiohttp
from bs4 import BeautifulSoup
from temporalio import activity

logger = logging.getLogger(__name__)

@activity.defn
async def fetch_html_activity(url: str) -> str:
    logger.info(f"Fetching HTML for URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataForgeBot/1.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=30) as response:
            response.raise_for_status()
            return await response.text()

@activity.defn
async def parse_html_to_text_activity(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

@activity.defn
async def generate_content_hash_activity(text_content: str) -> str:
    """Generates SHA-256 hash for idempotency checks."""
    return hashlib.sha256(text_content.encode("utf-8")).hexdigest()
