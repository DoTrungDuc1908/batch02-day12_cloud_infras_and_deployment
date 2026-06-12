"""Offline mock LLM used by the lab so no real API key is required."""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock production agent response. Replace this adapter with a real LLM client when an API key is available.",
        "The agent received your question and answered through the production API path.",
        "Your request passed authentication, rate limiting, budget checks, and conversation storage.",
    ],
    "docker": [
        "Docker packages the app and its dependencies so the same artifact can run locally and in the cloud.",
    ],
    "deploy": [
        "Deployment moves the service from local development to a managed runtime with public networking and logs.",
    ],
    "health": [
        "Health checks let the platform decide whether the process is alive and should keep receiving traffic.",
    ],
}


def ask(question: str, delay: float = 0.05) -> str:
    time.sleep(delay + random.uniform(0, 0.02))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])
