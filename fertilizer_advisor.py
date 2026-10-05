import os
import json
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = os.environ.get(
    "SMART_KISAN_TEXT_MODEL",
    "qwen/qwen3.8-27b"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _safe_text(
    value: Any,
    default: str = ""
) -> str:
    """
    Convert any value into a safe string.
    """

    if value is None:
        return default

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _safe_list(
    value: Any
) -> List[str]:
    """
    Convert a value into a clean list of strings.
    """

    if value is None:
        return []

    if isinstance(value, list):

        cleaned = []

        for item in value:

            text = _safe_text(item)

            if text:
                cleaned.append(text)

        return cleaned

    text = _safe_text(value)

    if text:
        return [text]

    return []


def _has_real_data(
    data: Any
) -> bool:
    """
    Check whether a dictionary contains meaningful data.

    This prevents a dictionary containing only empty values
    from being treated as available analysis.
    """

    if not isinstance(data, dict):
        return False

    for value in data.values():

        if value in (
            None,
            "",
            [],
            {}
        ):
            continue

        return True

    return False


def _format_soil_value(
    value: Any,
    unit: str = ""
) -> str:
    """
    Format soil values compactly for the AI.
    """

    if value in (
        None,
        ""
    ):
        return "Not provided"

    text = _safe_text(value)

    if unit:
        return f"{text} {unit}"

    return text


# ============================================================
# NORMALIZE AI RESULT
# ============================================================

def normalize_result(
    data: Dict[str, Any],
    crop_name: str,
    soil_data: Dict[str, Any],
    soil_available: bool,
    disease_data: Dict[str, Any],
    disease_available: bool,
    crop_health_data: Dict[str, Any],
    health_available: bool
) -> Dict[str, Any]:
    """
    Normalize the AI response.

    Important:
    analysis_basis is determined from the actual Python inputs,
    not from the AI model.
    """

    if not isinstance(data, dict):
        data = {}

    # --------------------------------------------------------
    # NUTRIENT STATUS
    # --------------------------------------------------------

    nutrient_status = data.get(
        "nutrient_status",
        {}
    )

    if not isinstance(
        nutrient_status,
        dict
    ):
        nutrient_status = {}

    # --------------------------------------------------------
    # FERTILIZER PLAN
    # --------------------------------------------------------

    fertilizer_plan = data.get(
        "fertilizer_plan",
        []
    )

    if not isinstance(
        fertilizer_plan,
        list
    ):
        fertilizer_plan = []

    normalized_plan = []

    for item in fertilizer_plan[:2]:

        if not isinstance(
            item,
            dict
        ):
            continue

        normalized_plan.append({

            "fertilizer":
                _safe_text(
                    item.get("fertilizer")
                ),

            "purpose":
                _safe_text(
                    item.get("purpose")
                ),

            "application_stage":
                _safe_text(
                    item.get("application_stage")
                ),

            "guidance":
                _safe_text(
                    item.get("guidance")
                )
        })

    # --------------------------------------------------------
    # SOIL IMPROVEMENT
    # --------------------------------------------------------

    soil_improvement = _safe_list(
        data.get(
            "soil_improvement"
        )
    )[:2]

    # --------------------------------------------------------
    # WARNINGS
    # --------------------------------------------------------

    warnings = _safe_list(
        data.get(
            "warnings"
        )
    )[:2]

    # --------------------------------------------------------
    # FALLBACK NUTRIENT VALUES
    # --------------------------------------------------------

    nitrogen_fallback = _format_soil_value(
        soil_data.get("nitrogen"),
        "kg/ha"
    )

    phosphorus_fallback = _format_soil_value(
        soil_data.get("phosphorus"),
        "kg/ha"
    )

    potassium_fallback = _format_soil_value(
        soil_data.get("potassium"),
        "kg/ha"
    )

    ph_fallback = _format_soil_value(
        soil_data.get(
            "ph",
            soil_data.get("pH")
        )
    )

    organic_carbon_fallback = _format_soil_value(
        soil_data.get("organic_carbon"),
        "%"
    )

    ec_fallback = _format_soil_value(
        soil_data.get(
            "electrical_conductivity"
        ),
        "dS/m"
    )

    # --------------------------------------------------------
    # FINAL NORMALIZED RESULT
    # --------------------------------------------------------

    result = {

        "crop":
            (
                _safe_text(
                    data.get("crop")
                )
                or crop_name
            ),

        "overall_message":
            _safe_text(
                data.get("overall_message"),
                "Recommendation based on the available farm analysis."
            ),

        # IMPORTANT:
        # These come from actual application data,
        # NOT from AI.
        "analysis_basis": {

            "soil_report_used":
                bool(soil_available),

            "disease_detection_used":
                bool(disease_available),

            "crop_health_used":
                bool(health_available)
        },

        "disease_assessment":
            _safe_text(
                data.get(
                    "disease_assessment"
                ),
                (
                    "No disease result was available."
                    if not disease_available
                    else
                    "Disease data was reviewed as supporting evidence."
                )
            ),

        "crop_health_assessment":
            _safe_text(
                data.get(
                    "crop_health_assessment"
                ),
                (
                    "No crop-health result was available."
                    if not health_available
                    else
                    "Crop-health data was reviewed as supporting evidence."
                )
            ),

        "combined_reasoning":
            _safe_text(
                data.get(
                    "combined_reasoning"
                ),
                "Recommendation uses the available soil, disease and crop-health evidence."
            ),

        "nutrient_status": {

            "nitrogen":
                _safe_text(
                    nutrient_status.get(
                        "nitrogen"
                    ),
                    nitrogen_fallback
                ),

            "phosphorus":
                _safe_text(
                    nutrient_status.get(
                        "phosphorus"
                    ),
                    phosphorus_fallback
                ),

            "potassium":
                _safe_text(
                    nutrient_status.get(
                        "potassium"
                    ),
                    potassium_fallback
                ),

            "ph":
                _safe_text(
                    nutrient_status.get(
                        "ph"
                    ),
                    ph_fallback
                ),

            "organic_carbon":
                _safe_text(
                    nutrient_status.get(
                        "organic_carbon"
                    ),
                    organic_carbon_fallback
                ),

            "electrical_conductivity":
                _safe_text(
                    nutrient_status.get(
                        "electrical_conductivity"
                    ),
                    ec_fallback
                )
        },

        "fertilizer_plan":
            normalized_plan,

        "application_timing":
            _safe_text(
                data.get(
                    "application_timing"
                ),
                "Follow the crop stage and soil-test based recommendation."
            ),

        "application_method":
            _safe_text(
                data.get(
                    "application_method"
                ),
                "Follow label guidance and suitable soil moisture conditions."
            ),

        "soil_improvement":
            soil_improvement,

        "irrigation_note":
            _safe_text(
                data.get(
                    "irrigation_note"
                ),
                "Maintain suitable soil moisture and avoid waterlogging."
            ),

        "warnings":
            warnings
    }

    return result


# ============================================================
# MAIN FERTILIZER ANALYSIS
# ============================================================

def analyze_fertilizer(
    crop_name: str,
    farm: Dict[str, Any],
    soil_data: Dict[str, Any],
    disease_data: Dict[str, Any] = None,
    crop_health_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate fertilizer advice using:

    1. Soil report
    2. Disease detection
    3. Crop health
    4. Farm conditions
    """

    # ========================================================
    # API KEY
    # ========================================================

    if not GROQ_API_KEY:

        return {
            "success": False,
            "error": (
                "GROQ_API_KEY is not configured. "
                "Please add GROQ_API_KEY to your .env file."
            )
        }

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    crop_name = _safe_text(
        crop_name
    )

    if not crop_name:

        return {
            "success": False,
            "error": "Crop name is required."
        }

    if not isinstance(
        farm,
        dict
    ):
        farm = {}

    if not isinstance(
        soil_data,
        dict
    ):
        soil_data = {}

    if not isinstance(
        disease_data,
        dict
    ):
        disease_data = {}

    if not isinstance(
        crop_health_data,
        dict
    ):
        crop_health_data = {}

    # ========================================================
    # DATA AVAILABILITY
    # ========================================================

    soil_available = _has_real_data(
        soil_data
    )

    disease_available = _has_real_data(
        disease_data
    )

    health_available = _has_real_data(
        crop_health_data
    )

    # ========================================================
    # FARM CONTEXT
    # ========================================================

    farm_context = {

        "soil_type":
            _safe_text(
                farm.get(
                    "soil_type"
                )
            ),

        "irrigation":
            _safe_text(
                farm.get(
                    "irrigation"
                )
            ),

        "water_source":
            _safe_text(
                farm.get(
                    "water_source"
                )
            ),

        "season":
            _safe_text(
                farm.get(
                    "season"
                )
            ),

        "previous_crop":
            _safe_text(
                farm.get(
                    "previous_crop"
                )
            ),

        "area":
            _safe_text(
                farm.get(
                    "area"
                )
            ),

        "area_unit":
            _safe_text(
                farm.get(
                    "area_unit"
                )
            )
    }

    # ========================================================
    # SOIL CONTEXT
    # ========================================================

    # IMPORTANT:
    # Your app.py saves pH using "ph", not "pH".

    soil_context = {

        "nitrogen":
            _format_soil_value(
                soil_data.get(
                    "nitrogen"
                ),
                "kg/ha"
            ),

        "phosphorus":
            _format_soil_value(
                soil_data.get(
                    "phosphorus"
                ),
                "kg/ha"
            ),

        "potassium":
            _format_soil_value(
                soil_data.get(
                    "potassium"
                ),
                "kg/ha"
            ),

        "ph":
            _format_soil_value(
                soil_data.get(
                    "ph",
                    soil_data.get("pH")
                )
            ),

        "organic_carbon":
            _format_soil_value(
                soil_data.get(
                    "organic_carbon"
                ),
                "%"
            ),

        "electrical_conductivity":
            _format_soil_value(
                soil_data.get(
                    "electrical_conductivity"
                ),
                "dS/m"
            ),

        "soil_type":
            _safe_text(
                farm.get(
                    "soil_type"
                )
            )
    }

    # ========================================================
    # DISEASE CONTEXT
    # ========================================================

    # Keep this compact.
    # Only information relevant to fertilizer decisions.

    disease_context = {

        "available":
            disease_available,

        "crop":
            _safe_text(
                disease_data.get(
                    "crop"
                )
            ),

        "disease":
            _safe_text(
                disease_data.get(
                    "disease"
                )
            ),

        "confidence":
            _safe_text(
                disease_data.get(
                    "confidence"
                )
            ),

        "severity":
            _safe_text(
                disease_data.get(
                    "severity"
                )
            ),

        "warning":
            _safe_text(
                disease_data.get(
                    "warning"
                )
            )
    }

    # ========================================================
    # CROP HEALTH CONTEXT
    # ========================================================

    # Keep this compact as well.

    health_context = {

        "available":
            health_available,

        "crop":
            _safe_text(
                crop_health_data.get(
                    "crop"
                )
            ),

        "health_status":
            _safe_text(
                crop_health_data.get(
                    "health_status"
                )
            ),

        "health_score":
            _safe_text(
                crop_health_data.get(
                    "health_score"
                )
            ),

        "growth_stage":
            _safe_text(
                crop_health_data.get(
                    "growth_stage"
                )
            ),

        "leaf_condition":
            _safe_text(
                crop_health_data.get(
                    "leaf_condition"
                )
            ),

        "visible_stress":
            _safe_list(
                crop_health_data.get(
                    "visible_stress"
                )
            )[:3],

        "warning":
            _safe_text(
                crop_health_data.get(
                    "warning"
                )
            )
    }

    # ========================================================
    # JSON CONTEXT FOR AI
    # ========================================================

    farm_json = json.dumps(
        farm_context,
        ensure_ascii=False
    )

    soil_json = json.dumps(
        soil_context,
        ensure_ascii=False
    )

    disease_json = json.dumps(
        disease_context,
        ensure_ascii=False
    )

    health_json = json.dumps(
        health_context,
        ensure_ascii=False
    )

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are the fertilizer advisory module of Smart Kisan AI.

Generate a concise fertilizer recommendation for the farmer.

CURRENT CROP:
{crop_name}

FARM INFORMATION:
{farm_json}

SOIL REPORT:
{soil_json}

DISEASE DETECTION:
{disease_json}

CROP HEALTH:
{health_json}


ANALYSIS RULES:

1. Soil report is the PRIMARY basis for fertilizer recommendations.

2. Disease Detection and Crop Health are SUPPORTING evidence.

3. Use disease information only when it is actually available.

4. Use crop-health information only when it is actually available.

5. Do not invent disease, deficiency, stress or symptoms.

6. Disease treatment is not the same as fertilizer application.

7. A disease result does not automatically require extra fertilizer.

8. Crop stress does not automatically mean nutrient deficiency.

9. Do not recommend additional fertilizer for a nutrient merely because
   it is moderate or adequate.

10. Do not invent precise fertilizer doses when reliable crop-specific
    information is not available.

11. Keep recommendations practical and farmer-friendly.

12. Clearly connect soil + disease + crop health to the recommendation.


OUTPUT REQUIREMENTS:

Return exactly ONE complete JSON object.

Return JSON only.
Do not write markdown.
Do not write ```json.
Do not write any text before or after the JSON.

The JSON MUST contain ALL of these top-level keys:

"crop"
"overall_message"
"analysis_basis"
"disease_assessment"
"crop_health_assessment"
"combined_reasoning"
"nutrient_status"
"fertilizer_plan"
"application_timing"
"application_method"
"soil_improvement"
"irrigation_note"
"warnings"

"analysis_basis" MUST contain:

"soil_report_used"
"disease_detection_used"
"crop_health_used"

Use these availability values exactly from the supplied data:

soil_report_used = {str(soil_available).lower()}
disease_detection_used = {str(disease_available).lower()}
crop_health_used = {str(health_available).lower()}

"nutrient_status" MUST contain:

"nitrogen"
"phosphorus"
"potassium"
"ph"
"organic_carbon"
"electrical_conductivity"

"fertilizer_plan" MUST be an array with maximum 2 items.

Each fertilizer item MUST contain:

"fertilizer"
"purpose"
"application_stage"
"guidance"

"soil_improvement" MUST be an array with maximum 2 short items.

"warnings" MUST be an array with maximum 2 short items.

KEEP THE OUTPUT VERY SHORT.

overall_message:
Maximum 18 words.

disease_assessment:
Maximum 25 words.

crop_health_assessment:
Maximum 25 words.

combined_reasoning:
Maximum 30 words.

application_timing:
Maximum 18 words.

application_method:
Maximum 18 words.

irrigation_note:
Maximum 18 words.

nutrient_status:
Use compact values such as:
"High (350 kg/ha)"
"Low (18 kg/ha)"
"Moderate (190 kg/ha)"
"pH 6.8"

fertilizer_plan:
Prefer 1 strong recommendation when appropriate.
Use 2 only when genuinely needed.
Keep every field short.

IMPORTANT:

Output ALL keys.
Do not stop after analysis_basis.
Do not omit any key.
Do not repeat information.
Do not invent missing information.
Use [] when there is no soil improvement recommendation.
Use [] when there is no warning.
If disease is unavailable, say so briefly.
If crop health is unavailable, say so briefly.
"""

    # ========================================================
    # GROQ CLIENT
    # ========================================================

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

    except Exception as error:

        return {
            "success": False,
            "error":
                f"Unable to initialize Groq client: {error}"
        }

    # ========================================================
    # AI REQUEST
    # ========================================================

    try:

        response = client.chat.completions.create(

            model=MODEL,

            temperature=0.1,

            max_completion_tokens=1000,

            reasoning_effort="none",

            response_format={
                "type": "json_object"
            },

            messages=[

                {
                    "role": "user",
                    "content": prompt
                }

            ]
        )

    except Exception as error:

        error_text = str(
            error
        )

        print(
            "Fertilizer AI request error:",
            error_text
        )

        return {
            "success": False,
            "error":
                "Fertilizer AI request failed. "
                + error_text
        }

    # ========================================================
    # EXTRACT RESPONSE
    # ========================================================

    try:

        content = (
            response
            .choices[0]
            .message
            .content
        )

    except Exception as error:

        print(
            "Fertilizer AI response extraction error:",
            error
        )

        return {
            "success": False,
            "error":
                "The AI returned an unexpected response."
        }

    if not content:

        return {
            "success": False,
            "error":
                "The AI returned an empty fertilizer recommendation."
        }

    print(
        "Fertilizer AI response:",
        content
    )

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        parsed = json.loads(
            content
        )

    except (
        TypeError,
        ValueError
    ) as error:

        print(
            "Fertilizer JSON parsing error:",
            error
        )

        return {
            "success": False,
            "error":
                "AI returned invalid fertilizer recommendation data."
        }

    if not isinstance(
        parsed,
        dict
    ):

        return {
            "success": False,
            "error":
                "AI returned an invalid fertilizer response."
        }

    # ========================================================
    # REQUIRED TOP-LEVEL KEYS
    # ========================================================

    required_keys = {

        "crop",

        "overall_message",

        "analysis_basis",

        "disease_assessment",

        "crop_health_assessment",

        "combined_reasoning",

        "nutrient_status",

        "fertilizer_plan",

        "application_timing",

        "application_method",

        "soil_improvement",

        "irrigation_note",

        "warnings"
    }

    missing_keys = [

        key

        for key in required_keys

        if key not in parsed

    ]

    # --------------------------------------------------------
    # IMPORTANT:
    # If the response is incomplete, do NOT show it as
    # "Analysis Complete".
    # --------------------------------------------------------

    if missing_keys:

        print(
            "Fertilizer AI incomplete response. Missing:",
            missing_keys
        )

        return {
            "success": False,
            "error":
                "Fertilizer AI returned an incomplete "
                "recommendation. Missing fields: "
                + ", ".join(
                    sorted(missing_keys)
                )
        }

    # ========================================================
    # NORMALIZE RESULT
    # ========================================================

    result = normalize_result(

        data=parsed,

        crop_name=crop_name,

        soil_data=soil_data,

        soil_available=soil_available,

        disease_data=disease_data,

        disease_available=disease_available,

        crop_health_data=crop_health_data,

        health_available=health_available
    )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {

        "success":
            True,

        "result":
            result
    }