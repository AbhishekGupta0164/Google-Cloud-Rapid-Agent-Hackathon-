"""
DevSentinel — Embedding Tool
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generates 1024-dimension embeddings using Voyage AI.
Used by Agent 2 (Analyst) for query embeddings before Atlas Vector Search,
and by the seed script to embed past incidents at insert time.

BUG FIX: asyncio.get_event_loop() is deprecated in Python 3.10+.
         Use asyncio.get_running_loop() inside async functions instead.
"""

import os
import asyncio
from typing import List

import voyageai


_client: voyageai.Client = None


def _get_client() -> voyageai.Client:
    """Lazy-init Voyage AI client (reads env var at call time, not import time)."""
    global _client
    if _client is None:
        api_key = os.environ.get("VOYAGE_API_KEY", "")
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY environment variable is not set. "
                "Get your key at https://www.voyageai.com/"
            )
        _client = voyageai.Client(api_key=api_key)
    return _client


async def get_embedding(text: str) -> List[float]:
    """
    Generates a 1024-dimension Voyage AI embedding for the given text.

    Used for QUERY embeddings (the search vector for Atlas Vector Search).
    Atlas autoEmbed handles INSERT-time embeddings automatically.

    USAGE (in Analyst agent):
      embedding = await get_embedding("PR renames payment_status field")
      # Returns: [0.023, -0.441, 0.187, ...] (1024 floats)

    Then used in Atlas $vectorSearch:
      "$vectorSearch": {
        "queryVector": embedding,
        "numCandidates": 100,
        "limit": 5
      }
    """
    loop = asyncio.get_running_loop()   # ← Fixed: was get_event_loop() (deprecated)
    result = await loop.run_in_executor(
        None,
        lambda: _get_client().embed([text], model="voyage-3", input_type="query"),
    )
    return result.embeddings[0]


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generates embeddings for multiple texts in one API call.
    More efficient than calling get_embedding() in a loop.
    Used by the seed script to embed all past incidents at once.
    """
    loop = asyncio.get_running_loop()   # ← Fixed: was get_event_loop() (deprecated)
    result = await loop.run_in_executor(
        None,
        lambda: _get_client().embed(texts, model="voyage-3", input_type="document"),
    )
    return result.embeddings
