"""
DevSentinel — Settings
All environment variables and configuration in one place.

BUG FIX: Using field(default_factory=...) instead of os.environ.get() as default
because dataclass defaults are evaluated at class definition time — meaning a
.env file loaded AFTER the import would be ignored. __post_init__ solves this.
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # ── MongoDB ───────────────────────────────────────────────────
    MONGODB_URI: str = field(default="")
    MONGODB_DB_NAME: str = field(default="devsentiinel")

    # ── Google / Gemini ───────────────────────────────────────────
    GEMINI_API_KEY: str = field(default="")
    GEMINI_MODEL: str = field(default="gemini-2.5-flash")

    # ── GitHub ────────────────────────────────────────────────────
    GITHUB_TOKEN: str = field(default="")
    GITHUB_WEBHOOK_SECRET: str = field(default="")

    # ── Voyage AI ─────────────────────────────────────────────────
    VOYAGE_API_KEY: str = field(default="")

    # ── Vector Search ─────────────────────────────────────────────
    INCIDENT_VECTOR_INDEX: str = field(default="incident_vector_index")
    QUERY_VECTOR_INDEX: str = field(default="query_vector_index")
    VECTOR_SIMILARITY_THRESHOLD: float = field(default=0.75)
    VECTOR_NUM_CANDIDATES: int = field(default=100)
    VECTOR_RESULT_LIMIT: int = field(default=5)
    EMBEDDING_DIMENSIONS: int = field(default=1024)   # Voyage AI voyage-3 default

    # ── Risk Thresholds ───────────────────────────────────────────
    CONFIDENCE_HIGH_THRESHOLD: float = field(default=0.80)
    CONFIDENCE_MED_THRESHOLD: float = field(default=0.50)
    QUERY_CRITICAL_MS: int = field(default=5000)    # >5s = CRITICAL
    QUERY_HIGH_MS: int = field(default=1000)         # >1s = HIGH

    # ── Pipeline ──────────────────────────────────────────────────
    PIPELINE_TIMEOUT_SECONDS: int = field(default=60)
    AUTO_POST_COMMENT: bool = field(default=True)    # Set False to require manual confirm
    AUTO_CREATE_FIX_PR: bool = field(default=False)  # Always requires user confirmation

    # ── Collections ───────────────────────────────────────────────
    COLLECTION_PAST_INCIDENTS: str = field(default="past_incidents")
    COLLECTION_PR_ANALYSES: str = field(default="pr_analyses")
    COLLECTION_QUERY_PATTERNS: str = field(default="query_patterns")
    COLLECTION_AUDIT_LOG: str = field(default="audit_log")
    COLLECTION_CHANGE_REQUESTS: str = field(default="change_requests")

    def __post_init__(self):
        """
        Read environment variables AFTER instantiation so that:
        1. dotenv's load_dotenv() has already run
        2. We pick up values set at runtime, not class-definition time
        Only overwrite if the current value is the empty-string default.
        """
        env_map = {
            "MONGODB_URI": "MONGODB_URI",
            "MONGODB_DB_NAME": "MONGODB_DB_NAME",
            "GEMINI_API_KEY": "GEMINI_API_KEY",
            "GEMINI_MODEL": "GEMINI_MODEL",
            "GITHUB_TOKEN": "GITHUB_TOKEN",
            "GITHUB_WEBHOOK_SECRET": "GITHUB_WEBHOOK_SECRET",
            "VOYAGE_API_KEY": "VOYAGE_API_KEY",
        }
        for attr, env_key in env_map.items():
            # Only override if the current value hasn't been set explicitly
            current = getattr(self, attr)
            if not current:
                setattr(self, attr, os.environ.get(env_key, current))
