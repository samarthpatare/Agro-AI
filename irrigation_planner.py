# ============================================================
# SMART KISAN AI
# SIMPLE WATER IRRIGATION DECISION ENGINE
# ============================================================

import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


# ============================================================
# HELPERS
# ============================================================

def farm_value(farm, key, default=""):
    """
    Safely read a value from sqlite3.Row or dictionary.
    """
    try:
        value = farm[key]
    except (KeyError, IndexError, TypeError):
        try:
            value = farm.get(key, default)
        except AttributeError:
            value = default

    if value is None:
        return default

    return value


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_text(value):
    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# WEATHER
# ============================================================

def fetch_irrigation_weather(farm):
    """
    Get weather information using the SAVED FARM coordinates.

    We do NOT use the laptop/phone current location.
    """

    latitude = to_float(
        farm_value(
            farm,
            "latitude"
        )
    )

    longitude = to_float(
        farm_value(
            farm,
            "longitude"
        )
    )

    if latitude is None or longitude is None:

        return {
            "success": False,
            "error":
                "Farm coordinates are not available."
        }

    params = {

        "latitude": latitude,

        "longitude": longitude,

        "timezone": "auto",

        "current":
            (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "wind_speed_10m"
            ),

        "hourly":
            (
                "precipitation,"
                "precipitation_probability,"
                "temperature_2m,"
                "relative_humidity_2m,"
                "wind_speed_10m"
            ),

        "past_hours": 24,

        "forecast_hours": 24
    }

    try:

        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        weather_json = response.json()

    except (
        requests.RequestException,
        ValueError
    ) as exc:

        return {
            "success": False,
            "error":
                f"Weather service is unavailable right now: {exc}"
        }

    current = weather_json.get(
        "current",
        {}
    )

    hourly = weather_json.get(
        "hourly",
        {}
    )

    times = hourly.get(
        "time",
        []
    )

    precipitation = hourly.get(
        "precipitation",
        []
    )

    precipitation_probability = hourly.get(
        "precipitation_probability",
        []
    )

    temperatures = hourly.get(
        "temperature_2m",
        []
    )

    humidities = hourly.get(
        "relative_humidity_2m",
        []
    )

    winds = hourly.get(
        "wind_speed_10m",
        []
    )

    current_time = current.get(
        "time",
        ""
    )

    try:

        current_index = times.index(
            current_time
        )

    except ValueError:

        # Safe fallback if the exact current timestamp
        # is not found in the hourly array.
        current_index = min(
            24,
            max(
                0,
                len(times) // 2
            )
        )

    # --------------------------------------------------------
    # LAST 24 HOURS
    # --------------------------------------------------------

    past_values = precipitation[
        max(0, current_index - 24):
        current_index
    ]

    # --------------------------------------------------------
    # NEXT 24 HOURS
    # --------------------------------------------------------

    future_values = precipitation[
        current_index + 1:
        current_index + 25
    ]

    future_probability_values = (
        precipitation_probability[
            current_index + 1:
            current_index + 25
        ]
    )

    future_temperature_values = [
        float(value)
        for value in temperatures[
            current_index + 1:
            current_index + 25
        ]
        if value is not None
    ]

    future_humidity_values = [
        float(value)
        for value in humidities[
            current_index + 1:
            current_index + 25
        ]
        if value is not None
    ]

    future_wind_values = [
        float(value)
        for value in winds[
            current_index + 1:
            current_index + 25
        ]
        if value is not None
    ]

    recent_rain = sum(
        float(value or 0)
        for value in past_values
    )

    next_rain = sum(
        float(value or 0)
        for value in future_values
    )

    next_rain_probability = max(
        [
            float(value or 0)
            for value in future_probability_values
        ] or [0]
    )

    current_temperature = to_float(
        current.get("temperature_2m")
    )

    current_humidity = to_float(
        current.get("relative_humidity_2m")
    )

    current_precipitation = to_float(
        current.get("precipitation")
    )

    current_wind = to_float(
        current.get("wind_speed_10m")
    )

    max_temperature = (
        max(future_temperature_values)
        if future_temperature_values
        else None
    )

    min_humidity = (
        min(future_humidity_values)
        if future_humidity_values
        else None
    )

    max_wind = (
        max(future_wind_values)
        if future_wind_values
        else None
    )

    return {

        "success": True,

        "timezone":
            weather_json.get(
                "timezone",
                "auto"
            ),

        "current": {

            "temperature":
                current_temperature,

            "humidity":
                current_humidity,

            "precipitation":
                current_precipitation,

            "wind_speed":
                current_wind
        },

        "rainfall": {

            "recent_24h_mm":
                round(
                    recent_rain,
                    1
                ),

            "next_24h_mm":
                round(
                    next_rain,
                    1
                ),

            "next_24h_probability":
                round(
                    next_rain_probability
                )
        },

        "forecast": {

            "max_temperature":
                (
                    round(
                        max_temperature,
                        1
                    )
                    if max_temperature is not None
                    else None
                ),

            "min_humidity":
                (
                    round(
                        min_humidity,
                        1
                    )
                    if min_humidity is not None
                    else None
                ),

            "max_wind":
                (
                    round(
                        max_wind,
                        1
                    )
                    if max_wind is not None
                    else None
                )
        }
    }


# ============================================================
# IRRIGATION ANALYSIS
# ============================================================

def analyze_irrigation(
    farm,
    crop_name,
    growth_stage,
    soil_moisture="unknown",
    field_observation=""
):
    """
    Simple explainable irrigation decision engine.

    Possible results:

    🔴 Irrigation Needed
    🟡 Monitor
    🟢 Irrigation Can Be Delayed
    ⚪ Field Check Required
    """

    crop_name = clean_text(
        crop_name
    )

    growth_stage = clean_text(
        growth_stage
    )

    soil_moisture = clean_text(
        soil_moisture
    ).lower()

    field_observation = clean_text(
        field_observation
    )

    # --------------------------------------------------------
    # BASIC VALIDATION
    # --------------------------------------------------------

    if not crop_name:

        return {
            "success": False,
            "error":
                "Please enter the crop name."
        }

    if not growth_stage:

        return {
            "success": False,
            "error":
                "Please select the crop growth stage."
        }

    allowed_soil_moisture = {

        "dry",

        "slightly_dry",

        "moist",

        "wet",

        "unknown"
    }

    if soil_moisture not in allowed_soil_moisture:

        soil_moisture = "unknown"

    # --------------------------------------------------------
    # GET WEATHER
    # --------------------------------------------------------

    weather = fetch_irrigation_weather(
        farm
    )

    if not weather["success"]:

        return {

            "success": True,

            "status":
                "field_check",

            "status_label":
                "⚪ Field Check Required",

            "status_class":
                "field-check",

            "summary":
                "Weather information is unavailable, "
                "so a reliable automatic irrigation "
                "decision cannot be made.",

            "reasons": [

                "Farm weather could not be retrieved.",

                "Actual field moisture should be checked."
            ],

            "actions": [

                "Inspect the soil near the crop root zone.",

                "Use your normal farm irrigation practice "
                "based on the field condition."
            ],

            "field_check":
                (
                    "Check whether the root-zone soil "
                    "is dry, moist or wet."
                ),

            "reassess":
                "After checking the field.",

            "warning":
                weather["error"],

            "weather":
                None,

            "effects": {},

            "inputs": {

                "crop_name":
                    crop_name,

                "growth_stage":
                    growth_stage,

                "soil_type":
                    clean_text(
                        farm_value(
                            farm,
                            "soil_type"
                        )
                    ),

                "irrigation":
                    clean_text(
                        farm_value(
                            farm,
                            "irrigation"
                        )
                    ),

                "water_source":
                    clean_text(
                        farm_value(
                            farm,
                            "water_source"
                        )
                    ),

                "soil_moisture":
                    soil_moisture,

                "field_observation":
                    field_observation
            }
        }

    # ========================================================
    # WEATHER VALUES
    # ========================================================

    current = weather["current"]

    rainfall = weather["rainfall"]

    forecast = weather["forecast"]

    recent_rain = rainfall[
        "recent_24h_mm"
    ]

    next_rain = rainfall[
        "next_24h_mm"
    ]

    rain_probability = rainfall[
        "next_24h_probability"
    ]

    temperature = current[
        "temperature"
    ]

    humidity = current[
        "humidity"
    ]

    max_temperature = forecast[
        "max_temperature"
    ]

    min_humidity = forecast[
        "min_humidity"
    ]

    max_wind = forecast[
        "max_wind"
    ]

    # ========================================================
    # WEATHER SIGNALS
    # ========================================================

    heat_signal = (

        (
            temperature is not None
            and temperature >= 32
        )

        or

        (
            max_temperature is not None
            and max_temperature >= 35
        )
    )

    dry_air_signal = (

        (
            humidity is not None
            and humidity <= 35
        )

        or

        (
            min_humidity is not None
            and min_humidity <= 30
        )
    )

    windy_signal = (

        max_wind is not None
        and max_wind >= 30
    )

    water_loss_signal = (

        heat_signal

        or

        dry_air_signal

        or

        windy_signal
    )

    useful_rain_expected = (

        next_rain >= 5

        or

        (
            next_rain >= 2
            and rain_probability >= 60
        )
    )

    recent_meaningful_rain = (

        recent_rain >= 5
    )

    # ========================================================
    # CROP STAGE
    # ========================================================

    stage_lower = growth_stage.lower()

    sensitive_stage = any(

        word in stage_lower

        for word in (

            "flowering",

            "fruit",

            "bulb",

            "pod",

            "reproductive"
        )
    )

    # ========================================================
    # SOIL EFFECT
    # ========================================================

    soil_type = clean_text(
        farm_value(
            farm,
            "soil_type"
        )
    )

    soil_lower = soil_type.lower()

    if "sand" in soil_lower:

        soil_effect = (
            "Sandy soil may lose available moisture faster."
        )

    elif (
        "black" in soil_lower
        or "clay" in soil_lower
    ):

        soil_effect = (
            "Black/clayey soil generally retains "
            "moisture longer."
        )

    elif "loam" in soil_lower:

        soil_effect = (
            "Loamy soil can provide a moderate "
            "moisture balance."
        )

    elif soil_type:

        soil_effect = (
            f"Soil type recorded as {soil_type}. "
            "Actual field moisture should guide "
            "the final decision."
        )

    else:

        soil_effect = (
            "Soil type is not available; "
            "use the actual field condition."
        )

    # ========================================================
    # DECISION
    # ========================================================

    reasons = []

    actions = []

    # --------------------------------------------------------
    # WET
    # --------------------------------------------------------

    if soil_moisture == "wet":

        status = "delay"

        status_label = (
            "🟢 Irrigation Can Be Delayed"
        )

        status_class = "delay"

        reasons.append(
            "The field is reported as wet."
        )

        if useful_rain_expected:

            reasons.append(
                "More rainfall is expected soon."
            )

        actions.append(
            "Do not irrigate immediately while "
            "the field remains wet."
        )

    # --------------------------------------------------------
    # DRY
    # --------------------------------------------------------

    elif soil_moisture == "dry":

        if useful_rain_expected:

            status = "monitor"

            status_label = (
                "🟡 Monitor"
            )

            status_class = "monitor"

            reasons.append(
                "The field is reported as dry."
            )

            reasons.append(
                "Rainfall is expected within the "
                "next 24 hours."
            )

            if sensitive_stage:

                reasons.append(
                    "The crop is at a moisture-sensitive "
                    "growth stage, so water stress should "
                    "be watched closely."
                )

            actions.append(
                "Check root-zone moisture before "
                "deciding to irrigate."
            )

        else:

            status = "needed"

            status_label = (
                "🔴 Irrigation Needed"
            )

            status_class = "needed"

            reasons.append(
                "The field is reported as dry."
            )

            reasons.append(
                "No useful rainfall is expected "
                "within the next 24 hours."
            )

            if water_loss_signal:

                reasons.append(
                    "Weather conditions may increase "
                    "water loss."
                )

            if sensitive_stage:

                reasons.append(
                    "The crop is at a growth stage where "
                    "water stress should be monitored closely."
                )

            actions.append(
                "Irrigate according to your normal "
                "farm practice."
            )

            actions.append(
                "Check root-zone moisture again "
                "after irrigation."
            )

    # --------------------------------------------------------
    # SLIGHTLY DRY
    # --------------------------------------------------------

    elif soil_moisture == "slightly_dry":

        if useful_rain_expected:

            status = "delay"

            status_label = (
                "🟢 Irrigation Can Be Delayed"
            )

            status_class = "delay"

            reasons.append(
                "The field is slightly dry."
            )

            reasons.append(
                "Useful rainfall is expected soon."
            )

            actions.append(
                "Delay irrigation and reassess "
                "after rainfall."
            )

        else:

            status = "monitor"

            status_label = (
                "🟡 Monitor"
            )

            status_class = "monitor"

            reasons.append(
                "The field is becoming dry."
            )

            if water_loss_signal:

                reasons.append(
                    "Weather may increase water loss."
                )

            if sensitive_stage:

                reasons.append(
                    "The crop stage makes moisture "
                    "monitoring important."
                )

            actions.append(
                "Check root-zone moisture before irrigating."
            )

    # --------------------------------------------------------
    # MOIST
    # --------------------------------------------------------

    elif soil_moisture == "moist":

        if useful_rain_expected:

            status = "delay"

            status_label = (
                "🟢 Irrigation Can Be Delayed"
            )

            status_class = "delay"

            reasons.append(
                "The field is reported as moist."
            )

            reasons.append(
                "Useful rainfall is expected soon."
            )

            actions.append(
                "Delay irrigation and recheck "
                "after rainfall."
            )

        elif water_loss_signal:

            status = "monitor"

            status_label = (
                "🟡 Monitor"
            )

            status_class = "monitor"

            reasons.append(
                "The field is currently moist."
            )

            reasons.append(
                "Weather may increase water loss."
            )

            actions.append(
                "Monitor the field and recheck "
                "root-zone moisture soon."
            )

        else:

            status = "delay"

            status_label = (
                "🟢 Irrigation Can Be Delayed"
            )

            status_class = "delay"

            reasons.append(
                "The field is reported as moist."
            )

            reasons.append(
                "There is no strong weather signal "
                "for immediate extra water."
            )

            actions.append(
                "Delay irrigation while the soil "
                "remains adequately moist."
            )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    else:

        if (
            recent_meaningful_rain
            and useful_rain_expected
        ):

            status = "delay"

            status_label = (
                "🟢 Irrigation Can Be Delayed"
            )

            status_class = "delay"

            reasons.append(
                "Meaningful rain occurred recently."
            )

            reasons.append(
                "Additional rainfall is expected soon."
            )

            actions.append(
                "Delay irrigation and check the field "
                "after rainfall."
            )

        elif (
            not useful_rain_expected
            and water_loss_signal
        ):

            status = "monitor"

            status_label = (
                "🟡 Monitor"
            )

            status_class = "monitor"

            reasons.append(
                "No useful rainfall is expected "
                "and weather may increase water loss."
            )

            reasons.append(
                "Actual soil moisture was not provided."
            )

            actions.append(
                "Check the root-zone moisture before irrigating."
            )

        else:

            status = "field_check"

            status_label = (
                "⚪ Field Check Required"
            )

            status_class = "field-check"

            reasons.append(
                "Actual soil moisture was not provided."
            )

            reasons.append(
                "Weather signals are not strong enough "
                "for a confident automatic decision."
            )

            actions.append(
                "Inspect the soil near the crop root zone "
                "before irrigating."
            )

    # ========================================================
    # WEATHER EXPLANATION
    # ========================================================

    rainfall_effect = (

        f"Recent 24-hour rainfall: "
        f"{recent_rain:.1f} mm. "

        f"Expected next 24-hour rainfall: "
        f"{next_rain:.1f} mm. "

        f"Rain probability: "
        f"{rain_probability:.0f}%."
    )

    weather_parts = []

    if temperature is not None:

        weather_parts.append(
            f"Current temperature: {temperature:.1f}°C"
        )

    if humidity is not None:

        weather_parts.append(
            f"Humidity: {humidity:.0f}%"
        )

    if max_temperature is not None:

        weather_parts.append(
            f"Forecast maximum: {max_temperature:.1f}°C"
        )

    if max_wind is not None:

        weather_parts.append(
            f"Maximum wind: {max_wind:.0f} km/h"
        )

    weather_effect = (

        " • ".join(
            weather_parts
        )

        if weather_parts

        else

        "Weather information is incomplete."
    )

    crop_stage_effect = (

        f"{growth_stage} is a moisture-sensitive "
        "growth stage, so water stress should be monitored closely."

        if sensitive_stage

        else

        f"{growth_stage} is included as crop-stage context "
        "for the irrigation decision."
    )

    irrigation_method = clean_text(
        farm_value(
            farm,
            "irrigation"
        )
    )

    water_source = clean_text(
        farm_value(
            farm,
            "water_source"
        )
    )

    irrigation_effect = (

        f"Farm irrigation method: {irrigation_method}."

        if irrigation_method

        else

        "Irrigation method is not available."
    )

    # ========================================================
    # FIELD CHECK
    # ========================================================

    field_check = (
        "Check the soil near the crop root zone. "
        "Do not judge only from the surface appearance."
    )

    # ========================================================
    # REASSESSMENT
    # ========================================================

    if status == "needed":

        reassess = (
            "Recheck root-zone moisture after irrigation."
        )

    elif status == "monitor":

        reassess = (
            "Recheck within 12–24 hours or sooner "
            "if the crop shows water stress."
        )

    elif status == "delay":

        reassess = (
            "Recheck after the expected rainfall "
            "or within 24 hours."
        )

    else:

        reassess = (
            "Check the field now."
        )

    # ========================================================
    # WARNING
    # ========================================================

    warning = (
        "This is a decision-support recommendation, "
        "not a guaranteed irrigation requirement. "
        "Local field conditions may differ from weather data."
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "success": True,

        "status":
            status,

        "status_label":
            status_label,

        "status_class":
            status_class,

        "summary":
            reasons[0]
            if reasons
            else status_label,

        "reasons":
            reasons,

        "actions":
            actions,

        "field_check":
            field_check,

        "reassess":
            reassess,

        "warning":
            warning,

        "weather":
            weather,

        "effects": {

            "rainfall":
                rainfall_effect,

            "weather":
                weather_effect,

            "soil":
                soil_effect,

            "crop_stage":
                crop_stage_effect,

            "irrigation":
                irrigation_effect
        },

        "inputs": {

            "farm_name":
                clean_text(
                    farm_value(
                        farm,
                        "farm_name"
                    )
                ),

            "crop_name":
                crop_name,

            "growth_stage":
                growth_stage,

            "soil_type":
                soil_type,

            "irrigation":
                irrigation_method,

            "water_source":
                water_source,

            "soil_moisture":
                soil_moisture,

            "field_observation":
                field_observation
        }
    }