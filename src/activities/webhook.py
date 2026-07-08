import logging
import aiohttp
from typing import Dict, Any
from temporalio import activity

logger = logging.getLogger(__name__)

@activity.defn
async def send_webhook_activity(url: str, payload: Dict[str, Any]) -> bool:
    """
    Sends an HTTP POST to the customer's webhook URL.
    Returns True if successful. If it raises an exception (e.g. 500), Temporal will retry.
    """
    logger.info(f"Sending webhook callback to {url}")
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DataForge-Webhook/1.0"
    }
    
    # In a real SaaS, we would sign this request with HMAC using the tenant's secret
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json=payload, timeout=10) as response:
            response.raise_for_status()
            logger.info(f"Webhook sent successfully, status {response.status}")
            return True
