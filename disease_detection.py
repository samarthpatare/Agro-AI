# =========================================================
# SMART KISAN AI
# AI PLANT DISEASE DETECTION V2
# =========================================================

import os
import base64
import json

from groq import Groq


# =========================================================
# CONFIGURATION
# =========================================================

MODEL = "qwen/qwen3.8-27b"

MAX_IMAGE_SIZE = 20 * 1024 * 1024


# =========================================================
# ALLOWED IMAGE TYPES
# =========================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


# =========================================================
# CHECK IMAGE
# =========================================================

def is_allowed_image(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    return extension in ALLOWED_EXTENSIONS


# =========================================================
# IMAGE TO BASE64 DATA URL
# =========================================================

def image_to_data_url(image_file):

    filename = image_file.filename or ""

    if "." not in filename:

        raise ValueError(
            "The uploaded file has no valid extension."
        )

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    mime_type = {

        "jpg":
            "image/jpeg",

        "jpeg":
            "image/jpeg",

        "png":
            "image/png",

        "webp":
            "image/webp"

    }.get(extension)

    if mime_type is None:

        raise ValueError(
            "Unsupported image format."
        )

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

    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return (
        f"data:{mime_type};base64,{encoded_image}"
    )


# =========================================================
# CLEAN JSON RESPONSE
# =========================================================

def clean_json_response(text):

    if not text:
        return None

    if isinstance(
        text,
        dict
    ):
        return text

    text = str(text).strip()

    # -----------------------------------------------------
    # Remove markdown code fences
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Complete JSON
    # -----------------------------------------------------

    try:

        return json.loads(
            text
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        pass

    # -----------------------------------------------------
    # Find JSON object inside response
    # -----------------------------------------------------

    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        possible_json = text[
            start:end + 1
        ]

        try:

            return json.loads(
                possible_json
            )

        except json.JSONDecodeError:

            pass

    return None


# =========================================================
# NORMALIZE RESULT
# =========================================================

def normalize_result(result):

    if not isinstance(
        result,
        dict
    ):

        return None

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
        "disease",
        "Unknown"
    )

    result.setdefault(
        "confidence",
        0
    )

    result.setdefault(
        "severity",
        "Unknown"
    )

    result.setdefault(
        "image_quality",
        "Unknown"
    )

    result.setdefault(
        "symptoms",
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
    # Normalize is_plant
    # -----------------------------------------------------

    is_plant = result.get(
        "is_plant",
        True
    )

    if isinstance(
        is_plant,
        str
    ):

        is_plant = (
            is_plant.strip().lower()
            in {
                "true",
                "yes",
                "1"
            }
        )

    else:

        is_plant = bool(
            is_plant
        )

    result["is_plant"] = is_plant

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    confidence = result.get(
        "confidence",
        0
    )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError
    ):

        confidence = 0

    confidence = max(
        0,
        min(
            100,
            confidence
        )
    )

    result["confidence"] = round(
        confidence
    )

    # -----------------------------------------------------
    # Image quality
    # -----------------------------------------------------

    image_quality = str(
        result.get(
            "image_quality",
            "Unknown"
        )
    ).strip()

    allowed_quality = {
        "Good",
        "Fair",
        "Poor",
        "Unknown"
    }

    if image_quality not in allowed_quality:

        image_quality = "Unknown"

    result["image_quality"] = (
        image_quality
    )

    # -----------------------------------------------------
    # Normalize severity
    # -----------------------------------------------------

    severity = str(
        result.get(
            "severity",
            "Unknown"
        )
    ).strip()

    allowed_severity = {
        "Low",
        "Moderate",
        "High",
        "Unknown"
    }

    if severity not in allowed_severity:

        severity = "Unknown"

    result["severity"] = severity

    # -----------------------------------------------------
    # Convert list fields safely
    # -----------------------------------------------------

    list_fields = [

        "symptoms",

        "possible_causes",

        "recommendations",

        "prevention"

    ]

    for field in list_fields:

        value = result.get(
            field
        )

        if value is None:

            result[field] = []

        elif isinstance(
            value,
            str
        ):

            result[field] = [
                value
            ]

        elif not isinstance(
            value,
            list
        ):

            result[field] = []

        else:

            # Keep only useful text values
            result[field] = [
                str(item).strip()
                for item in value
                if str(item).strip()
            ]

    # -----------------------------------------------------
    # Non-plant image handling
    # -----------------------------------------------------

    if not result["is_plant"]:

        result["crop"] = "Unknown"

        result["disease"] = (
            "Not a plant image"
        )

        result["severity"] = (
            "Unknown"
        )

        result["confidence"] = min(
            result["confidence"],
            20
        )

        result["warning"] = (
            "The uploaded image does not "
            "appear to contain a plant or leaf. "
            "Please upload a clear crop image."
        )

        result["symptoms"] = []

        result["possible_causes"] = []

        result["recommendations"] = [
            "Upload a clear image of the affected plant or leaf."
        ]

        result["prevention"] = []

        return result

    # -----------------------------------------------------
    # Unknown / poor image handling
    # -----------------------------------------------------

    disease = str(
        result.get(
            "disease",
            "Unknown"
        )
    ).strip()

    if (
        result["image_quality"] == "Poor"
        and result["confidence"] < 70
    ):

        result["disease"] = (
            "Unable to determine reliably"
        )

        result["severity"] = "Unknown"

        result["warning"] = (
            "The image quality or visible symptoms "
            "are not sufficient for a reliable visual assessment. "
            "Please upload a clearer close-up image."
        )

    elif (
        disease
        and disease.lower()
        not in {
            "unknown",
            "healthy plant",
            "not a plant image",
            "unable to determine reliably"
        }
        and not disease.lower().startswith(
            "possible "
        )
    ):

        # -------------------------------------------------
        # Never present visual disease detection
        # as laboratory-confirmed diagnosis.
        # -------------------------------------------------

        result["disease"] = (
            "Possible " + disease
        )

    # -----------------------------------------------------
    # Healthy plant handling
    # -----------------------------------------------------

    if disease.lower() == "healthy plant":

        result["disease"] = (
            "Healthy Plant"
        )

        if result["confidence"] < 70:

            result["warning"] = (
                "The image does not show strong visible "
                "evidence of disease, but visual analysis "
                "cannot confirm that the plant is completely healthy."
            )

    # -----------------------------------------------------
    # Low confidence handling
    # -----------------------------------------------------

    if (
        result["confidence"] < 50
        and result["is_plant"]
    ):

        result["warning"] = (
            "The visual evidence is limited. "
            "This result should be treated as a preliminary "
            "assessment and confirmed by a local agriculture expert."
        )

    # -----------------------------------------------------
    # Default warning
    # -----------------------------------------------------

    if not str(
        result.get(
            "warning",
            ""
        )
    ).strip():

        result["warning"] = (
            "This is an AI-based visual assessment, "
            "not a laboratory-confirmed diagnosis. "
            "Consider crop condition, weather, soil factors "
            "and expert confirmation before treatment."
        )

    return result


# =========================================================
# DISEASE DETECTION
# =========================================================

def detect_plant_disease(
    image_file,
    crop_name=""
):

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

    filename = (
        image_file.filename
        if image_file
        else ""
    )

    if not is_allowed_image(
        filename
    ):

        return {

            "success":
                False,

            "error":
                "Please upload a JPG, JPEG, PNG, "
                "or WEBP image."

        }

    # =====================================================
    # CONVERT IMAGE
    # =====================================================

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
    # CROP INFORMATION
    # =====================================================

    crop_context = str(
        crop_name or ""
    ).strip()

    if not crop_context:

        crop_context = (
            "The farmer did not specify the crop. "
            "Identify the crop from the image if possible."
        )

    # =====================================================
    # AI PROMPT
    # =====================================================

    prompt = f"""
You are Smart Kisan AI, an agricultural plant
health and disease visual-assessment assistant.

Analyze the uploaded plant or leaf image carefully.

The farmer provided this crop information:

{crop_context}

IMPORTANT:
This is a visual AI assessment only.
It is NOT a laboratory diagnosis.
Do not present a suspected disease as confirmed.

Your tasks:

1. Determine whether the image contains a plant or leaf.

2. Identify the crop if possible.

3. Assess whether visible symptoms may be
   consistent with a plant disease, pest damage,
   nutrient stress, environmental stress,
   or another visible problem.

4. If the plant appears healthy, use:
   "Healthy Plant"

5. If there is insufficient visual evidence,
   use:
   "Unknown"

6. If a disease appears likely, provide the
   disease name as a POSSIBLE disease.

7. Never invent symptoms that are not visibly
   supported by the image.

8. Consider image quality carefully.

9. Rate image quality as:
   "Good", "Fair", "Poor", or "Unknown".

10. Give a confidence value from 0 to 100.
    This is ONLY AI visual confidence, not
    laboratory certainty.

11. Use severity:
    "Low", "Moderate", "High", or "Unknown".

12. Provide general agricultural next steps.

13. Do NOT prescribe a specific pesticide,
    fungicide, insecticide, herbicide,
    chemical dose, concentration, or application
    schedule from the image alone.

14. Do NOT recommend a specific chemical product
    as if the disease were confirmed.

15. Instead, recommend safe general actions such as:
    monitoring,
    removing severely affected plant material
    where appropriate,
    improving airflow,
    avoiding prolonged leaf wetness,
    checking irrigation,
    checking soil/nutrient conditions,
    crop sanitation,
    and expert confirmation.

16. If treatment may be necessary, tell the farmer
    to confirm the suspected problem with a qualified
    local agriculture expert before selecting a treatment.

17. If the image is blurry, poorly lit, obstructed,
    too distant, or otherwise insufficient,
    do NOT make a confident disease claim.

18. If the image is not a plant image:
    is_plant must be false.

19. Return ONLY valid JSON.

20. Do not return markdown.

21. Do not return explanations outside JSON.

IMPORTANT JSON FORMAT:

Return exactly ONE JSON object:

{{
    "is_plant": true,

    "crop": "crop name",

    "disease": "Possible disease name, Healthy Plant, or Unknown",

    "confidence": 0,

    "severity": "Low, Moderate, High, or Unknown",

    "image_quality": "Good, Fair, Poor, or Unknown",

    "symptoms": [
        "visible symptom 1",
        "visible symptom 2"
    ],

    "possible_causes": [
        "possible cause 1",
        "possible cause 2"
    ],

    "recommendations": [
        "safe general recommendation 1",
        "safe general recommendation 2",
        "expert confirmation recommendation"
    ],

    "prevention": [
        "prevention 1",
        "prevention 2"
    ],

    "warning": "short uncertainty and safety note"
}}

Every field MUST be present.

The confidence MUST be a number from 0 to 100.

If the image is not a plant:

{{
    "is_plant": false,
    "crop": "Unknown",
    "disease": "Not a plant image",
    "confidence": 0,
    "severity": "Unknown",
    "image_quality": "Good, Fair, Poor, or Unknown",
    "symptoms": [],
    "possible_causes": [],
    "recommendations": [
        "Upload a clear image of the affected plant or leaf."
    ],
    "prevention": [],
    "warning": "Please upload a clear crop image."
}}

Do not diagnose a disease with high confidence when
the image does not provide enough visual evidence.
"""

    # =====================================================
    # GROQ CLIENT
    # =====================================================

    try:

        client = Groq(
            api_key=api_key
        )

        # =================================================
        # VISION + JSON MODE
        # =================================================

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

            max_completion_tokens=1200,

            top_p=0.8,

            stream=False,

            response_format={
                "type":
                    "json_object"
            },

            reasoning_effort="none"

        )

        # =================================================
        # GET RESPONSE
        # =================================================

        if not completion.choices:

            return {

                "success":
                    False,

                "error":
                    "The AI did not return a response."

            }

        message = (
            completion
            .choices[0]
            .message
        )

        response_text = (
            message.content
        )

        # =================================================
        # EMPTY RESPONSE CHECK
        # =================================================

        if not response_text:

            return {

                "success":
                    False,

                "error":
                    "The AI returned an empty response. "
                    "Please try another clear plant image."

            }

        # =================================================
        # PARSE JSON
        # =================================================

        result = clean_json_response(
            response_text
        )

        # =================================================
        # JSON FAILED
        # =================================================

        if result is None:

            return {

                "success":
                    False,

                "error":
                    "The AI returned an invalid analysis. "
                    "Please try another clear plant image."

            }

        # =================================================
        # NORMALIZE
        # =================================================

        result = normalize_result(
            result
        )

        if result is None:

            return {

                "success":
                    False,

                "error":
                    "The AI response could not be processed."

            }

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
    # GROQ API ERROR
    # =====================================================

    except Exception as error:

        error_text = str(
            error
        )

        # -------------------------------------------------
        # Never expose the API key.
        # -------------------------------------------------

        if api_key:

            error_text = error_text.replace(
                api_key,
                "[REDACTED]"
            )

        return {

            "success":
                False,

            "error":
                "Disease detection failed: "
                + error_text

        }