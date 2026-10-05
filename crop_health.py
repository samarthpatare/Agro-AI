
# =========================================================
# SMART KISAN AI
# AI CROP HEALTH ANALYSIS BACKEND
# =========================================================

import os
import base64
import json
from typing import Any, Dict, Optional

from groq import Groq


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = os.environ.get(
    "SMART_KISAN_VISION_MODEL",
    "qwen/qwen3.8-27b"
)

MAX_IMAGE_SIZE = 20 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


# =========================================================
# IMAGE VALIDATION
# =========================================================

def is_allowed_image(filename: str) -> bool:

    if not filename or "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


def image_to_data_url(image_file) -> str:

    filename = getattr(
        image_file,
        "filename",
        ""
    ) or ""

    if not is_allowed_image(filename):

        raise ValueError(
            "Please upload a JPG, JPEG, PNG, or WEBP image."
        )

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    mime_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp"
    }[extension]

    image_bytes = image_file.read()

    if not image_bytes:

        raise ValueError(
            "The uploaded image is empty."
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:

        raise ValueError(
            "Image is too large. "
            "Please upload an image smaller than 20 MB."
        )

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        f"data:{mime_type};base64,{encoded}"
    )


# =========================================================
# JSON RESPONSE CLEANER
# =========================================================

def clean_json_response(
    text: Any
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    if isinstance(
        text,
        dict
    ):
        return text

    text = str(
        text
    ).strip()

    # Remove markdown code fences
    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    # Try normal JSON
    try:

        parsed = json.loads(
            text
        )

        if isinstance(
            parsed,
            dict
        ):
            return parsed

    except (
        json.JSONDecodeError,
        TypeError
    ):

        pass

    # Try extracting JSON object
    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        try:

            parsed = json.loads(
                text[
                    start:end + 1
                ]
            )

            if isinstance(
                parsed,
                dict
            ):
                return parsed

        except json.JSONDecodeError:

            pass

    return None


# =========================================================
# SAFE LIST CONVERSION
# =========================================================

def _as_list(
    value: Any
) -> list:

    if value is None:
        return []

    if isinstance(
        value,
        list
    ):

        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    if isinstance(
        value,
        str
    ):

        value = value.strip()

        if value:
            return [value]

    return []


# =========================================================
# SCORE NORMALIZATION
# =========================================================

def _clamp_score(
    value: Any
) -> int:

    try:

        value = float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        value = 0

    value = max(
        0,
        min(
            100,
            value
        )
    )

    return int(
        round(value)
    )


# =========================================================
# NORMALIZE AI RESULT
# =========================================================

def normalize_result(
    result: Dict[str, Any]
) -> Dict[str, Any]:

    # -----------------------------------------------------
    # Default fields
    # -----------------------------------------------------

    result.setdefault(
        "is_plant",
        True
    )

    result.setdefault(
        "crop",
        "Unknown"
    )

    result.setdefault(
        "health_status",
        "Needs Attention"
    )

    result.setdefault(
        "health_score",
        0
    )

    result.setdefault(
        "confidence",
        0
    )

    result.setdefault(
        "growth_stage",
        "Unknown"
    )

    result.setdefault(
        "image_quality",
        "Unknown"
    )

    result.setdefault(
        "leaf_condition",
        "Unknown"
    )

    result.setdefault(
        "visible_stress",
        []
    )

    result.setdefault(
        "possible_causes",
        []
    )

    result.setdefault(
        "recommendations",
        []
    )

    result.setdefault(
        "prevention",
        []
    )

    result.setdefault(
        "warning",
        ""
    )

    # -----------------------------------------------------
    # Basic fields
    # -----------------------------------------------------

    result["is_plant"] = bool(
        result.get(
            "is_plant",
            True
        )
    )

    result["crop"] = str(
        result.get(
            "crop"
        )
        or "Unknown"
    ).strip()

    result["health_status"] = str(
        result.get(
            "health_status"
        )
        or "Needs Attention"
    ).strip()

    result["growth_stage"] = str(
        result.get(
            "growth_stage"
        )
        or "Unknown"
    ).strip()

    result["image_quality"] = str(
        result.get(
            "image_quality"
        )
        or "Unknown"
    ).strip()

    result["leaf_condition"] = str(
        result.get(
            "leaf_condition"
        )
        or "Unknown"
    ).strip()

    result["warning"] = str(
        result.get(
            "warning"
        )
        or ""
    ).strip()

    # -----------------------------------------------------
    # Scores
    # -----------------------------------------------------

    result["health_score"] = _clamp_score(
        result.get(
            "health_score"
        )
    )

    result["confidence"] = _clamp_score(
        result.get(
            "confidence"
        )
    )

    # -----------------------------------------------------
    # Lists
    # -----------------------------------------------------

    result["visible_stress"] = _as_list(
        result.get(
            "visible_stress"
        )
    )

    result["possible_causes"] = _as_list(
        result.get(
            "possible_causes"
        )
    )

    result["recommendations"] = _as_list(
        result.get(
            "recommendations"
        )
    )

    result["prevention"] = _as_list(
        result.get(
            "prevention"
        )
    )

    return result


# =========================================================
# MAIN CROP HEALTH FUNCTION
# =========================================================

def detect_crop_health(
    image_file,
    crop_name: str = "",
    farm: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze the visible overall health of a crop.

    This feature is different from Disease Detection.

    Disease Detection:
        Identifies possible diseases.

    Crop Health:
        Evaluates overall visible plant condition,
        stress, growth stage and care needs.
    """

    # =====================================================
    # API KEY
    # =====================================================

    api_key = os.environ.get(
        "GROQ_API_KEY"
    )

    if not api_key:

        return {

            "success":
                False,

            "error":
                "GROQ_API_KEY is not configured."

        }

    # =====================================================
    # IMAGE VALIDATION
    # =====================================================

    filename = getattr(
        image_file,
        "filename",
        ""
    ) or ""

    if not is_allowed_image(
        filename
    ):

        return {

            "success":
                False,

            "error":
                "Please upload a JPG, JPEG, PNG, "
                "or WEBP crop image."

        }

    try:

        image_data_url = image_to_data_url(
            image_file
        )

    except ValueError as error:

        return {

            "success":
                False,

            "error":
                str(error)

        }

    # =====================================================
    # FARM CONTEXT
    # =====================================================

    farm = farm or {}

    crop_context = str(
        crop_name or ""
    ).strip()

    if not crop_context:

        crop_context = (
            "The farmer did not provide the crop name. "
            "Identify the crop only when visually reasonable."
        )

    farm_context = {

        "district":
            farm.get(
                "district",
                ""
            ),

        "taluka":
            farm.get(
                "taluka",
                ""
            ),

        "village":
            farm.get(
                "village",
                ""
            ),

        "soil_type":
            farm.get(
                "soil_type",
                ""
            ),

        "irrigation":
            farm.get(
                "irrigation",
                ""
            ),

        "water_source":
            farm.get(
                "water_source",
                ""
            ),

        "season":
            farm.get(
                "season",
                ""
            ),

        "previous_crop":
            farm.get(
                "previous_crop",
                ""
            )

    }

    # =====================================================
    # AI PROMPT
    # =====================================================

    prompt = f"""
You are Smart Kisan AI, an agricultural crop-health
assistant.

Analyze the uploaded crop or plant image for OVERALL
VISIBLE PLANT HEALTH.

This is NOT the disease-detection tool.

Do not claim a confirmed disease from an image alone.

Focus on:

- overall plant vigor
- leaf condition
- visible stress
- growth stage
- plant appearance
- practical care actions

FARMER CROP:

{crop_context}

FARM CONTEXT:

{json.dumps(
    farm_context,
    ensure_ascii=False
)}

Evaluate:

1. Whether the image actually contains a plant/crop.

2. Crop identity when visually reasonable.

3. Overall health status.

Use one of:

Healthy
Mild Stress
Moderate Stress
Critical

4. Health score from 0 to 100.

5. Confidence from 0 to 100.

6. Approximate growth stage.

7. Image quality.

Use:

Good
Fair
Poor

8. Overall leaf condition.

9. Visible stress signs such as:

- yellowing
- wilting
- curling
- browning
- holes
- discoloration
- stunted growth
- dryness
- water stress patterns
- possible nutrient-stress patterns

10. Possible causes.

These must be POSSIBLE causes,
not confirmed diagnoses.

11. Practical recommendations.

12. Preventive care.

IMPORTANT:

- Do not invent laboratory measurements.
- Do not claim a disease is confirmed.
- Do not invent symptoms that are not visible.
- Lower confidence when the image is unclear.
- If the image does not contain a plant,
  clearly say so.
- Keep recommendations practical and general.

Return ONLY valid JSON.

Use exactly these keys:

"is_plant": boolean,
"crop": string,
"health_status": string,
"health_score": number,
"confidence": number,
"growth_stage": string,
"image_quality": string,
"leaf_condition": string,
"visible_stress": array of strings,
"possible_causes": array of strings,
"recommendations": array of strings,
"prevention": array of strings,
"warning": string
""".strip()

    # =====================================================
    # GROQ VISION REQUEST
    # =====================================================

    try:

        client = Groq(
            api_key=api_key
        )

        completion = client.chat.completions.create(

            model=MODEL,

            messages=[

                {

                    "role":
                        "user",

                    "content": [

                        {

                            "type":
                                "text",

                            "text":
                                prompt

                        },

                        {

                            "type":
                                "image_url",

                            "image_url": {

                                "url":
                                    image_data_url

                            }

                        }

                    ]

                }

            ],

            temperature=0.2,

            max_completion_tokens=1400,

            top_p=0.8,

            stream=False,

            response_format={
                "type":
                    "json_object"
            },

            reasoning_effort="none"

        )

        # =================================================
        # CHECK RESPONSE
        # =================================================

        if not completion.choices:

            return {

                "success":
                    False,

                "error":
                    "The AI did not return a response."

            }

        response_text = (
            completion
            .choices[0]
            .message
            .content
        )

        if not response_text:

            return {

                "success":
                    False,

                "error":
                    "The AI returned an empty response. "
                    "Please try a clearer crop image."

            }

        # =================================================
        # PARSE JSON
        # =================================================

        result = clean_json_response(
            response_text
        )

        if result is None:

            return {

                "success":
                    False,

                "error":
                    "The AI returned an invalid crop "
                    "health analysis. "
                    "Please try another clear image."

            }

        # =================================================
        # NORMALIZE RESULT
        # =================================================

        result = normalize_result(
            result
        )

        # =================================================
        # NON-PLANT IMAGE
        # =================================================

        if not result.get(
            "is_plant",
            True
        ):

            result["health_status"] = (
                "Image Not Suitable"
            )

            result["health_score"] = 0

            result["warning"] = (

                result.get(
                    "warning"
                )

                or

                "Please upload a clear image "
                "of the crop or plant."

            )

        # =================================================
        # SUCCESS
        # =================================================

        return {

            "success":
                True,

            "result":
                result

        }

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as error:

        error_text = str(
            error
        )

        # Never expose API key
        if api_key:

            error_text = error_text.replace(
                api_key,
                "[REDACTED]"
            )

        return {

            "success":
                False,

            "error":
                "Crop health analysis failed: "
                + error_text

        }

