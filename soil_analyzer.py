# =========================================================
# SMART KISAN AI
# SOIL ANALYZER ENGINE
# =========================================================

"""
Soil analysis engine for Smart Kisan AI.

Important:
- Manual laboratory values are preferred.
- Uploaded PDF/image reports are optional.
- N/P/K values are treated as kg/ha.
- Organic carbon is treated as percent.
- Results are screening/advisory results, not a substitute
  for a laboratory's crop-specific fertilizer prescription.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


# =========================================================
# SAFE NUMBER
# =========================================================

def safe_float(value) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")

    if not text:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def normalize_text(value) -> str:
    return str(value or "").strip().lower()


# =========================================================
# PARAMETER ANALYSIS
# =========================================================

def analyze_ph(ph: Optional[float]) -> Dict[str, Any]:
    if ph is None:
        return {
            "status": "Not provided",
            "level": "unknown",
            "message": "Soil pH was not provided.",
            "recommendation":
                "Enter the pH value from the laboratory soil report."
        }

    if ph < 4.5:
        return {
            "status": "Strongly acidic",
            "level": "critical",
            "message": "The soil is strongly acidic.",
            "recommendation":
                "Acidity correction may be required. Do not apply lime "
                "blindly; use laboratory and local soil-testing guidance."
        }

    if ph < 5.5:
        return {
            "status": "Acidic",
            "level": "low",
            "message": "The soil is acidic.",
            "recommendation":
                "Check lime requirement from a soil laboratory before "
                "applying amendments."
        }

    if ph < 6.5:
        return {
            "status": "Slightly acidic",
            "level": "good",
            "message": "pH is generally suitable for many crops.",
            "recommendation":
                "Maintain organic matter and monitor pH periodically."
        }

    if ph <= 7.5:
        return {
            "status": "Near neutral",
            "level": "excellent",
            "message": "pH is generally favorable for many crops.",
            "recommendation":
                "Maintain balanced nutrient management and organic matter."
        }

    if ph <= 8.5:
        return {
            "status": "Alkaline",
            "level": "warning",
            "message": "The soil is alkaline.",
            "recommendation":
                "Increase organic matter and follow soil-test-based "
                "amendment recommendations."
        }

    return {
        "status": "Strongly alkaline",
        "level": "critical",
        "message": "The soil is strongly alkaline.",
        "recommendation":
            "Use a laboratory-based amendment plan and monitor "
            "salinity/sodicity where relevant."
    }


def analyze_organic_carbon(
    organic_carbon: Optional[float]
) -> Dict[str, Any]:
    if organic_carbon is None:
        return {
            "status": "Not provided",
            "level": "unknown",
            "message": "Organic carbon was not provided.",
            "recommendation":
                "Enter organic carbon (%) from the soil report."
        }

    if organic_carbon < 0.40:
        return {
            "status": "Low",
            "level": "low",
            "message": "Organic carbon is low.",
            "recommendation":
                "Increase organic matter through well-decomposed "
                "farmyard manure, compost and suitable green manure."
        }

    if organic_carbon < 0.75:
        return {
            "status": "Medium",
            "level": "good",
            "message": "Organic carbon is in a moderate range.",
            "recommendation":
                "Maintain organic matter inputs and avoid unnecessary "
                "removal or burning of crop residues."
        }

    return {
        "status": "High",
        "level": "excellent",
        "message": "Organic carbon is relatively high.",
        "recommendation":
            "Maintain the current organic-matter management practices."
    }


def analyze_nitrogen(nitrogen: Optional[float]) -> Dict[str, Any]:
    if nitrogen is None:
        return {
            "status": "Not provided",
            "level": "unknown",
            "message": "Available nitrogen was not provided.",
            "recommendation":
                "Enter available N in kg/ha from the soil report."
        }

    if nitrogen < 280:
        return {
            "status": "Low",
            "level": "low",
            "message": "Available nitrogen is in the low screening range.",
            "recommendation":
                "Use soil-test-based nitrogen management and prefer "
                "split application according to crop stage."
        }

    if nitrogen <= 560:
        return {
            "status": "Medium",
            "level": "good",
            "message": "Available nitrogen is in the medium screening range.",
            "recommendation":
                "Use balanced nitrogen application and avoid excessive "
                "nitrogen."
        }

    return {
        "status": "High",
        "level": "excellent",
        "message": "Available nitrogen is relatively high.",
        "recommendation":
            "Avoid unnecessary additional nitrogen and follow "
            "crop-specific soil-test recommendations."
    }


def analyze_phosphorus(phosphorus: Optional[float]) -> Dict[str, Any]:
    if phosphorus is None:
        return {
            "status": "Not provided",
            "level": "unknown",
            "message": "Available phosphorus was not provided.",
            "recommendation":
                "Enter available P in kg/ha from the soil report."
        }

    if phosphorus < 22:
        return {
            "status": "Low",
            "level": "low",
            "message": "Available phosphorus is in the low screening range.",
            "recommendation":
                "Phosphorus correction may be required depending on "
                "crop requirement and the exact soil-test rating."
        }

    if phosphorus <= 55:
        return {
            "status": "Medium",
            "level": "good",
            "message":
                "Available phosphorus is in the medium screening range.",
            "recommendation":
                "Maintain balanced phosphorus management based on crop "
                "requirement and soil testing."
        }

    return {
        "status": "High",
        "level": "excellent",
        "message": "Available phosphorus is relatively high.",
        "recommendation":
            "Avoid unnecessary phosphorus application."
    }


def analyze_potassium(potassium: Optional[float]) -> Dict[str, Any]:
    if potassium is None:
        return {
            "status": "Not provided",
            "level": "unknown",
            "message": "Available potassium was not provided.",
            "recommendation":
                "Enter available K in kg/ha from the soil report."
        }

    if potassium < 140:
        return {
            "status": "Low",
            "level": "low",
            "message": "Available potassium is in the low screening range.",
            "recommendation":
                "Potassium management may be required depending on crop "
                "demand and the laboratory soil-test rating."
        }

    if potassium <= 280:
        return {
            "status": "Medium",
            "level": "good",
            "message":
                "Available potassium is in the medium screening range.",
            "recommendation":
                "Maintain balanced potassium application according "
                "to crop requirement."
        }

    return {
        "status": "High",
        "level": "excellent",
        "message": "Available potassium is relatively high.",
        "recommendation":
            "Avoid unnecessary potassium application."
    }


# =========================================================
# SCORE
# =========================================================

def parameter_score(result: Dict[str, Any]) -> int:
    return {
        "excellent": 100,
        "good": 80,
        "warning": 60,
        "low": 45,
        "critical": 25,
        "unknown": 0
    }.get(result.get("level", "unknown"), 0)


def calculate_soil_score(*results) -> int:
    known = [
        parameter_score(result)
        for result in results
        if result.get("level") != "unknown"
    ]

    if not known:
        return 0

    return int(round(sum(known) / len(known)))


def score_label(score: int) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Needs Attention"
    return "Poor"


# =========================================================
# RECOMMENDATIONS
# =========================================================

def find_priorities(results):
    names = {
        "pH": "Soil pH",
        "organic_carbon": "Organic carbon",
        "nitrogen": "Nitrogen",
        "phosphorus": "Phosphorus",
        "potassium": "Potassium"
    }

    priorities = []

    for key, name in names.items():
        result = results.get(key, {})
        if result.get("level") in (
            "critical",
            "low",
            "warning"
        ):
            priorities.append({
                "parameter": name,
                "status": result.get("status", "Needs attention"),
                "recommendation":
                    result.get("recommendation", "")
            })

    return priorities


def general_recommendations(
    results,
    soil_type="",
    season="",
    crop=""
):
    recommendations = []

    if results.get("organic_carbon", {}).get("level") == "low":
        recommendations.append(
            "Increase organic matter using well-decomposed organic "
            "inputs and suitable crop-residue management."
        )

    if results.get("nitrogen", {}).get("level") == "low":
        recommendations.append(
            "Manage nitrogen according to crop requirement and "
            "soil-test recommendation, preferably through split applications."
        )

    if results.get("phosphorus", {}).get("level") == "low":
        recommendations.append(
            "Phosphorus may need correction based on crop requirement "
            "and the soil-test recommendation."
        )

    if results.get("potassium", {}).get("level") == "low":
        recommendations.append(
            "Potassium may need correction based on crop demand "
            "and the soil-test rating."
        )

    soil = normalize_text(soil_type)

    if "black" in soil:
        recommendations.append(
            "Black soil commonly has good moisture-holding capacity. "
            "Avoid unnecessary irrigation and maintain good drainage."
        )
    elif "sandy" in soil:
        recommendations.append(
            "Sandy soil generally benefits from frequent, smaller "
            "irrigation and organic-matter improvement."
        )
    elif "clay" in soil:
        recommendations.append(
            "Clay soil may hold water strongly. Avoid working soil "
            "when excessively wet and maintain proper drainage."
        )
    elif "laterite" in soil:
        recommendations.append(
            "Lateritic soils can be acidic and nutrient-poor in some "
            "locations, so soil-test-based amendment is important."
        )

    if crop:
        recommendations.append(
            f"For planned crop '{crop}', use the crop-specific "
            "fertilizer recommendation from the soil test rather "
            "than a generic fertilizer dose."
        )

    if season:
        recommendations.append(
            f"Current season recorded as {season}. Nutrient and "
            "irrigation decisions should also consider crop stage "
            "and current weather."
        )

    if not recommendations:
        recommendations.append(
            "Maintain balanced fertilization, organic matter, "
            "appropriate irrigation and regular soil testing."
        )

    return recommendations


def fertilizer_guidance(results):
    guidance = []

    for key, name in (
        ("nitrogen", "Nitrogen"),
        ("phosphorus", "Phosphorus"),
        ("potassium", "Potassium")
    ):
        result = results.get(key, {})
        level = result.get("level")

        if level == "low":
            guidance.append({
                "nutrient": name,
                "action": "Potentially required",
                "reason": result.get("message", ""),
                "note":
                    "Final dose must be based on crop requirement "
                    "and the laboratory recommendation."
            })
        elif level == "excellent":
            guidance.append({
                "nutrient": name,
                "action": "Avoid unnecessary application",
                "reason": result.get("message", ""),
                "note":
                    "Do not add fertilizer simply because more nutrient "
                    "does not always mean higher yield."
            })

    if not guidance:
        guidance.append({
            "nutrient": "NPK",
            "action": "Balanced management",
            "reason":
                "No major NPK deficiency was detected in the "
                "available screening values.",
            "note":
                "Continue soil-test-based nutrient management."
        })

    return guidance


# =========================================================
# VALIDATION
# =========================================================

def validate_values(values):
    errors = []

    ph = safe_float(values.get("ph"))
    oc = safe_float(values.get("organic_carbon"))
    n = safe_float(values.get("nitrogen"))
    p = safe_float(values.get("phosphorus"))
    k = safe_float(values.get("potassium"))

    if ph is not None and not 2 <= ph <= 12:
        errors.append("pH must be between 2 and 12.")

    if oc is not None and not 0 <= oc <= 20:
        errors.append("Organic carbon percentage appears invalid.")

    for label, value in (
        ("Nitrogen", n),
        ("Phosphorus", p),
        ("Potassium", k)
    ):
        if value is not None and value < 0:
            errors.append(f"{label} cannot be negative.")

    return errors


# =========================================================
# MAIN ANALYSIS
# =========================================================

def analyze_soil(
    *,
    ph=None,
    organic_carbon=None,
    nitrogen=None,
    phosphorus=None,
    potassium=None,
    soil_type="",
    season="",
    crop="",
    farm_name="",
    village="",
    taluka="",
    district="",
    state="Maharashtra"
):
    values = {
        "ph": ph,
        "organic_carbon": organic_carbon,
        "nitrogen": nitrogen,
        "phosphorus": phosphorus,
        "potassium": potassium
    }

    errors = validate_values(values)

    if errors:
        raise ValueError(" ".join(errors))

    ph_value = safe_float(ph)
    oc_value = safe_float(organic_carbon)
    n_value = safe_float(nitrogen)
    p_value = safe_float(phosphorus)
    k_value = safe_float(potassium)

    results = {
        "pH": analyze_ph(ph_value),
        "organic_carbon": analyze_organic_carbon(oc_value),
        "nitrogen": analyze_nitrogen(n_value),
        "phosphorus": analyze_phosphorus(p_value),
        "potassium": analyze_potassium(k_value)
    }

    score = calculate_soil_score(*results.values())

    provided = sum(
        value is not None
        for value in (
            ph_value,
            oc_value,
            n_value,
            p_value,
            k_value
        )
    )

    if provided == 0:
        summary = (
            "No laboratory soil values were provided. "
            "Enter the values from your soil report for a meaningful analysis."
        )
    elif score >= 85:
        summary = (
            "The available soil values indicate generally favorable "
            "soil conditions. Continue balanced soil and nutrient management."
        )
    elif score >= 70:
        summary = (
            "The soil appears generally suitable, but some parameters "
            "should be monitored and managed."
        )
    elif score >= 55:
        summary = (
            "The soil needs attention in one or more important parameters. "
            "Follow soil-test-based management."
        )
    else:
        summary = (
            "The available values indicate important soil management "
            "concerns. Consider professional soil testing before major "
            "input applications."
        )

    return {
        "success": True,
        "score": score,
        "score_label": score_label(score),
        "summary": summary,
        "farm": {
            "farm_name": farm_name,
            "village": village,
            "taluka": taluka,
            "district": district,
            "state": state
        },
        "inputs": {
            "ph": ph_value,
            "organic_carbon": oc_value,
            "nitrogen": n_value,
            "phosphorus": p_value,
            "potassium": k_value,
            "soil_type": soil_type,
            "season": season,
            "crop": crop
        },
        "analysis": results,
        "priorities": find_priorities(results),
        "recommendations": general_recommendations(
            results,
            soil_type,
            season,
            crop
        ),
        "fertilizer_guidance": fertilizer_guidance(results),
        "data_quality": {
            "parameters_provided": provided,
            "total_parameters": 5,
            "message":
                "Analysis is based only on the soil parameters "
                "provided by the user."
        }
    }


# =========================================================
# REPORT TEXT EXTRACTION
# =========================================================

def extract_soil_values_from_text(text):
    if not text:
        return {
            "ph": None,
            "organic_carbon": None,
            "nitrogen": None,
            "phosphorus": None,
            "potassium": None
        }

    clean = " ".join(
        str(text).replace("\r", " ").replace("\n", " ").split()
    )

    def find_value(patterns):
        for pattern in patterns:
            match = re.search(
                pattern,
                clean,
                flags=re.IGNORECASE
            )
            if match:
                value = safe_float(match.group(1))
                if value is not None:
                    return value
        return None

    number = r"(\d+(?:\.\d+)?)"

    return {
        "ph": find_value([
            rf"\bpH\s*[:=-]?\s*{number}"
        ]),
        "organic_carbon": find_value([
            rf"organic\s+carbon\s*(?:\(%?\))?\s*[:=-]?\s*{number}"
        ]),
        "nitrogen": find_value([
            rf"(?:available\s+)?nitrogen\s*(?:\(N\))?\s*[:=-]?\s*{number}"
        ]),
        "phosphorus": find_value([
            rf"(?:available\s+)?phosphorus\s*(?:\(P\))?\s*[:=-]?\s*{number}"
        ]),
        "potassium": find_value([
            rf"(?:available\s+)?potassium\s*(?:\(K\))?\s*[:=-]?\s*{number}"
        ]),
        "electrical_conductivity": find_value([
            rf"(?:electrical\s+conductivity|EC)\s*(?:\(?(?:dS/m|ds/m|mmhos/cm)\)?)?\s*[:=-]?\s*{number}"
        ])
    }


def extract_text_from_pdf(file_stream):
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(file_stream)
        return "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
    except Exception:
        return ""


def extract_text_from_image(file_stream):
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return ""

    try:
        image = Image.open(file_stream)
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def extract_report_values(file_stream, filename):
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        text = extract_text_from_pdf(file_stream)
    elif name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        text = extract_text_from_image(file_stream)
    else:
        text = ""

    values = extract_soil_values_from_text(text)

    return {
        "success": bool(text.strip()),
        "text_found": bool(text.strip()),
        "extracted": values,
        "raw_text_preview": text[:3000]
    }


# =========================================================
# APP-FACING WRAPPER
# =========================================================

def analyze_soil_report(form_data=None, farm=None):
    form_data = form_data or {}
    farm = farm or {}

    # Values supplied by the manual form or report extractor.
    values = {
        "ph": form_data.get("ph"),
        "organic_carbon": form_data.get("organic_carbon"),
        "nitrogen": form_data.get("nitrogen"),
        "phosphorus": form_data.get("phosphorus"),
        "potassium": form_data.get("potassium"),
        "electrical_conductivity": form_data.get(
            "electrical_conductivity"
        )
    }

    result = analyze_soil(
        ph=values["ph"],
        organic_carbon=values["organic_carbon"],
        nitrogen=values["nitrogen"],
        phosphorus=values["phosphorus"],
        potassium=values["potassium"],
        soil_type=form_data.get(
            "soil_type",
            farm.get("soil_type", "")
        ),
        season=form_data.get(
            "season",
            farm.get("season", "")
        ),
        crop=form_data.get("crop", ""),
        farm_name=farm.get("farm_name", ""),
        village=farm.get("village", ""),
        taluka=farm.get("taluka", ""),
        district=farm.get("district", ""),
        state=farm.get("state", "Maharashtra")
    )

    # EC is extracted and preserved for downstream crop recommendation,
    # even though the current soil-health score does not include EC.
    result.setdefault("inputs", {})
    result["inputs"]["electrical_conductivity"] = safe_float(
        values.get("electrical_conductivity")
    )

    return result
