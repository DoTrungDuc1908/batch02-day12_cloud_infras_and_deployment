"""Redis-backed monthly budget guard."""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_store import redis_client


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = input_tokens / 1000 * settings.estimated_input_cost_per_1k
    output_cost = output_tokens / 1000 * settings.estimated_output_cost_per_1k
    return input_cost + output_cost


def check_and_record_budget(user_id: str, estimated_cost: float) -> float:
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    current = float(redis_client.get(key) or 0)

    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail=(
                "Monthly budget exceeded. "
                f"Current: ${current:.4f}, limit: ${settings.monthly_budget_usd:.2f}"
            ),
        )

    total = redis_client.incrbyfloat(key, estimated_cost)
    redis_client.expire(key, 32 * 24 * 3600)
    return float(total)
