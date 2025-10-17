from __future__ import annotations
import os
import json
from typing import List
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError

from .ai_schemas import (
    PatternRequest, PatternResult, GARMENT_SCHEMA, SYSTEM_MSG, USER_INSTRUCTIONS
)

load_dotenv()


class AIClient:
    """
    Thin wrapper around OpenAI Responses API with Structured Outputs.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or os.getenv("WEARWISE_VLM", "gpt-4.1-mini")
        self.client = OpenAI(api_key=api_key)  # reads OPENAI_API_KEY if None

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.8, min=1, max=8),
        retry=retry_if_exception_type(
            (APIConnectionError, RateLimitError, APIStatusError))
    )
    def _describe_one(self, req: PatternRequest) -> PatternResult:
        """
        Calls the model for a single garment crop using Structured Outputs
        with json_schema via text.format. Assumes OpenAI SDK >= 1.40.0.
        """
        resp = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_MSG}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"{USER_INSTRUCTIONS}\nGarment label: {req['label']}",
                        },
                        {"type": "input_image", "image_url": req["cropDataUrl"]},
                    ],
                }, # type: ignore
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "GarmentPattern",
                    "schema": GARMENT_SCHEMA,
                    "strict": True,
                }
            },
        )

        # Parse response
        try:
            payload = resp.output[0].content[0].text  # type: ignore[index]
            data = json.loads(payload)
            return {
                "id": req["id"],
                "label": req["label"],
                "pattern": data.get("pattern", "other"),
                "confidence": float(data.get("confidence", 0.0)),
                "notes": data.get("notes"),
            }
        except Exception as e:
            return {
                "id": req["id"],
                "label": req["label"],
                "pattern": "other",
                "confidence": 0.0,
                "notes": None,
                "error": f"ParseError: {type(e).__name__}: {e}",
            }

    def analyze_batch(self, items: List[PatternRequest], max_concurrency: int = 3) -> List[PatternResult]:
        """
        Simple bounded concurrency without asyncio—good enough for Socket.IO handler.
        """
        results: List[PatternResult] = []
        if not items:
            return results

        # small worker pool using threads
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max_concurrency) as ex:
            futs = [ex.submit(self._safe_call, req) for req in items]
            for f in as_completed(futs):
                results.append(f.result())
        # preserve input order (optional)
        by_id = {r["id"]: r for r in results}
        return [by_id[i["id"]] for i in items if i["id"] in by_id]

    def _safe_call(self, req: PatternRequest) -> PatternResult:
        try:
            return self._describe_one(req)
        except Exception as e:
            return {
                "id": req["id"],
                "label": req["label"],
                "pattern": "other",
                "confidence": 0.0,
                "error": f"{type(e).__name__}: {e}",
            }
