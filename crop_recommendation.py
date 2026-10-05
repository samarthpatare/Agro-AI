# =========================================================
# SMART KISAN AI
# CROP RECOMMENDATION ENGINE V2
# =========================================================
#
# Hybrid Maharashtra Crop Recommendation System
#
# Inputs:
#   - Farm region / district
#   - Soil type
#   - Farm area
#   - Irrigation
#   - Water source
#   - Season
#   - Previous crop
#   - Soil N, P, K
#   - pH
#   - Organic Carbon
#   - EC
#
# Output:
#   - Ranked crop recommendations
#   - Suitability score
#   - Region suitability
#   - Soil suitability
#   - Season suitability
#   - Irrigation suitability
#   - Soil parameter analysis
#   - Reasons
#   - Warnings
#
# =========================================================


from __future__ import annotations

from typing import Any, Dict, List, Optional
import math
import os
import csv


# =========================================================
# CONFIGURATION
# =========================================================

DATASET_FILENAME = "smartkisan_maharashtra_crop_recommendation_5000.csv"


# =========================================================
# MAHARASHTRA REGIONS
# =========================================================

REGIONS = {

    "konkan": [
        "Mumbai City",
        "Mumbai Suburban",
        "Palghar",
        "Thane",
        "Raigad",
        "Ratnagiri",
        "Sindhudurg"
    ],

    "western_maharashtra": [
        "Pune",
        "Satara",
        "Sangli",
        "Kolhapur",
        "Solapur"
    ],

    "marathwada": [
        "Chhatrapati Sambhajinagar",
        "Aurangabad",
        "Jalna",
        "Beed",
        "Dharashiv",
        "Osmanabad",
        "Latur",
        "Nanded",
        "Parbhani",
        "Hingoli"
    ],

    "khandesh": [
        "Nashik",
        "Dhule",
        "Nandurbar",
        "Jalgaon"
    ],

    "vidarbha": [
        "Buldhana",
        "Akola",
        "Washim",
        "Amravati",
        "Yavatmal",
        "Wardha",
        "Nagpur",
        "Bhandara",
        "Gondia",
        "Chandrapur",
        "Gadchiroli"
    ]
}


# =========================================================
# REGION NORMALIZATION
# =========================================================

REGION_ALIASES = {

    "konkan": "konkan",

    "western maharashtra": "western_maharashtra",
    "western_maharashtra": "western_maharashtra",
    "desh": "western_maharashtra",

    "marathwada": "marathwada",

    "khandesh": "khandesh",

    "vidarbha": "vidarbha"
}


# =========================================================
# CROP KNOWLEDGE BASE
# =========================================================
#
# This is the core agronomic rule layer.
#
# Scores are NOT probabilities.
# They represent suitability used for ranking.
#
# =========================================================

CROP_DATABASE = {

    # =====================================================
    # CEREALS
    # =====================================================

    "Rice": {

        "category": "Cereal",

        "regions": [
            "konkan",
            "western_maharashtra",
            "vidarbha"
        ],

        "seasons": [
            "kharif"
        ],

        "soils": [
            "laterite",
            "alluvial",
            "red",
            "black cotton"
        ],

        "irrigation": [
            "rainfed",
            "canal",
            "well",
            "borewell",
            "drip",
            "sprinkler"
        ],

        "water_need": "high",

        "ph": (5.0, 7.5),

        "nitrogen": (40, 150),
        "phosphorus": (20, 80),
        "potassium": (30, 150),
        "organic_carbon": (0.5, 2.0),

        "temperature": (20, 35),
        "rainfall": (800, 3000),

        "preferred_regions": {
            "konkan": 1.00,
            "western_maharashtra": 0.65,
            "vidarbha": 0.55,
            "marathwada": 0.25,
            "khandesh": 0.40
        }
    },


    "Jowar": {

        "category": "Cereal",

        "regions": [
            "western_maharashtra",
            "marathwada",
            "khandesh",
            "vidarbha"
        ],

        "seasons": [
            "kharif",
            "rabi"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "canal",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "medium",

        "ph": (5.5, 8.0),

        "nitrogen": (30, 130),
        "phosphorus": (15, 70),
        "potassium": (30, 150),
        "organic_carbon": (0.4, 1.5),

        "temperature": (20, 35),
        "rainfall": (400, 1000),

        "preferred_regions": {
            "western_maharashtra": 0.95,
            "marathwada": 0.95,
            "khandesh": 0.80,
            "vidarbha": 0.75,
            "konkan": 0.35
        }
    },


    "Maize": {

        "category": "Cereal",

        "regions": [
            "western_maharashtra",
            "khandesh",
            "marathwada",
            "vidarbha"
        ],

        "seasons": [
            "kharif",
            "rabi",
            "zaid"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "canal",
            "well",
            "borewell",
            "drip",
            "sprinkler"
        ],

        "water_need": "medium",

        "ph": (5.5, 7.5),

        "nitrogen": (50, 180),
        "phosphorus": (20, 80),
        "potassium": (30, 160),
        "organic_carbon": (0.5, 1.8),

        "temperature": (18, 35),
        "rainfall": (500, 1200),

        "preferred_regions": {
            "western_maharashtra": 0.90,
            "khandesh": 0.90,
            "marathwada": 0.80,
            "vidarbha": 0.85,
            "konkan": 0.50
        }
    },


    # =====================================================
    # PULSES
    # =====================================================

    "Tur": {

        "category": "Pulse",

        "regions": [
            "western_maharashtra",
            "marathwada",
            "vidarbha",
            "khandesh"
        ],

        "seasons": [
            "kharif"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "low",

        "ph": (5.5, 8.0),

        "nitrogen": (20, 100),
        "phosphorus": (15, 70),
        "potassium": (20, 130),
        "organic_carbon": (0.3, 1.5),

        "temperature": (20, 35),
        "rainfall": (500, 1000),

        "preferred_regions": {
            "marathwada": 0.95,
            "vidarbha": 0.90,
            "western_maharashtra": 0.90,
            "khandesh": 0.85,
            "konkan": 0.40
        }
    },


    "Gram": {

        "category": "Pulse",

        "regions": [
            "western_maharashtra",
            "marathwada",
            "khandesh",
            "vidarbha"
        ],

        "seasons": [
            "rabi"
        ],

        "soils": [
            "black cotton",
            "alluvial",
            "red"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell",
            "canal"
        ],

        "water_need": "low",

        "ph": (6.0, 8.0),

        "nitrogen": (20, 90),
        "phosphorus": (15, 60),
        "potassium": (20, 120),
        "organic_carbon": (0.3, 1.5),

        "temperature": (18, 30),
        "rainfall": (350, 700),

        "preferred_regions": {
            "western_maharashtra": 0.95,
            "marathwada": 0.95,
            "khandesh": 0.90,
            "vidarbha": 0.85,
            "konkan": 0.30
        }
    },


    "Green Gram": {

        "category": "Pulse",

        "regions": [
            "western_maharashtra",
            "marathwada",
            "khandesh",
            "vidarbha"
        ],

        "seasons": [
            "kharif",
            "zaid"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "low",

        "ph": (6.0, 7.5),

        "nitrogen": (20, 80),
        "phosphorus": (15, 60),
        "potassium": (20, 100),
        "organic_carbon": (0.3, 1.3),

        "temperature": (25, 35),
        "rainfall": (400, 800),

        "preferred_regions": {
            "western_maharashtra": 0.90,
            "marathwada": 0.90,
            "khandesh": 0.85,
            "vidarbha": 0.85,
            "konkan": 0.35
        }
    },


    # =====================================================
    # OILSEEDS
    # =====================================================

    "Soybean": {

        "category": "Oilseed",

        "regions": [
            "marathwada",
            "vidarbha",
            "western_maharashtra",
            "khandesh"
        ],

        "seasons": [
            "kharif"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (6.0, 7.5),

        "nitrogen": (30, 120),
        "phosphorus": (20, 80),
        "potassium": (30, 150),
        "organic_carbon": (0.5, 1.8),

        "temperature": (20, 32),
        "rainfall": (600, 1100),

        "preferred_regions": {
            "marathwada": 1.00,
            "vidarbha": 0.95,
            "western_maharashtra": 0.80,
            "khandesh": 0.80,
            "konkan": 0.35
        }
    },


    "Groundnut": {

        "category": "Oilseed",

        "regions": [
            "western_maharashtra",
            "khandesh",
            "vidarbha",
            "marathwada"
        ],

        "seasons": [
            "kharif",
            "zaid"
        ],

        "soils": [
            "red",
            "alluvial",
            "black cotton"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "medium",

        "ph": (5.5, 7.5),

        "nitrogen": (20, 100),
        "phosphorus": (20, 70),
        "potassium": (30, 120),
        "organic_carbon": (0.3, 1.3),

        "temperature": (24, 35),
        "rainfall": (500, 1000),

        "preferred_regions": {
            "western_maharashtra": 0.90,
            "khandesh": 0.85,
            "vidarbha": 0.80,
            "marathwada": 0.75,
            "konkan": 0.45
        }
    },


    # =====================================================
    # FIBER / CASH CROP
    # =====================================================

    "Cotton": {

        "category": "Fiber / Cash Crop",

        "regions": [
            "marathwada",
            "vidarbha",
            "khandesh",
            "western_maharashtra"
        ],

        "seasons": [
            "kharif"
        ],

        "soils": [
            "black cotton",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "medium",

        "ph": (6.0, 8.0),

        "nitrogen": (40, 160),
        "phosphorus": (20, 80),
        "potassium": (40, 180),
        "organic_carbon": (0.4, 1.8),

        "temperature": (21, 35),
        "rainfall": (500, 1000),

        "preferred_regions": {
            "vidarbha": 1.00,
            "marathwada": 0.95,
            "khandesh": 0.90,
            "western_maharashtra": 0.45,
            "konkan": 0.10
        }
    },


    "Sugarcane": {

        "category": "Cash Crop",

        "regions": [
            "western_maharashtra",
            "khandesh",
            "marathwada"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "black cotton",
            "alluvial",
            "red"
        ],

        "irrigation": [
            "canal",
            "well",
            "borewell",
            "drip"
        ],

        "water_need": "very_high",

        "ph": (6.0, 8.0),

        "nitrogen": (80, 220),
        "phosphorus": (30, 100),
        "potassium": (80, 250),
        "organic_carbon": (0.5, 2.0),

        "temperature": (20, 35),
        "rainfall": (750, 1500),

        "preferred_regions": {
            "western_maharashtra": 1.00,
            "khandesh": 0.80,
            "marathwada": 0.65,
            "vidarbha": 0.35,
            "konkan": 0.35
        }
    },


    # =====================================================
    # VEGETABLES
    # =====================================================

    "Onion": {

        "category": "Vegetable",

        "regions": [
            "khandesh",
            "western_maharashtra",
            "marathwada"
        ],

        "seasons": [
            "kharif",
            "rabi",
            "zaid"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "well",
            "borewell",
            "drip",
            "canal"
        ],

        "water_need": "medium",

        "ph": (6.0, 7.5),

        "nitrogen": (40, 140),
        "phosphorus": (20, 80),
        "potassium": (40, 180),
        "organic_carbon": (0.4, 1.5),

        "temperature": (13, 30),
        "rainfall": (500, 1000),

        "preferred_regions": {
            "khandesh": 1.00,
            "western_maharashtra": 0.95,
            "marathwada": 0.80,
            "vidarbha": 0.70,
            "konkan": 0.45
        }
    },


    "Tomato": {

        "category": "Vegetable",

        "regions": [
            "western_maharashtra",
            "khandesh",
            "marathwada",
            "vidarbha",
            "konkan"
        ],

        "seasons": [
            "kharif",
            "rabi",
            "zaid"
        ],

        "soils": [
            "red",
            "alluvial",
            "black cotton"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell",
            "canal"
        ],

        "water_need": "medium",

        "ph": (5.5, 7.5),

        "nitrogen": (50, 160),
        "phosphorus": (30, 100),
        "potassium": (60, 200),
        "organic_carbon": (0.5, 1.8),

        "temperature": (18, 30),
        "rainfall": (500, 1200),

        "preferred_regions": {
            "western_maharashtra": 0.95,
            "khandesh": 0.85,
            "marathwada": 0.75,
            "vidarbha": 0.75,
            "konkan": 0.70
        }
    },


    "Potato": {

        "category": "Vegetable",

        "regions": [
            "western_maharashtra",
            "khandesh"
        ],

        "seasons": [
            "rabi"
        ],

        "soils": [
            "red",
            "alluvial",
            "black cotton"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (5.0, 7.0),

        "nitrogen": (50, 150),
        "phosphorus": (30, 100),
        "potassium": (60, 180),
        "organic_carbon": (0.5, 1.8),

        "temperature": (12, 25),
        "rainfall": (400, 800),

        "preferred_regions": {
            "western_maharashtra": 0.85,
            "khandesh": 0.80,
            "marathwada": 0.45,
            "vidarbha": 0.45,
            "konkan": 0.25
        }
    },


    "Chilli": {

        "category": "Vegetable / Spice",

        "regions": [
            "western_maharashtra",
            "khandesh",
            "marathwada",
            "vidarbha"
        ],

        "seasons": [
            "kharif",
            "rabi"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (5.5, 7.5),

        "nitrogen": (40, 140),
        "phosphorus": (20, 80),
        "potassium": (50, 180),
        "organic_carbon": (0.4, 1.5),

        "temperature": (20, 32),
        "rainfall": (600, 1200),

        "preferred_regions": {
            "western_maharashtra": 0.90,
            "khandesh": 0.85,
            "marathwada": 0.75,
            "vidarbha": 0.75,
            "konkan": 0.50
        }
    },


    # =====================================================
    # FRUITS
    # =====================================================

    "Grapes": {

        "category": "Fruit",

        "regions": [
            "khandesh",
            "western_maharashtra"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "red",
            "alluvial",
            "black cotton"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (6.0, 7.5),

        "nitrogen": (40, 140),
        "phosphorus": (20, 80),
        "potassium": (60, 200),
        "organic_carbon": (0.5, 1.8),

        "temperature": (15, 35),
        "rainfall": (500, 900),

        "preferred_regions": {
            "khandesh": 1.00,
            "western_maharashtra": 0.90,
            "marathwada": 0.50,
            "vidarbha": 0.40,
            "konkan": 0.20
        }
    },


    "Banana": {

        "category": "Fruit",

        "regions": [
            "khandesh",
            "western_maharashtra",
            "marathwada"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "alluvial",
            "black cotton"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell",
            "canal"
        ],

        "water_need": "high",

        "ph": (6.0, 7.5),

        "nitrogen": (60, 180),
        "phosphorus": (25, 100),
        "potassium": (100, 300),
        "organic_carbon": (0.6, 2.0),

        "temperature": (20, 35),
        "rainfall": (800, 2000),

        "preferred_regions": {
            "khandesh": 1.00,
            "western_maharashtra": 0.75,
            "marathwada": 0.65,
            "vidarbha": 0.45,
            "konkan": 0.50
        }
    },


    "Pomegranate": {

        "category": "Fruit",

        "regions": [
            "western_maharashtra",
            "marathwada"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "black cotton",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "drip",
            "well",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (6.0, 8.0),

        "nitrogen": (40, 140),
        "phosphorus": (20, 80),
        "potassium": (60, 200),
        "organic_carbon": (0.4, 1.8),

        "temperature": (20, 38),
        "rainfall": (400, 800),

        "preferred_regions": {
            "western_maharashtra": 1.00,
            "marathwada": 0.90,
            "khandesh": 0.65,
            "vidarbha": 0.45,
            "konkan": 0.20
        }
    },


    "Mango": {

        "category": "Fruit",

        "regions": [
            "konkan",
            "western_maharashtra"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "laterite",
            "red",
            "alluvial"
        ],

        "irrigation": [
            "rainfed",
            "well",
            "drip",
            "borewell"
        ],

        "water_need": "medium",

        "ph": (5.5, 7.5),

        "nitrogen": (30, 120),
        "phosphorus": (15, 70),
        "potassium": (40, 180),
        "organic_carbon": (0.6, 2.0),

        "temperature": (20, 35),
        "rainfall": (700, 2500),

        "preferred_regions": {
            "konkan": 1.00,
            "western_maharashtra": 0.60,
            "marathwada": 0.30,
            "khandesh": 0.30,
            "vidarbha": 0.30
        }
    },


    "Cashew": {

        "category": "Fruit / Plantation",

        "regions": [
            "konkan"
        ],

        "seasons": [
            "perennial"
        ],

        "soils": [
            "laterite",
            "red"
        ],

        "irrigation": [
            "rainfed",
            "drip",
            "well"
        ],

        "water_need": "low",

        "ph": (5.0, 7.0),

        "nitrogen": (20, 100),
        "phosphorus": (15, 60),
        "potassium": (30, 140),
        "organic_carbon": (0.5, 2.0),

        "temperature": (20, 35),
        "rainfall": (1000, 3000),

        "preferred_regions": {
            "konkan": 1.00,
            "western_maharashtra": 0.25,
            "marathwada": 0.05,
            "khandesh": 0.15,
            "vidarbha": 0.15
        }
    }

}


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value).strip().lower()

    text = (
        text.replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
    )

    return " ".join(text.split())


# =========================================================
# NUMBER CONVERSION
# =========================================================

def safe_float(value: Any) -> Optional[float]:

    if value is None:
        return None

    if isinstance(value, (int, float)):

        if math.isfinite(float(value)):
            return float(value)

        return None

    try:

        text = str(value).strip()

        if not text:
            return None

        number = float(text)

        if math.isfinite(number):
            return number

    except (
        ValueError,
        TypeError
    ):
        pass

    return None


# =========================================================
# SEASON NORMALIZATION
# =========================================================

def normalize_season(value: Any) -> str:

    text = normalize_text(value)

    if text in (
        "kharif",
        "monsoon",
        "rainy"
    ):
        return "kharif"

    if text in (
        "rabi",
        "winter"
    ):
        return "rabi"

    if text in (
        "zaid",
        "summer",
        "zaid summer"
    ):
        return "zaid"

    if text in (
        "perennial",
        "annual plantation"
    ):
        return "perennial"

    return text


# =========================================================
# SOIL NORMALIZATION
# =========================================================

def normalize_soil(value: Any) -> str:

    text = normalize_text(value)

    if "black" in text:

        return "black cotton"

    if "cotton" in text:

        return "black cotton"

    if "laterite" in text:

        return "laterite"

    if "alluvial" in text:

        return "alluvial"

    if "red" in text:

        return "red"

    return text


# =========================================================
# REGION DETECTION
# =========================================================

def get_region(
    district: Any = None,
    region: Any = None
) -> str:

    region_text = normalize_text(region)

    if region_text in REGION_ALIASES:

        return REGION_ALIASES[
            region_text
        ]

    district_text = normalize_text(
        district
    )

    for region_name, districts in REGIONS.items():

        for district_name in districts:

            if normalize_text(
                district_name
            ) == district_text:

                return region_name

    return ""


# =========================================================
# DISTRICT NORMALIZATION
# =========================================================

DISTRICT_ALIASES = {

    "aurangabad": "Chhatrapati Sambhajinagar",
    "chhatrapati sambhajinagar":
        "Chhatrapati Sambhajinagar",

    "osmanabad": "Dharashiv",
    "dharashiv": "Dharashiv"
}


def normalize_district(
    district: Any
) -> str:

    text = normalize_text(
        district
    )

    return DISTRICT_ALIASES.get(
        text,
        str(district).strip()
        if district is not None
        else ""
    )


# =========================================================
# RANGE SCORE
# =========================================================

def range_score(
    value: Optional[float],
    minimum: float,
    maximum: float
) -> float:

    if value is None:
        return 0.50

    if minimum <= value <= maximum:

        return 1.00

    distance = (
        minimum - value
        if value < minimum
        else value - maximum
    )

    range_width = max(
        maximum - minimum,
        0.001
    )

    penalty = min(
        distance / range_width,
        1.0
    )

    return max(
        0.0,
        1.0 - penalty
    )


# =========================================================
# REGIONAL SCORE
# =========================================================

def regional_score(
    crop_data: Dict[str, Any],
    region: str
) -> float:

    if not region:
        return 0.50

    preferred = crop_data.get(
        "preferred_regions",
        {}
    )

    if region in preferred:

        return float(
            preferred[region]
        )

    if region in crop_data.get(
        "regions",
        []
    ):

        return 0.70

    return 0.10


# =========================================================
# SEASON SCORE
# =========================================================

def season_score(
    crop_data: Dict[str, Any],
    season: str
) -> float:

    if not season:
        return 0.50

    seasons = crop_data.get(
        "seasons",
        []
    )

    if season in seasons:

        return 1.00

    return 0.15


# =========================================================
# SOIL SCORE
# =========================================================

def soil_score(
    crop_data: Dict[str, Any],
    soil_type: str
) -> float:

    if not soil_type:
        return 0.50

    soils = crop_data.get(
        "soils",
        []
    )

    if soil_type in soils:

        return 1.00

    return 0.25


# =========================================================
# IRRIGATION SCORE
# =========================================================

def irrigation_score(
    crop_data: Dict[str, Any],
    irrigation: str
) -> float:

    if not irrigation:
        return 0.50

    irrigation = normalize_text(
        irrigation
    )

    allowed = [
        normalize_text(item)
        for item in crop_data.get(
            "irrigation",
            []
        )
    ]

    if irrigation in allowed:
        return 1.00

    return 0.30


# =========================================================
# WATER REQUIREMENT SCORE
# =========================================================

def water_requirement_score(
    crop_data: Dict[str, Any],
    irrigation: str
) -> float:

    irrigation = normalize_text(
        irrigation
    )

    water_need = crop_data.get(
        "water_need",
        "medium"
    )

    if water_need == "very_high":

        if irrigation in (
            "drip",
            "canal",
            "well",
            "borewell"
        ):
            return 1.00

        if irrigation == "rainfed":
            return 0.20

    if water_need == "high":

        if irrigation in (
            "drip",
            "canal",
            "well",
            "borewell"
        ):
            return 1.00

        if irrigation == "rainfed":
            return 0.50

    if water_need == "medium":

        if irrigation:
            return 0.90

        return 0.60

    if water_need == "low":

        if irrigation == "rainfed":
            return 1.00

        return 0.90

    return 0.50


# =========================================================
# PREVIOUS CROP SCORE
# =========================================================

def previous_crop_score(
    crop_name: str,
    previous_crop: str
) -> float:

    previous = normalize_text(
        previous_crop
    )

    current = normalize_text(
        crop_name
    )

    if not previous:
        return 0.50

    if previous == current:
        return 0.40

    # Avoid repeatedly selecting the same crop
    # when the previous crop is identical.

    if (
        current in (
            "soybean",
            "groundnut",
            "green gram",
            "gram",
            "tur"
        )
        and previous in (
            "soybean",
            "groundnut",
            "green gram",
            "gram",
            "tur"
        )
    ):
        return 0.70

    return 1.00


# =========================================================
# FARM AREA SCORE
# =========================================================

def area_score(
    crop_name: str,
    area: Optional[float],
    area_unit: str
) -> float:

    if area is None:
        return 0.50

    area_unit = normalize_text(
        area_unit
    )

    # Convert approximately to acres
    if area_unit in (
        "hectare",
        "hectares"
    ):
        acres = area * 2.47105

    elif area_unit in (
        "guntha",
        "gunthas"
    ):
        acres = area / 40.0

    else:
        acres = area

    # Area is used as a practical factor,
    # not as a biological requirement.

    if acres <= 0:
        return 0.20

    category = CROP_DATABASE[
        crop_name
    ].get(
        "category",
        ""
    )

    if "Fruit" in category:

        if acres >= 1:
            return 1.00

        return 0.75

    if "Cash Crop" in category:

        if acres >= 2:
            return 1.00

        if acres >= 1:
            return 0.90

        return 0.75

    if "Vegetable" in category:

        if acres <= 10:
            return 1.00

        return 0.90

    return 1.00


# =========================================================
# PARAMETER SCORE
# =========================================================

def parameter_scores(
    crop_data: Dict[str, Any],
    values: Dict[str, Optional[float]]
) -> Dict[str, float]:

    scores = {}

    scores["ph"] = range_score(
        values.get("ph"),
        *crop_data["ph"]
    )

    scores["nitrogen"] = range_score(
        values.get("nitrogen"),
        *crop_data["nitrogen"]
    )

    scores["phosphorus"] = range_score(
        values.get("phosphorus"),
        *crop_data["phosphorus"]
    )

    scores["potassium"] = range_score(
        values.get("potassium"),
        *crop_data["potassium"]
    )

    scores["organic_carbon"] = range_score(
        values.get("organic_carbon"),
        *crop_data["organic_carbon"]
    )

    return scores


# =========================================================
# DATASET LOADER
# =========================================================

def load_dataset_records(
    dataset_path: Optional[str] = None
) -> List[Dict[str, Any]]:

    if dataset_path is None:

        dataset_path = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            DATASET_FILENAME
        )

    if not os.path.exists(
        dataset_path
    ):

        return []

    records = []

    try:

        with open(
            dataset_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(
                file
            )

            for row in reader:

                if row:
                    records.append(
                        row
                    )

    except (
        OSError,
        csv.Error
    ):

        return []

    return records


# =========================================================
# DATASET SUPPORT SCORE
# =========================================================

def _dataset_crop_alias(value):
    text = normalize_text(value)
    aliases = {
        "paddy": "rice",
        "finger millet": "ragi",
        "pearl millet": "bajra",
        "pigeon pea": "tur",
        "pigeonpeas": "tur",
        "chickpea": "gram",
        "chickpeas": "gram",
        "green gram": "green gram",
        "mungbean": "green gram",
        "mung bean": "green gram",
        "soybean": "soybean",
        "groundnut": "groundnut",
        "cotton": "cotton",
        "sugarcane": "sugarcane",
        "onion": "onion",
        "tomato": "tomato",
        "potato": "potato",
        "chilli": "chilli",
        "grapes": "grapes",
        "banana": "banana",
        "pomegranate": "pomegranate",
        "mango": "mango",
        "cashew": "cashew"
    }
    return aliases.get(text, text)


def _dataset_region_alias(value):
    text = normalize_text(value)
    aliases = {
        "western maharashtra desh": "western_maharashtra",
        "western maharashtra": "western_maharashtra",
        "desh": "western_maharashtra",
        "konkan": "konkan",
        "marathwada": "marathwada",
        "khandesh": "khandesh",
        "vidarbha": "vidarbha"
    }
    return aliases.get(text, text)


def dataset_support_score(
    crop_name: str,
    region: str,
    season: str,
    dataset_records: List[Dict[str, Any]]
) -> float:
    """Use the bundled Maharashtra project dataset only as a small tie-breaker."""

    if not dataset_records:
        return 0.50

    target_crop = _dataset_crop_alias(crop_name)
    target_region = _dataset_region_alias(region)
    target_season = normalize_season(season)

    matching_crop = 0
    matching_region = 0
    matching_season = 0

    for row in dataset_records:
        row_crop = _dataset_crop_alias(
            row.get("crop", row.get("crop_name", ""))
        )

        if row_crop != target_crop:
            continue

        matching_crop += 1

        row_region = _dataset_region_alias(
            row.get("region", "")
        )

        if row_region == target_region:
            matching_region += 1

        row_season = normalize_season(
            row.get("season", "")
        )

        if row_season == target_season:
            matching_season += 1

    if matching_crop == 0:
        return 0.25

    region_ratio = matching_region / matching_crop
    season_ratio = matching_season / matching_crop

    return min(
        1.0,
        0.40
        + (region_ratio * 0.35)
        + (season_ratio * 0.25)
    )


# =========================================================
# CROP RECOMMENDATION
# =========================================================

def recommend_crops(
    farm: Optional[Dict[str, Any]] = None,
    soil_data: Optional[Dict[str, Any]] = None,
    top_n: int = 5,
    dataset_path: Optional[str] = None
) -> Dict[str, Any]:

    farm = farm or {}
    soil_data = soil_data or {}

    # -----------------------------------------------------
    # Farm information
    # -----------------------------------------------------

    district = normalize_district(
        farm.get("district", "")
    )

    region = get_region(
        district=district,
        region=farm.get("region", "")
    )

    soil_type = normalize_soil(
        soil_data.get(
            "soil_type",
            farm.get("soil_type", "")
        )
    )

    irrigation = normalize_text(
        farm.get(
            "irrigation",
            ""
        )
    )

    water_source = normalize_text(
        farm.get(
            "water_source",
            ""
        )
    )

    season = normalize_season(
        farm.get(
            "season",
            ""
        )
    )

    previous_crop = normalize_text(
        farm.get(
            "previous_crop",
            ""
        )
    )

    area = safe_float(
        farm.get(
            "area"
        )
    )

    area_unit = farm.get(
        "area_unit",
        "acre"
    )

    # -----------------------------------------------------
    # Soil values
    # -----------------------------------------------------

    values = {

        "ph": safe_float(
            soil_data.get(
                "ph"
            )
        ),

        "nitrogen": safe_float(
            soil_data.get(
                "nitrogen"
            )
        ),

        "phosphorus": safe_float(
            soil_data.get(
                "phosphorus"
            )
        ),

        "potassium": safe_float(
            soil_data.get(
                "potassium"
            )
        ),

        "organic_carbon": safe_float(
            soil_data.get(
                "organic_carbon"
            )
        ),

        "electrical_conductivity":
            safe_float(
                soil_data.get(
                    "electrical_conductivity"
                )
            )
    }

    # -----------------------------------------------------
    # Dataset
    # -----------------------------------------------------

    dataset_records = load_dataset_records(
        dataset_path
    )

    recommendations = []

    # -----------------------------------------------------
    # Evaluate every crop
    # -----------------------------------------------------

    for crop_name, crop_data in CROP_DATABASE.items():

        region_score = regional_score(
            crop_data,
            region
        )

        season_fit = season_score(
            crop_data,
            season
        )

        soil_fit = soil_score(
            crop_data,
            soil_type
        )

        irrigation_fit = irrigation_score(
            crop_data,
            irrigation
        )

        water_fit = water_requirement_score(
            crop_data,
            irrigation
        )

        area_fit = area_score(
            crop_name,
            area,
            area_unit
        )

        previous_fit = previous_crop_score(
            crop_name,
            previous_crop
        )

        parameter_fit = parameter_scores(
            crop_data,
            values
        )

        parameter_average = (
            sum(
                parameter_fit.values()
            )
            /
            len(
                parameter_fit
            )
        )

        dataset_fit = dataset_support_score(
            crop_name,
            region,
            season,
            dataset_records
        )

        # -------------------------------------------------
        # HARD AGRONOMIC FILTERS
        # -------------------------------------------------

        hard_penalty = 1.0

        # Crop must not receive a high ranking
        # when region is fundamentally unsuitable.

        if region_score < 0.20:

            hard_penalty *= 0.25

        # Cashew is strongly associated with
        # Konkan/lateritic conditions.

        if crop_name == "Cashew":

            if region != "konkan":

                hard_penalty *= 0.20

            if soil_type not in (
                "laterite",
                "red",
                ""
            ):

                hard_penalty *= 0.30

        # Rice requires suitable water/rainfall context.

        if crop_name == "Rice":

            if (
                irrigation == "rainfed"
                and region not in (
                    "konkan",
                    "western_maharashtra"
                )
            ):

                hard_penalty *= 0.65

        # Sugarcane should not rank highly
        # under rainfed low-water conditions.

        if crop_name == "Sugarcane":

            if irrigation == "rainfed":

                hard_penalty *= 0.25

        # Cotton regional protection.
        #
        # This prevents cotton from becoming the
        # default recommendation in places such as
        # typical Western Maharashtra situations.

        if crop_name == "Cotton":

            if region == "konkan":

                hard_penalty *= 0.10

            elif region == "western_maharashtra":

                hard_penalty *= 0.55

        # -------------------------------------------------
        # Weighted score
        # -------------------------------------------------

        # The recommendation is intentionally dominated by the two things
        # the farmer actually knows best: the farm region and the laboratory
        # soil report. Farm management factors then refine the ranking.
        score = (
            region_score * 0.30
            + parameter_average * 0.25
            + soil_fit * 0.15
            + season_fit * 0.15
            + irrigation_fit * 0.07
            + water_fit * 0.04
            + previous_fit * 0.02
            + area_fit * 0.01
            + dataset_fit * 0.01
        )

        score *= hard_penalty

        score = max(
            0.0,
            min(
                1.0,
                score
            )
        )

        suitability = round(
            score * 100
        )

        reasons = []

        warnings = []

        # -------------------------------------------------
        # Reasons
        # -------------------------------------------------

        if region_score >= 0.85:

            reasons.append(
                "Strong regional suitability"
            )

        elif region_score >= 0.65:

            reasons.append(
                "Good regional suitability"
            )

        elif region_score < 0.40:

            warnings.append(
                "Regional suitability is limited"
            )

        if season_fit >= 0.90:

            reasons.append(
                f"Suitable for {season.title()} season"
            )

        elif season_fit < 0.40:

            warnings.append(
                f"Season suitability is low for {season.title()}"
            )

        if soil_fit >= 0.90:

            reasons.append(
                f"Suitable for {soil_type.title()} soil"
            )

        elif soil_fit < 0.50:

            warnings.append(
                "Soil type is not ideal"
            )

        if irrigation_fit >= 0.90:

            reasons.append(
                "Irrigation method is suitable"
            )

        elif irrigation_fit < 0.50:

            warnings.append(
                "Irrigation conditions may limit this crop"
            )

        # -------------------------------------------------
        # Soil parameter explanations
        # -------------------------------------------------

        if values["ph"] is not None:

            if parameter_fit["ph"] >= 0.90:

                reasons.append(
                    "Soil pH is suitable"
                )

            elif parameter_fit["ph"] < 0.60:

                warnings.append(
                    "Soil pH is outside the preferred range"
                )

        if values["nitrogen"] is not None:

            if parameter_fit["nitrogen"] < 0.60:

                warnings.append(
                    "Nitrogen level may need management"
                )

        if values["phosphorus"] is not None:

            if parameter_fit["phosphorus"] < 0.60:

                warnings.append(
                    "Phosphorus level may need management"
                )

        if values["potassium"] is not None:

            if parameter_fit["potassium"] < 0.60:

                warnings.append(
                    "Potassium level may need management"
                )

        if values["organic_carbon"] is not None:

            if parameter_fit["organic_carbon"] < 0.60:

                warnings.append(
                    "Organic carbon is relatively low"
                )

        # -------------------------------------------------
        # Water warning
        # -------------------------------------------------

        if (
            crop_data["water_need"]
            in (
                "high",
                "very_high"
            )
            and irrigation == "rainfed"
        ):

            warnings.append(
                "This crop has relatively high water demand"
            )

        # -------------------------------------------------
        # Dataset note
        # -------------------------------------------------

        if dataset_records:

            if dataset_fit >= 0.75:

                reasons.append(
                    "Supported by the regional crop dataset"
                )

        recommendations.append({

            "crop": crop_name,

            "category":
                crop_data["category"],

            "score":
                suitability,

            "suitability":
                suitability,

            "region":
                region,

            "region_name":
                region.replace(
                    "_",
                    " "
                ).title()
                if region
                else "Unknown",

            "region_score":
                round(
                    region_score * 100
                ),

            "season_score":
                round(
                    season_fit * 100
                ),

            "soil_score":
                round(
                    soil_fit * 100
                ),

            "irrigation_score":
                round(
                    irrigation_fit * 100
                ),

            "parameter_score":
                round(
                    parameter_average * 100
                ),

            "dataset_score":
                round(
                    dataset_fit * 100
                ),

            "reasons":
                reasons,

            "warnings":
                warnings,

            "soil_parameter_scores":
                {
                    key: round(
                        value * 100
                    )
                    for key, value
                    in parameter_fit.items()
                },

            "water_need":
                crop_data["water_need"],

            "preferred_soils":
                crop_data["soils"],

            "preferred_seasons":
                crop_data["seasons"]
        })

    # =====================================================
    # SORT
    # =====================================================

    recommendations.sort(
        key=lambda item:
            item["suitability"],
        reverse=True
    )

    recommendations = recommendations[
        :max(
            1,
            int(top_n)
        )
    ]

    # =====================================================
    # GENERAL WARNINGS
    # =====================================================

    general_warnings = []

    if not region:

        general_warnings.append(
            "Maharashtra region could not be determined from the district."
        )

    if not season:

        general_warnings.append(
            "Season was not provided."
        )

    if not soil_type:

        general_warnings.append(
            "Soil type was not provided."
        )

    missing_soil = []

    for key in (
        "ph",
        "nitrogen",
        "phosphorus",
        "potassium",
        "organic_carbon"
    ):

        if values.get(key) is None:

            missing_soil.append(
                key
            )

    if missing_soil:

        general_warnings.append(
            "Some soil-test values are missing. "
            "Recommendations are therefore less specific."
        )

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "success": True,

        "engine":
            "Smart Kisan Maharashtra Hybrid Crop Recommendation V2",

        "method":
            "Regional agronomic suitability + soil parameters + farm conditions",

        "region":
            region,

        "region_name":
            region.replace(
                "_",
                " "
            ).title()
            if region
            else "Unknown",

        "district":
            district,

        "soil_type":
            soil_type,

        "season":
            season,

        "irrigation":
            irrigation,

        "water_source":
            water_source,

        "area":
            area,

        "area_unit":
            area_unit,

        "previous_crop":
            previous_crop,

        "soil_data":
            values,

        "recommendations":
            recommendations,

        "top_crop":
            recommendations[0]["crop"]
            if recommendations
            else None,

        "top_score":
            recommendations[0]["suitability"]
            if recommendations
            else 0,

        "general_warnings":
            general_warnings,

        "dataset_loaded":
            bool(dataset_records),

        "dataset_records":
            len(dataset_records),

        "note":
            "Suitability scores are ranking scores, not guaranteed yield probabilities. "
            "Final crop selection should consider local agronomic advice, water availability, "
            "market conditions, seed availability and the actual soil-test report."
    }


# =========================================================
# COMPATIBILITY FUNCTION
# =========================================================
#
# This is the function that can be called from app.py.
#
# Your current app.py can use:
#
# analyze_crop_recommendation(...)
#
# =========================================================

def analyze_crop_recommendation(
    form_data: Optional[Dict[str, Any]] = None,
    farm: Optional[Dict[str, Any]] = None,
    top_n: int = 5
) -> Dict[str, Any]:

    form_data = form_data or {}
    farm = farm or {}

    # -----------------------------------------------------
    # Soil report values
    # -----------------------------------------------------

    soil_data = {

        "ph":
            form_data.get(
                "ph",
                ""
            ),

        "nitrogen":
            form_data.get(
                "nitrogen",
                ""
            ),

        "phosphorus":
            form_data.get(
                "phosphorus",
                ""
            ),

        "potassium":
            form_data.get(
                "potassium",
                ""
            ),

        "organic_carbon":
            form_data.get(
                "organic_carbon",
                ""
            ),

        "electrical_conductivity":
            form_data.get(
                "electrical_conductivity",
                ""
            ),

        "soil_type":
            form_data.get(
                "soil_type",
                farm.get(
                    "soil_type",
                    ""
                )
            )
    }

    return recommend_crops(
        farm=farm,
        soil_data=soil_data,
        top_n=top_n
    )


# =========================================================
# ALIAS
# =========================================================
#
# Useful if another part of Smart Kisan imports:
#
# from crop_recommendation import recommend_crop
#
# =========================================================

def recommend_crop(
    farm: Optional[Dict[str, Any]] = None,
    soil_data: Optional[Dict[str, Any]] = None,
    top_n: int = 5
) -> Dict[str, Any]:

    return recommend_crops(
        farm=farm,
        soil_data=soil_data,
        top_n=top_n
    )


# =========================================================
# SIMPLE TEST
# =========================================================

if __name__ == "__main__":

    test_farm = {

        "district": "Satara",

        "soil_type": "Black Cotton",

        "irrigation": "Drip",

        "water_source": "Borewell",

        "season": "Kharif",

        "previous_crop": "Gram",

        "area": 3,

        "area_unit": "acre"
    }

    test_soil = {

        "ph": 7.2,

        "nitrogen": 70,

        "phosphorus": 45,

        "potassium": 110,

        "organic_carbon": 0.8,

        "electrical_conductivity": 0.5
    }

    result = recommend_crops(
        farm=test_farm,
        soil_data=test_soil,
        top_n=5
    )

    print("\n")
    print("=" * 60)
    print("SMART KISAN AI")
    print("CROP RECOMMENDATION V2 TEST")
    print("=" * 60)

    print(
        "Region:",
        result["region_name"]
    )

    print(
        "District:",
        result["district"]
    )

    print(
        "Season:",
        result["season"]
    )

    print(
        "Soil:",
        result["soil_type"]
    )

    print("\nTOP RECOMMENDATIONS")
    print("-" * 60)

    for index, crop in enumerate(
        result["recommendations"],
        start=1
    ):

        print(
            f"{index}. "
            f"{crop['crop']} "
            f"({crop['suitability']}%)"
        )

        if crop["reasons"]:

            print(
                "   Reasons:"
            )

            for reason in crop["reasons"]:

                print(
                    "   -",
                    reason
                )

        if crop["warnings"]:

            print(
                "   Warnings:"
            )

            for warning in crop["warnings"]:

                print(
                    "   -",
                    warning
                )

    print("=" * 60)