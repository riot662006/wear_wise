# backend/services/ai_schemas.py
from __future__ import annotations
from typing import Literal, Required, TypedDict

PatternEnum = Literal[
    "solid","striped","plaid","floral","graphic","polka_dots","geom","textured","other"
]

# Material enum for garment fabrics
MaterialEnum = Literal[
    "cotton","denim","leather","wool","silk","satin","knit","linen","synthetic","other"
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
    # Added material fields to the same garment schema
    material: MaterialEnum
    materialConfidence: float
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
        "material": {
            "type": "string",
            "enum": ["cotton","denim","leather","wool","silk","satin","knit","linen","synthetic","other"],
            "description": "Dominant material or fabric type visible in the crop."
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Model confidence that the selected pattern is correct."
        },
        "materialConfidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Model confidence that the selected material is correct."
        },
        "notes": {
            "type": ["string", "null"],
            "description": "Optional short comments; null if none."
        }
    },
    "required": ["pattern", "confidence", "material", "materialConfidence", "notes"],
    "additionalProperties": False,
}
# System / user guidance
SYSTEM_MSG = (
    "You are a fashion attribute extractor. "
    "Always respond in JSON that conforms to the provided JSON Schema. "
    "If unsure about pattern or material, choose 'other' and set the corresponding confidence<=0.5."
)
USER_INSTRUCTIONS = (
    "Identify the garment's PATTERN (fabric motif) and DOMINANT MATERIAL in the crop image. "
    "Return ONLY JSON per schema. Pattern options: solid, striped, plaid, floral, "
    "graphic, polka_dots, geom, textured, other. Material options: cotton, denim, leather, wool, silk, satin, knit, linen, synthetic, other."
)
