# backend/services/ai_schemas.py
from __future__ import annotations
from typing import Literal, Required, TypedDict

PatternEnum = Literal[
    "solid","striped","plaid","floral","graphic","polka_dots","geom","textured","other"
]

class PatternRequest(TypedDict):
    id: str
    label: str
    cropDataUrl: str  # data:image/jpeg;base64,...

class PatternResult(TypedDict, total=False):
    id: Required[str]
    label: Required[str]
    pattern: PatternEnum
    confidence: float
    notes: str | None
    error: str

GARMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "enum": ["solid","striped","plaid","floral","graphic","polka_dots","geom","textured","other"],
            "description": "Primary visible fabric motif."
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Model confidence that the selected pattern is correct."
        },
        "notes": {
            "type": ["string", "null"],
            "description": "Optional short comments; null if none."
        }
    },
    "required": ["pattern", "confidence", "notes"],
    "additionalProperties": False,
}
# System / user guidance
SYSTEM_MSG = (
    "You are a fashion attribute extractor. "
    "Always respond in JSON that conforms to the provided JSON Schema. "
    "If unsure, choose pattern='other' and set confidence<=0.5."
)
USER_INSTRUCTIONS = (
    "Identify the garment's PATTERN (fabric motif) in the crop image. "
    "Return ONLY JSON per schema. Options include: solid, striped, plaid, floral, "
    "graphic, polka_dots, geom, textured, other."
)
