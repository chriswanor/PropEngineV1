from typing import Optional, Dict, Any
import os

from openai import OpenAI

MODEL = "gpt-4o-mini"

def generate_ai_report(
    metrics: Dict[str, Any],
    sensitivity: Dict[str, Any],
    api_key: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> str:
    """Generate an AI investment report using OpenAI.

    If a client is passed, it will be used directly (useful for tests).
    Otherwise, a client will be constructed using the provided api_key
    or the OPENAI_API_KEY environment variable.
    """
    if client is None:
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ValueError("Missing OpenAI API key. Provide api_key or set OPENAI_API_KEY.")
        client = OpenAI(api_key=resolved_api_key)

    prompt = f"""
    You are a commercial real estate investment analyst.
    Based on the following data, write a structured investment report.

    Metrics:
    {metrics}

    Sensitivity:
    {sensitivity}

    Report structure:
    1. Executive Summary
    2. Market Benchmark Analysis
    3. Sensitivity Insights
    4. Final Recommendation (BUY or DON'T BUY)
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a professional CRE investment analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content