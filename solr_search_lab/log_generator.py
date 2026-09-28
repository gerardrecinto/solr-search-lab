"""Synthetic CI build-log line generator."""

import random
import uuid
from datetime import datetime, timedelta, timezone

SERVICES = [f"service-{i:02d}" for i in range(10)]
ENVIRONMENTS = ["dev", "staging", "prod"]

MESSAGE_TEMPLATES = [
    ("ERROR", "OutOfMemoryError: Java heap space exhausted during test suite"),
    ("ERROR", "Connection refused while reaching artifact repository"),
    ("ERROR", "No space left on device while writing build cache"),
    ("ERROR", "NullPointerException at build step compile-stage"),
    ("ERROR", "Connection timed out waiting for docker daemon"),
    ("WARN", "Deprecated API usage detected in module network-utils"),
    ("WARN", "Test suite took longer than expected to complete"),
    ("INFO", "Build completed successfully in record time"),
    ("INFO", "Checked out revision and starting pipeline"),
    ("INFO", "Artifact published to repository"),
]


def generate_log_line(rng: random.Random, occurred_at: datetime | None = None) -> dict:
    log_level, message = rng.choice(MESSAGE_TEMPLATES)
    occurred_at = occurred_at or (datetime.now(timezone.utc) - timedelta(minutes=rng.randint(0, 60 * 24 * 30)))
    return {
        "id": str(uuid.uuid4()),
        "build_id": f"build-{rng.randint(1000, 9999)}",
        "service": rng.choice(SERVICES),
        "environment": rng.choice(ENVIRONMENTS),
        "log_level": log_level,
        "message": message,
        "raw_line": f"[{occurred_at.isoformat()}] {log_level} {message}",
        "occurred_at": occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
