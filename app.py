# =========================================================
# SMART KISAN AI
# MAIN FLASK APPLICATION
# =========================================================

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    flash,
    jsonify
)

import os
import json
import time
import requests
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()


# =========================================================
# DATABASE
# =========================================================

from database import (
    create_tables,
    add_farmer,
    check_farmer,
    get_farmer_by_id,
    add_farm,
    get_farms_by_farmer,
    get_farm_by_id,
    delete_farm,
    add_ai_history,
    get_ai_history,
    clear_ai_history
)


# =========================================================
# SOIL ANALYZER
# =========================================================

try:

    from soil_analyzer import (
        analyze_soil_report,
        extract_report_values
    )

except ImportError:

    analyze_soil_report = None
    extract_report_values = None


# =========================================================
# CROP RECOMMENDATION V2
# =========================================================

try:

    from crop_recommendation import recommend_crops

except ImportError:

    recommend_crops = None


# =========================================================
# DISEASE DETECTION
# =========================================================

try:

    from disease_detection import (
        detect_plant_disease
    )

except ImportError:

    detect_plant_disease = None


# =========================================================
# CROP HEALTH AI
# =========================================================

try:

    from crop_health import detect_crop_health

except ImportError:

    detect_crop_health = None


# =========================================================
# FERTILIZER ADVISOR AI
# =========================================================

try:

    from fertilizer_advisor import analyze_fertilizer

except ImportError:

    analyze_fertilizer = None


# =========================================================
# FLASK APP
# =========================================================

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)


# =========================================================
# JSON TEMPLATE FILTER
# =========================================================

@app.template_filter("from_json")
def from_json_filter(value):

    if isinstance(value, (dict, list)):

        return value

    try:

        return json.loads(value)

    except (TypeError, ValueError):

        return None


# =========================================================
# CONFIGURATION
# =========================================================

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "smart-kisan-development-secret-key"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# =========================================================
# GLOBAL LANGUAGE SCRIPT
# =========================================================

@app.after_request
def inject_language_script(response):

    content_type = response.headers.get("Content-Type", "")

    if "text/html" not in content_type:
        return response

    try:
        body = response.get_data(as_text=True)
    except Exception:
        return response

    script_src = url_for(
        "static",
        filename="js/language.js"
    )

    tag = f'<script src="{script_src}"></script>'

    if "language.js" in body:
        return response

    if "</body>" in body.lower():
        index = body.lower().rfind("</body>")
        body = body[:index] + tag + body[index:]
        response.set_data(body)

    return response


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

create_tables()


# =========================================================
# MULTILINGUAL SUPPORT
# =========================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "हिन्दी",
    "mr": "मराठी"
}


@app.context_processor
def inject_language_context():

    language = session.get("farmer_language", "en")

    if language not in SUPPORTED_LANGUAGES:
        language = "en"

    return {
        "current_language": language,
        "current_language_name": SUPPORTED_LANGUAGES[language],
        "supported_languages": SUPPORTED_LANGUAGES
    }


@app.route(
    "/set-language",
    methods=["POST"]
)
def set_language():

    data = request.get_json(silent=True) or {}
    language = str(data.get("language", "")).strip().lower()

    if language not in SUPPORTED_LANGUAGES:

        return jsonify({
            "success": False,
            "error": "Unsupported language."
        }), 400

    session["farmer_language"] = language

    return jsonify({
        "success": True,
        "language": language,
        "language_name": SUPPORTED_LANGUAGES[language]
    })


# =========================================================
# FULL TEXT TRANSLATION API
# =========================================================

TRANSLATION_CACHE = {}
TRANSLATION_CACHE_MAX = 3000


def _translation_cache_get(language, text_value):

    return TRANSLATION_CACHE.get(
        (language, text_value)
    )


def _translation_cache_set(language, text_value, translated):

    if len(TRANSLATION_CACHE) >= TRANSLATION_CACHE_MAX:

        try:
            first_key = next(iter(TRANSLATION_CACHE))
            TRANSLATION_CACHE.pop(first_key, None)
        except StopIteration:
            pass

    TRANSLATION_CACHE[(language, text_value)] = translated


def _parse_translation_json(content):

    content = str(content or "").strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        content = "\n".join(lines).strip()

    try:
        return json.loads(content)
    except (TypeError, ValueError):
        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end <= start:
            return None

        try:
            return json.loads(content[start:end + 1])
        except (TypeError, ValueError):
            return None


@app.route(
    "/api/translate-text",
    methods=["POST"]
)
def api_translate_text():

    data = request.get_json(silent=True) or {}

    language = str(
        data.get("language", "en")
    ).strip().lower()

    if language not in SUPPORTED_LANGUAGES:

        return jsonify({
            "success": False,
            "error": "Unsupported language."
        }), 400

    texts = data.get("texts")

    if not isinstance(texts, list):

        return jsonify({
            "success": False,
            "error": "texts must be a list."
        }), 400

    if len(texts) > 12:

        return jsonify({
            "success": False,
            "error": "Too many text items in one request."
        }), 400

    clean_texts = []

    for value in texts:

        value = str(value or "")

        if len(value) > 4000:

            return jsonify({
                "success": False,
                "error": "One text item is too long."
            }), 400

        clean_texts.append(value)

    if language == "en":

        return jsonify({
            "success": True,
            "language": language,
            "translations": clean_texts
        })

    if not clean_texts:

        return jsonify({
            "success": True,
            "language": language,
            "translations": []
        })

    api_key = os.getenv(
        "GROQ_API_KEY",
        ""
    ).strip()

    if not api_key:

        return jsonify({
            "success": False,
            "error": "GROQ_API_KEY is not configured."
        }), 503

    translations = [None] * len(clean_texts)
    missing = []

    for index, text_value in enumerate(clean_texts):

        clean_value = text_value.strip()

        if not clean_value:
            translations[index] = text_value
            continue

        cached = _translation_cache_get(
            language,
            clean_value
        )

        if cached is not None:
            translations[index] = cached
        else:
            missing.append(
                (index, clean_value)
            )

    if missing:

        target_language = SUPPORTED_LANGUAGES[language]

        items = [
            {
                "id": index,
                "text": value
            }
            for index, value in missing
        ]

        system_prompt = (
            "You are the official translation engine for Smart Kisan AI. "
            "Translate each supplied English text into "
            + target_language
            + ". Return only valid JSON in this exact structure: "
            + '{"translations":[{"id":0,"translation":"..."}]} '
            + "Use every supplied id exactly once. Do not omit any item. "
            + "Keep numbers, units, percentages, dates, URLs, crop names, "
            + "scientific names, place names, scheme names and technical "
            + "model names accurate. Keep words that should stay in English "
            + "such as Smart Kisan AI when appropriate. Do not add markdown "
            + "or explanations. Use natural, simple language suitable for "
            + "Indian farmers."
        )

        user_prompt = json.dumps(
            {
                "target_language": target_language,
                "items": items
            },
            ensure_ascii=False
        )

        try:

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization":
                        f"Bearer {api_key}",
                    "Content-Type":
                        "application/json"
                },
                json={
                    "model": os.getenv(
                        "GROQ_MODEL",
                        "openai/gpt-oss-20b"
                    ).strip(),
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_completion_tokens": 3500
                },
                timeout=45
            )

            if not response.ok:

                try:
                    error_json = response.json()
                    message = (
                        error_json
                        .get("error", {})
                        .get("message")
                        or "Translation request failed."
                    )
                except ValueError:
                    message = "Translation request failed."

                return jsonify({
                    "success": False,
                    "error": message
                }), 502

            response_json = response.json()
            choices = response_json.get("choices") or []

            if not choices:

                return jsonify({
                    "success": False,
                    "error": "Translation AI returned no result."
                }), 502

            content = (
                choices[0]
                .get("message", {})
                .get("content", "")
            )

            payload = _parse_translation_json(
                content
            )

            translated_items = (
                payload.get("translations")
                if isinstance(payload, dict)
                else None
            )

            if not isinstance(translated_items, list):

                return jsonify({
                    "success": False,
                    "error": "Translation AI returned invalid JSON."
                }), 502

            by_id = {}

            for item in translated_items:

                if not isinstance(item, dict):
                    continue

                try:
                    item_id = int(
                        item.get("id")
                    )
                except (TypeError, ValueError):
                    continue

                translation = str(
                    item.get("translation", "")
                ).strip()

                if translation:
                    by_id[item_id] = translation

            for index, original in missing:

                translated = by_id.get(index)

                if translated:

                    translations[index] = translated

                    _translation_cache_set(
                        language,
                        original,
                        translated
                    )

                else:
                    translations[index] = original

        except requests.RequestException as error:

            print(
                "Translation API error:",
                error
            )

            return jsonify({
                "success": False,
                "error": "Unable to reach the translation service."
            }), 502

        except (ValueError, TypeError, KeyError, IndexError) as error:

            print(
                "Translation parsing error:",
                error
            )

            return jsonify({
                "success": False,
                "error": "Unable to process the translation response."
            }), 502

    for index, value in enumerate(translations):

        if value is None:
            translations[index] = clean_texts[index]

    return jsonify({
        "success": True,
        "language": language,
        "translations": translations
    })


# =========================================================
# LOGIN HELPER
# =========================================================

def require_login():

    return session.get("farmer_id")


# =========================================================
# ACTIVE FARM HELPER
# =========================================================

def get_active_farm(farmer_id):

    active_farm_id = session.get(
        "active_farm_id"
    )

    if active_farm_id is not None:

        try:

            active_farm_id = int(
                active_farm_id
            )

        except (
            ValueError,
            TypeError
        ):

            active_farm_id = None

    if active_farm_id is not None:

        farm = get_farm_by_id(
            active_farm_id,
            farmer_id
        )

        if farm is not None:

            return dict(farm)

        session.pop(
            "active_farm_id",
            None
        )

    farms = get_farms_by_farmer(
        farmer_id
    )

    if farms:

        active_farm = farms[-1]

        session["active_farm_id"] = (
            active_farm["farm_id"]
        )

        return dict(active_farm)

    return None


# =========================================================
# REQUIRE ACTIVE FARM
# =========================================================

def require_active_farm(
    feature_name="this feature"
):

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return (
            None,
            None,
            redirect(
                url_for("login")
            )
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            + feature_name
            + ".",
            "error"
        )

        return (
            None,
            None,
            redirect(
                url_for(
                    "farm_details",
                    new="1"
                )
            )
        )

    return (
        farmer_id,
        active_farm,
        None
    )


# =========================================================
# WEATHER DESCRIPTION
# =========================================================

def get_weather_description(
    weather_code
):

    try:

        code = int(
            weather_code
        )

    except (
        TypeError,
        ValueError
    ):

        return (
            "Weather information",
            "🌦️"
        )

    if code == 0:

        return (
            "Clear sky",
            "☀️"
        )

    if code in (1, 2, 3):

        return (
            "Partly cloudy",
            "⛅"
        )

    if code in (45, 48):

        return (
            "Fog",
            "🌫️"
        )

    if code in (51, 53, 55):

        return (
            "Drizzle",
            "🌦️"
        )

    if code in (56, 57):

        return (
            "Freezing drizzle",
            "🌧️"
        )

    if code in (61, 63, 65):

        return (
            "Rain",
            "🌧️"
        )

    if code in (66, 67):

        return (
            "Freezing rain",
            "🌧️"
        )

    if code in (71, 73, 75, 77):

        return (
            "Snow",
            "❄️"
        )

    if code in (80, 81, 82):

        return (
            "Rain showers",
            "🌦️"
        )

    if code in (85, 86):

        return (
            "Snow showers",
            "🌨️"
        )

    if code == 95:

        return (
            "Thunderstorm",
            "⛈️"
        )

    if code in (96, 99):

        return (
            "Thunderstorm with hail",
            "⛈️"
        )

    return (
        "Variable weather",
        "🌦️"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":

        return render_template(
            "register.html"
        )

    name = request.form.get(
        "name",
        ""
    ).strip()

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    language = request.form.get(
        "language",
        "en"
    ).strip()

    state = request.form.get(
        "state",
        "Maharashtra"
    ).strip()

    district = request.form.get(
        "district",
        ""
    ).strip()

    taluka = request.form.get(
        "taluka",
        ""
    ).strip()

    village = request.form.get(
        "village",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if len(name) < 2:

        flash(
            "Please enter your full name.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if not (
        mobile.isdigit()
        and len(mobile) == 10
        and mobile[0] in "6789"
    ):

        flash(
            "Please enter a valid 10-digit mobile number.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if language not in (
        "en",
        "hi",
        "mr"
    ):

        flash(
            "Invalid language selected.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if state != "Maharashtra":

        flash(
            "Currently Smart Kisan supports Maharashtra only.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if not district:

        flash(
            "Please select your district.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if not taluka:

        flash(
            "Please select your taluka.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if not village:

        flash(
            "Please enter your village.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    if password != confirm_password:

        flash(
            "Passwords do not match.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    farmer_id = add_farmer(

        name=name,

        mobile=mobile,

        password=password,

        language=language,

        state=state,

        district=district,

        taluka=taluka,

        village=village
    )

    if farmer_id is None:

        flash(
            "This mobile number is already registered.",
            "error"
        )

        return redirect(
            url_for("register")
        )

    flash(
        "Registration successful. Please login.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

    mobile = request.form.get(
        "mobile",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not mobile or not password:

        flash(
            "Please enter mobile number and password.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farmer = check_farmer(
        mobile,
        password
    )

    if farmer is None:

        flash(
            "Invalid mobile number or password.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    session.clear()

    session["farmer_id"] = (
        farmer["farmer_id"]
    )

    session["farmer_name"] = (
        farmer["name"]
    )

    session["farmer_language"] = (
        farmer["language"]
    )

    farms = get_farms_by_farmer(
        farmer["farmer_id"]
    )

    if farms:

        session["active_farm_id"] = (
            farms[-1]["farm_id"]
        )

    return redirect(
        url_for("dashboard")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farmer = get_farmer_by_id(
        farmer_id
    )

    if farmer is None:

        session.clear()

        flash(
            "Farmer account could not be found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farms = get_farms_by_farmer(
        farmer_id
    )

    active_farm = get_active_farm(
        farmer_id
    )

    return render_template(
        "dashboard.html",
        farmer=farmer,
        farms=farms,
        active_farm=active_farm
    )


# =========================================================
# FARMER DETAILS
# =========================================================

@app.route("/farmer-details")
def farmer_details():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farmer = get_farmer_by_id(
        farmer_id
    )

    if farmer is None:

        session.clear()

        flash(
            "Farmer account could not be found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "farmer-details.html",
        farmer=farmer
    )


# =========================================================
# GEOCODE FARM LOCATION
# =========================================================

@app.route(
    "/geocode-farm",
    methods=["POST"]
)
def geocode_farm():

    if "farmer_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    data = request.get_json(
        silent=True
    ) or {}

    state = str(
        data.get(
            "state",
            ""
        )
    ).strip()

    district = str(
        data.get(
            "district",
            ""
        )
    ).strip()

    taluka = str(
        data.get(
            "taluka",
            ""
        )
    ).strip()

    village = str(
        data.get(
            "village",
            ""
        )
    ).strip()

    if state != "Maharashtra":

        return jsonify({
            "success": False,
            "message":
                "Only Maharashtra is supported."
        }), 400

    if not district:

        return jsonify({
            "success": False,
            "message":
                "District is required."
        }), 400

    if not taluka:

        return jsonify({
            "success": False,
            "message":
                "Taluka is required."
        }), 400

    if not village:

        return jsonify({
            "success": False,
            "message":
                "Village is required."
        }), 400

    nominatim_url = (
        "https://nominatim.openstreetmap.org/search"
    )

    headers = {
        "User-Agent":
            "SmartKisanAI/1.0 "
            "(agriculture engineering project)"
    }

    def search_location(query):

        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
            "countrycodes": "in"
        }

        try:

            response = requests.get(
                nominatim_url,
                params=params,
                headers=headers,
                timeout=10
            )

            response.raise_for_status()

            results = response.json()

            if not isinstance(
                results,
                list
            ):

                return []

            return results

        except (
            requests.RequestException,
            ValueError
        ):

            return []

    village_query = (
        f"{village}, "
        f"{taluka}, "
        f"{district}, "
        f"{state}, India"
    )

    village_results = search_location(
        village_query
    )

    for result in village_results:

        address = result.get(
            "address",
            {}
        )

        display_name = str(
            result.get(
                "display_name",
                ""
            )
        ).lower()

        address_text = " ".join(
            str(value).lower()
            for value in address.values()
        )

        combined_text = (
            address_text
            + " "
            + display_name
        )

        if (
            village.lower()
            in combined_text
            and district.lower()
            in combined_text
        ):

            try:

                latitude = float(
                    result["lat"]
                )

                longitude = float(
                    result["lon"]
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                continue

            return jsonify({

                "success": True,

                "latitude": latitude,

                "longitude": longitude,

                "location_level":
                    "village",

                "message":
                    "Village coordinates found."
            })

    time.sleep(1.1)

    taluka_query = (
        f"{taluka}, "
        f"{district}, "
        f"{state}, India"
    )

    taluka_results = search_location(
        taluka_query
    )

    for result in taluka_results:

        address = result.get(
            "address",
            {}
        )

        display_name = str(
            result.get(
                "display_name",
                ""
            )
        ).lower()

        address_text = " ".join(
            str(value).lower()
            for value in address.values()
        )

        combined_text = (
            address_text
            + " "
            + display_name
        )

        if (
            taluka.lower()
            in combined_text
            and district.lower()
            in combined_text
        ):

            try:

                latitude = float(
                    result["lat"]
                )

                longitude = float(
                    result["lon"]
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                continue

            return jsonify({

                "success": True,

                "latitude": latitude,

                "longitude": longitude,

                "location_level":
                    "taluka",

                "message":
                    "Village coordinates were unavailable. "
                    "Taluka coordinates are being used."
            })

    return jsonify({

        "success": False,

        "message":
            "The selected location could not be found. "
            "Please check the village and taluka name."
    }), 404


# =========================================================
# FARM DETAILS
# =========================================================

@app.route(
    "/farm-details",
    methods=["GET", "POST"]
)
def farm_details():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    if request.method == "GET":

        farms = get_farms_by_farmer(
            farmer_id
        )

        is_new_farm = (
            request.args.get(
                "new",
                ""
            ).strip()
            == "1"
        )

        if is_new_farm:

            return render_template(
                "farm-details.html",
                farms=farms,
                farm=None,
                is_new_farm=True
            )

        requested_farm_id = request.args.get(
            "farm_id",
            type=int
        )

        selected_farm = None

        if requested_farm_id:

            selected_farm = get_farm_by_id(
                requested_farm_id,
                farmer_id
            )

            if selected_farm is None:

                flash(
                    "Selected farm could not be found.",
                    "error"
                )

        if selected_farm is None:

            selected_farm = get_active_farm(
                farmer_id
            )

        if selected_farm is not None:

            session["active_farm_id"] = (
                selected_farm["farm_id"]
            )

        return render_template(
            "farm-details.html",
            farms=farms,
            farm=selected_farm,
            is_new_farm=False
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    farm_id_raw = request.form.get(
        "farm_id",
        ""
    ).strip()

    farm_id = None

    if farm_id_raw:

        try:

            farm_id = int(
                farm_id_raw
            )

        except (
            ValueError,
            TypeError
        ):

            farm_id = None

    farm_name = request.form.get(
        "farm_name",
        ""
    ).strip()

    area = request.form.get(
        "area",
        ""
    ).strip()

    area_unit = request.form.get(
        "area_unit",
        ""
    ).strip()

    soil_type = request.form.get(
        "soil_type",
        ""
    ).strip()

    irrigation = request.form.get(
        "irrigation",
        ""
    ).strip()

    water_source = request.form.get(
        "water_source",
        ""
    ).strip()

    season = request.form.get(
        "season",
        ""
    ).strip()

    previous_crop = request.form.get(
        "previous_crop",
        ""
    ).strip()

    state = request.form.get(
        "state",
        "Maharashtra"
    ).strip()

    district = request.form.get(
        "district",
        ""
    ).strip()

    taluka = request.form.get(
        "taluka",
        ""
    ).strip()

    village = request.form.get(
        "village",
        ""
    ).strip()

    latitude = request.form.get(
        "latitude",
        ""
    ).strip()

    longitude = request.form.get(
        "longitude",
        ""
    ).strip()

    location_level = request.form.get(
        "location_level",
        ""
    ).strip()

    if farm_id is not None:

        form_redirect = url_for(
            "farm_details",
            farm_id=farm_id
        )

    else:

        form_redirect = url_for(
            "farm_details",
            new="1"
        )

    if not farm_name:

        flash(
            "Please enter your farm name.",
            "error"
        )

        return redirect(
            form_redirect
        )

    try:

        area_value = float(
            area
        )

        if area_value <= 0:

            raise ValueError

    except (
        ValueError,
        TypeError
    ):

        flash(
            "Please enter a valid farm area.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if area_unit not in (
        "acre",
        "hectare",
        "guntha"
    ):

        flash(
            "Please select a valid area unit.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not soil_type:

        flash(
            "Please select your soil type.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not irrigation:

        flash(
            "Please select your irrigation method.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not water_source:

        flash(
            "Please select your water source.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not season:

        flash(
            "Please select the current season.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not previous_crop:

        flash(
            "Please select the previous crop.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if state != "Maharashtra":

        flash(
            "Only Maharashtra is supported.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not district:

        flash(
            "Please select the farm district.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not taluka:

        flash(
            "Please select the farm taluka.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not village:

        flash(
            "Please enter the farm village.",
            "error"
        )

        return redirect(
            form_redirect
        )

    try:

        latitude_value = float(
            latitude
        )

        longitude_value = float(
            longitude
        )

    except (
        ValueError,
        TypeError
    ):

        flash(
            "Please locate this farm before saving.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not (
        -90 <= latitude_value <= 90
    ):

        flash(
            "Invalid farm latitude.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if not (
        -180 <= longitude_value <= 180
    ):

        flash(
            "Invalid farm longitude.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if location_level not in (
        "village",
        "taluka"
    ):

        flash(
            "Please locate this farm before saving.",
            "error"
        )

        return redirect(
            form_redirect
        )

    if farm_id is not None:

        existing_farm = get_farm_by_id(
            farm_id,
            farmer_id
        )

        if existing_farm is None:

            flash(
                "You cannot modify this farm.",
                "error"
            )

            return redirect(
                url_for("farm_details")
            )

    saved_farm_id = add_farm(

        farmer_id=farmer_id,

        farm_name=farm_name,

        area=area_value,

        area_unit=area_unit,

        soil_type=soil_type,

        irrigation=irrigation,

        water_source=water_source,

        season=season,

        previous_crop=previous_crop,

        state=state,

        district=district,

        taluka=taluka,

        village=village,

        latitude=latitude_value,

        longitude=longitude_value,

        location_level=location_level,

        farm_id=farm_id
    )

    if saved_farm_id is None:

        flash(
            "Unable to save farm details. Please try again.",
            "error"
        )

        return redirect(
            form_redirect
        )

    session["active_farm_id"] = (
        saved_farm_id
    )

    if farm_id is None:

        flash(
            "New farm added successfully.",
            "success"
        )

    else:

        flash(
            "Farm details updated successfully.",
            "success"
        )

    return redirect(
        url_for(
            "farm_details",
            farm_id=saved_farm_id
        )
    )


# =========================================================
# DELETE FARM
# =========================================================

@app.route(
    "/delete-farm/<int:farm_id>",
    methods=["POST"]
)
def delete_farm_route(
    farm_id
):

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farm = get_farm_by_id(
        farm_id,
        farmer_id
    )

    if farm is None:

        flash(
            "Farm could not be found.",
            "error"
        )

        return redirect(
            url_for("farm_details")
        )

    deleted = delete_farm(
        farm_id,
        farmer_id
    )

    if not deleted:

        flash(
            "Farm could not be deleted.",
            "error"
        )

        return redirect(
            url_for("farm_details")
        )

    if session.get(
        "active_farm_id"
    ) == farm_id:

        session.pop(
            "active_farm_id",
            None
        )

        remaining_farms = get_farms_by_farmer(
            farmer_id
        )

        if remaining_farms:

            session["active_farm_id"] = (
                remaining_farms[-1]["farm_id"]
            )

    flash(
        "Farm deleted successfully.",
        "success"
    )

    return redirect(
        url_for("farm_details")
    )


# =========================================================
# SELECT FARM
# =========================================================

@app.route(
    "/select-farm/<int:farm_id>"
)
def select_farm(
    farm_id
):

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farm = get_farm_by_id(
        farm_id,
        farmer_id
    )

    if farm is None:

        flash(
            "Farm could not be found.",
            "error"
        )

        return redirect(
            url_for("farm_details")
        )

    session["active_farm_id"] = (
        farm_id
    )

    return redirect(
        url_for(
            "farm_details",
            farm_id=farm_id
        )
    )


# =========================================================
# LIVE WEATHER
# =========================================================

@app.route("/weather")
def weather():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    farm = get_active_farm(
        farmer_id
    )

    if farm is None:

        flash(
            "Please add a farm before using Live Weather.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    latitude = farm["latitude"]
    longitude = farm["longitude"]

    if (
        latitude is None
        or longitude is None
    ):

        flash(
            "Farm coordinates are not available. "
            "Please locate this farm first.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                farm_id=farm["farm_id"]
            )
        )

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    params = {

        "latitude": latitude,

        "longitude": longitude,

        "current":
            (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation,"
                "weather_code,"
                "cloud_cover,"
                "wind_speed_10m"
            ),

        "timezone": "auto"
    }

    try:

        response = requests.get(
            weather_url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        weather_json = response.json()

    except (
        requests.RequestException,
        ValueError
    ):

        location_level = (
            farm["location_level"]
            if (
                "location_level"
                in farm.keys()
                and farm["location_level"]
            )
            else "village"
        )

        if location_level == "village":

            location_name = (
                f"{farm['village']}, "
                f"{farm['taluka']}, "
                f"{farm['district']}"
            )

        else:

            location_name = (
                f"{farm['taluka']}, "
                f"{farm['district']}"
            )

        weather_data = {

            "error":
                "Live weather could not be retrieved right now.",

            "location_name":
                location_name,

            "location_level":
                location_level,

            "farm_name":
                farm["farm_name"],

            "farm_id":
                farm["farm_id"],

            "state":
                farm["state"],

            "district":
                farm["district"],

            "taluka":
                farm["taluka"],

            "village":
                farm["village"]
        }

        return render_template(
            "weather.html",
            weather_data=weather_data
        )

    current = weather_json.get(
        "current",
        {}
    )

    temperature = current.get(
        "temperature_2m"
    )

    humidity = current.get(
        "relative_humidity_2m"
    )

    precipitation = current.get(
        "precipitation"
    )

    weather_code = current.get(
        "weather_code"
    )

    cloud_cover = current.get(
        "cloud_cover"
    )

    wind = current.get(
        "wind_speed_10m"
    )

    weather_time = current.get(
        "time",
        ""
    )

    condition, icon = get_weather_description(
        weather_code
    )

    location_level = (
        farm["location_level"]
        if (
            "location_level"
            in farm.keys()
            and farm["location_level"]
        )
        else "village"
    )

    if location_level == "village":

        location_name = (
            f"{farm['village']}, "
            f"{farm['taluka']}, "
            f"{farm['district']}"
        )

    else:

        location_name = (
            f"{farm['taluka']}, "
            f"{farm['district']}"
        )

    weather_data = {

        "temperature":
            round(
                float(temperature),
                1
            )
            if temperature is not None
            else "--",

        "humidity":
            round(
                float(humidity)
            )
            if humidity is not None
            else "--",

        "precipitation":
            round(
                float(precipitation),
                1
            )
            if precipitation is not None
            else "--",

        "cloud_cover":
            round(
                float(cloud_cover)
            )
            if cloud_cover is not None
            else "--",

        "wind":
            round(
                float(wind),
                1
            )
            if wind is not None
            else "--",

        "condition":
            condition,

        "icon":
            icon,

        "time":
            weather_time,

        "location_name":
            location_name,

        "location_level":
            location_level,

        "farm_name":
            farm["farm_name"],

        "farm_id":
            farm["farm_id"],

        "state":
            farm["state"],

        "district":
            farm["district"],

        "taluka":
            farm["taluka"],

        "village":
            farm["village"]
    }

    return render_template(
        "weather.html",
        weather_data=weather_data
    )


# =========================================================
# AI CENTER
# =========================================================

@app.route("/ai")
def ai_tools():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    template_path = os.path.join(
        app.template_folder,
        "ai-tools",
        "index.html"
    )

    if not os.path.exists(
        template_path
    ):

        flash(
            "AI Tools page is being prepared.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using AI Tools.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    return render_template(
        "ai-tools/index.html",
        active_farm=active_farm
    )


# =========================================================
# GENERIC AI TOOL PAGE
# =========================================================

def render_ai_tool_page(
    template_name,
    tool_name,
    icon="🤖"
):

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            + tool_name
            + ".",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    template_path = os.path.join(
        app.template_folder,
        template_name
    )

    if not os.path.exists(
        template_path
    ):

        flash(
            tool_name
            + " page is not available yet.",
            "error"
        )

        return redirect(
            url_for("ai_tools")
        )

    return render_template(
        template_name,
        active_farm=active_farm
    )


# =========================================================
# SOIL ANALYZER HELPER
# =========================================================

def run_soil_analysis(
    form_data,
    active_farm
):

    if analyze_soil_report is None:

        return {
            "success": False,
            "error":
                "soil_analyzer.py could not be imported."
        }

    try:

        return analyze_soil_report(
            form_data=form_data,
            farm=active_farm
        )

    except TypeError:

        try:

            return analyze_soil_report(
                form_data
            )

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


# =========================================================
# SOIL REPORT ANALYZER
# =========================================================

@app.route(
    "/ai/soil-report-analyzer",
    methods=["GET", "POST"]
)
def soil_report_analyzer():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using Soil Report Analyzer.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    template_name = (
        "ai-tools/soil-report-analyzer.html"
    )

    if request.method == "GET":

        return render_template(
            template_name,
            active_farm=active_farm,
            result=None,
            form_data={}
        )

    form_data = {

        "ph":
            request.form.get(
                "ph",
                ""
            ).strip(),

        "nitrogen":
            request.form.get(
                "nitrogen",
                ""
            ).strip(),

        "phosphorus":
            request.form.get(
                "phosphorus",
                ""
            ).strip(),

        "potassium":
            request.form.get(
                "potassium",
                ""
            ).strip(),

        "organic_carbon":
            request.form.get(
                "organic_carbon",
                ""
            ).strip(),

        "electrical_conductivity":
            request.form.get(
                "electrical_conductivity",
                ""
            ).strip(),

        "soil_type":
            request.form.get(
                "soil_type",
                active_farm["soil_type"]
            ).strip()
    }

    result = run_soil_analysis(
        form_data,
        active_farm
    )

    return render_template(
        template_name,
        active_farm=active_farm,
        result=result,
        form_data=form_data
    )


# =========================================================
# SAVE LATEST SOIL REPORT FOR CROP RECOMMENDATION
# =========================================================

def save_latest_soil_report(result, active_farm):
    """
    Keep the latest analyzed soil values in the logged-in session.

    Crop Recommendation and Fertilizer Advisor read these values
    automatically.

    The values are tied to the current farm_id so a different farm
    cannot accidentally reuse the previous farm's soil report.
    """

    if not isinstance(result, dict):

        return

    if not result.get("success"):

        return

    inputs = result.get("inputs") or {}

    soil_values = {

        "ph":
            inputs.get("ph"),

        "nitrogen":
            inputs.get("nitrogen"),

        "phosphorus":
            inputs.get("phosphorus"),

        "potassium":
            inputs.get("potassium"),

        "organic_carbon":
            inputs.get("organic_carbon"),

        "electrical_conductivity":
            inputs.get(
                "electrical_conductivity"
            )
    }

    if not any(
        value not in (None, "")
        for value in soil_values.values()
    ):

        return

    session["latest_soil_report"] = {

        "farm_id":
            active_farm.get("farm_id"),

        "values":
            soil_values,

        "soil_type":
            active_farm.get(
                "soil_type",
                ""
            ),

        "analyzed_at":
            time.time()
    }


def get_latest_soil_report(active_farm):
    """
    Return the latest soil report only if it belongs to this farm.
    """

    saved = session.get(
        "latest_soil_report"
    )

    if not isinstance(
        saved,
        dict
    ):

        return None

    if str(
        saved.get("farm_id")
    ) != str(
        active_farm.get("farm_id")
    ):

        return None

    values = saved.get(
        "values"
    )

    if not isinstance(
        values,
        dict
    ):

        return None

    return saved


# =========================================================
# SAVE LATEST DISEASE ANALYSIS
# =========================================================

def save_latest_disease_analysis(
    result,
    active_farm
):
    """
    Save the latest Disease Detection result.

    The result is tied to the active farm.
    """

    if not isinstance(
        result,
        dict
    ):

        return

    if not result.get(
        "success"
    ):

        return

    disease_data = {

        "crop":
            result.get(
                "crop",
                ""
            ),

        "disease":
            result.get(
                "disease",
                ""
            ),

        "confidence":
            result.get(
                "confidence",
                ""
            ),

        "severity":
            result.get(
                "severity",
                "Unknown"
            ),

        "image_quality":
            result.get(
                "image_quality",
                "Unknown"
            ),

        "symptoms":
            result.get(
                "symptoms",
                []
            ),

        "possible_causes":
            result.get(
                "possible_causes",
                []
            ),

        "recommendations":
            result.get(
                "recommendations",
                []
            ),

        "prevention":
            result.get(
                "prevention",
                []
            ),

        "warning":
            result.get(
                "warning",
                ""
            )

    }

    session["latest_disease_analysis"] = {

        "farm_id":
            active_farm.get(
                "farm_id"
            ),

        "data":
            disease_data,

        "analyzed_at":
            time.time()

    }


# =========================================================
# SAVE LATEST CROP HEALTH ANALYSIS
# =========================================================

def save_latest_crop_health_analysis(
    result,
    active_farm
):
    """
    Save the latest Crop Health result.

    The result is tied to the active farm.
    """

    if not isinstance(
        result,
        dict
    ):

        return

    if not result.get(
        "success"
    ):

        return

    health_result = result.get(
        "result",
        {}
    )

    if not isinstance(
        health_result,
        dict
    ):

        return

    crop_health_data = {

        "crop":
            health_result.get(
                "crop",
                ""
            ),

        "health_status":
            health_result.get(
                "health_status",
                ""
            ),

        "health_score":
            health_result.get(
                "health_score",
                ""
            ),

        "confidence":
            health_result.get(
                "confidence",
                ""
            ),

        "growth_stage":
            health_result.get(
                "growth_stage",
                ""
            ),

        "image_quality":
            health_result.get(
                "image_quality",
                ""
            ),

        "leaf_condition":
            health_result.get(
                "leaf_condition",
                ""
            ),

        "visible_stress":
            health_result.get(
                "visible_stress",
                []
            ),

        "possible_causes":
            health_result.get(
                "possible_causes",
                []
            ),

        "recommendations":
            health_result.get(
                "recommendations",
                []
            ),

        "prevention":
            health_result.get(
                "prevention",
                []
            ),

        "warning":
            health_result.get(
                "warning",
                ""
            )

    }

    session["latest_crop_health_analysis"] = {

        "farm_id":
            active_farm.get(
                "farm_id"
            ),

        "data":
            crop_health_data,

        "analyzed_at":
            time.time()

    }


# =========================================================
# GET LATEST FARM-SPECIFIC SESSION AI ANALYSIS
# =========================================================

def get_latest_ai_analysis(
    session_key,
    active_farm
):
    """
    Return the latest saved AI analysis only when it belongs
    to the currently selected farm.
    """

    saved = session.get(
        session_key
    )

    if not isinstance(
        saved,
        dict
    ):

        return None

    if str(
        saved.get(
            "farm_id"
        )
    ) != str(
        active_farm.get(
            "farm_id"
        )
    ):

        return None

    data = saved.get(
        "data"
    )

    if not isinstance(
        data,
        dict
    ):

        return None

    return data


# =========================================================
# GET LATEST AI HISTORY RESULT
# =========================================================

def get_latest_feature_analysis(farmer_id, feature, active_farm):
    """
    Get the latest analysis result for a specific AI feature.

    First checks the current session.
    If not available, falls back to AI history.

    Handles both dictionaries and sqlite3.Row objects.
    """

    session_key_map = {
        "disease_detection": "latest_disease_analysis",
        "crop_health": "latest_crop_health_analysis",
    }

    session_key = session_key_map.get(feature)

    # ------------------------------------------------------------
    # 1. CHECK CURRENT SESSION FIRST
    # ------------------------------------------------------------

    if session_key:
        current_result = get_latest_ai_analysis(
            session_key,
            active_farm
        )

        if current_result is not None:
            return current_result

    # ------------------------------------------------------------
    # 2. FALLBACK TO AI HISTORY
    # ------------------------------------------------------------

    try:
        history = get_ai_history(
            farmer_id,
            100
        )

    except Exception as error:
        print(
            "AI History fallback error:",
            error
        )
        return None

    if not history:
        return None

    candidates = []

    # ------------------------------------------------------------
    # 3. READ HISTORY SAFELY
    # ------------------------------------------------------------

    for item in history:

        # sqlite3.Row -> dictionary
        if hasattr(item, "keys"):
            try:
                item = dict(item)
            except Exception:
                pass

        # If somehow still not a dictionary, skip it
        if not isinstance(item, dict):
            continue

        # --------------------------------------------------------
        # CHECK FEATURE
        # --------------------------------------------------------

        if item.get("feature") != feature:
            continue

        answer = item.get("answer", "")

        if not answer:
            continue

        # --------------------------------------------------------
        # PARSE SAVED JSON
        # --------------------------------------------------------

        try:
            parsed = json.loads(answer)

        except (TypeError, ValueError):
            continue

        if not isinstance(parsed, dict):
            continue

        # --------------------------------------------------------
        # CHECK FARM ID
        # --------------------------------------------------------

        saved_farm_id = parsed.get("_farm_id")

        if saved_farm_id is None:
            continue

        if str(saved_farm_id) != str(
            active_farm.get("farm_id")
        ):
            continue

        # --------------------------------------------------------
        # REMOVE INTERNAL FIELD
        # --------------------------------------------------------

        parsed.pop("_farm_id", None)

        candidates.append(
            {
                "created_at": item.get(
                    "created_at",
                    ""
                ),
                "data": parsed
            }
        )

    # ------------------------------------------------------------
    # 4. NOTHING FOUND
    # ------------------------------------------------------------

    if not candidates:
        return None

    # ------------------------------------------------------------
    # 5. SORT NEWEST FIRST
    # ------------------------------------------------------------

    candidates.sort(
        key=lambda item: str(
            item.get("created_at", "")
        ),
        reverse=True
    )

    # ------------------------------------------------------------
    # 6. RETURN LATEST RESULT
    # ------------------------------------------------------------

    return candidates[0].get("data")

# =========================================================
# SOIL ANALYZER API
# =========================================================

@app.route(
    "/api/soil-analyze",
    methods=["POST"]
)
def api_soil_analyze():

    farmer_id = require_login()

    if farmer_id is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please add a farm before using "
                "Soil Report Analyzer."

        }), 400

    if analyze_soil_report is None:

        return jsonify({

            "success":
                False,

            "error":
                "soil_analyzer.py could not be imported."

        }), 500

    # -----------------------------------------------------
    # Uploaded soil report has priority.
    # -----------------------------------------------------

    uploaded = request.files.get(
        "soil_report"
    )

    if uploaded and uploaded.filename:

        if extract_report_values is None:

            return jsonify({

                "success":
                    False,

                "error":
                    "Soil report extraction engine "
                    "is unavailable."

            }), 500

        try:

            extracted = extract_report_values(
                uploaded.stream,
                uploaded.filename
            )

        except Exception as exc:

            return jsonify({

                "success":
                    False,

                "error":
                    f"Could not read the soil report: {exc}"

            }), 422

        if not extracted.get(
            "text_found"
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    "No readable text was found in "
                    "the soil report. Please upload a "
                    "clear PDF/image or use the manual "
                    "soil report fields."

            }), 422

        form_data = (
            extracted.get(
                "extracted",
                {}
            )
            or {}
        )

        form_data["soil_type"] = request.form.get(
            "soil_type",
            active_farm.get(
                "soil_type",
                ""
            )
        ).strip()

        form_data["season"] = request.form.get(
            "season",
            active_farm.get(
                "season",
                ""
            )
        ).strip()

        form_data["crop"] = request.form.get(
            "crop",
            ""
        ).strip()

    else:

        data = request.get_json(
            silent=True
        ) or {}

        def get_value(
            name,
            default=""
        ):

            value = data.get(
                name,
                None
            )

            if value is None:

                value = request.form.get(
                    name,
                    default
                )

            if value is None:

                return default

            return str(
                value
            ).strip()

        form_data = {

            "ph":
                get_value("ph"),

            "nitrogen":
                get_value("nitrogen"),

            "phosphorus":
                get_value("phosphorus"),

            "potassium":
                get_value("potassium"),

            "organic_carbon":
                get_value("organic_carbon"),

            "electrical_conductivity":
                get_value(
                    "electrical_conductivity"
                ),

            "soil_type":
                get_value(
                    "soil_type",
                    active_farm.get(
                        "soil_type",
                        ""
                    )
                ),

            "season":
                get_value(
                    "season",
                    active_farm.get(
                        "season",
                        ""
                    )
                ),

            "crop":
                get_value("crop")
        }

    result = run_soil_analysis(
        form_data,
        active_farm
    )

    if result is None:

        result = {

            "success":
                False,

            "error":
                "Soil analyzer returned no result."

        }

    if not isinstance(
        result,
        dict
    ):

        result = {

            "success":
                True,

            "result":
                result

        }

    if result.get(
        "success"
    ):

        save_latest_soil_report(
            result,
            active_farm
        )

    return jsonify(
        result
    )


# =========================================================
# CROP RECOMMENDATION V2 HELPER
# =========================================================

def run_crop_recommendation(
    form_data,
    active_farm
):
    """
    Run crop recommendation using the saved soil report
    + farm data.
    """

    if recommend_crops is None:

        return {

            "success":
                False,

            "error":
                "crop_recommendation.py could not "
                "be imported."

        }

    saved = get_latest_soil_report(
        active_farm
    )

    if saved is None:

        return {

            "success":
                False,

            "error":
                "No soil report is available for "
                "this farm. Please analyze/upload "
                "the soil report first."

        }

    soil_data = dict(
        saved.get(
            "values"
        )
        or {}
    )

    soil_data["soil_type"] = active_farm.get(
        "soil_type",
        saved.get(
            "soil_type",
            ""
        )
    )

    farm_data = {}

    try:

        for key in active_farm.keys():

            farm_data[key] = (
                active_farm[key]
            )

    except Exception:

        farm_data = {}

    try:

        return recommend_crops(

            farm=farm_data,

            soil_data=soil_data,

            top_n=5

        )

    except Exception as error:

        return {

            "success":
                False,

            "error":
                str(error)

        }


# =========================================================
# BUILD CROP FORM DATA
# =========================================================

def build_crop_form_data(
    source,
    active_farm
):
    """
    Build display data from the saved soil report
    and farm record.

    Soil numbers are deliberately NOT read from request.form.
    This prevents duplicate manual N/P/K/pH entry after the
    soil report has been analyzed.
    """

    saved = get_latest_soil_report(
        active_farm
    )

    values = {}

    if saved:

        values = dict(
            saved.get(
                "values"
            )
            or {}
        )

    return {

        "nitrogen":
            values.get(
                "nitrogen",
                ""
            ),

        "phosphorus":
            values.get(
                "phosphorus",
                ""
            ),

        "potassium":
            values.get(
                "potassium",
                ""
            ),

        "ph":
            values.get(
                "ph",
                ""
            ),

        "organic_carbon":
            values.get(
                "organic_carbon",
                ""
            ),

        "electrical_conductivity":
            values.get(
                "electrical_conductivity",
                ""
            ),

        "soil_type":
            active_farm.get(
                "soil_type",
                ""
            ),

        "season":
            active_farm.get(
                "season",
                ""
            ),

        "irrigation":
            active_farm.get(
                "irrigation",
                ""
            ),

        "water_source":
            active_farm.get(
                "water_source",
                ""
            ),

        "area":
            active_farm.get(
                "area",
                ""
            ),

        "area_unit":
            active_farm.get(
                "area_unit",
                ""
            ),

        "previous_crop":
            active_farm.get(
                "previous_crop",
                "unknown"
            )
    }


# =========================================================
# CROP RECOMMENDATION
# =========================================================

@app.route(
    "/ai/crop-recommendation",
    methods=["GET", "POST"]
)
def crop_recommendation():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            "AI Crop Recommendation.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    template_name = (
        "ai-tools/crop-recommendation.html"
    )

    form_data = build_crop_form_data(
        {},
        active_farm
    )

    saved_soil = get_latest_soil_report(
        active_farm
    )

    if saved_soil is None:

        return render_template(

            template_name,

            active_farm=active_farm,

            result={

                "success":
                    False,

                "error":
                    "No soil report is available for "
                    "this farm. Please analyze/upload "
                    "the soil report first."

            },

            form_data=form_data,

            soil_report=None

        )

    result = None

    if request.method == "POST":

        result = run_crop_recommendation(

            form_data,

            active_farm

        )

        if result is None:

            result = {

                "success":
                    False,

                "error":
                    "Crop recommendation returned "
                    "no result."

            }

    return render_template(

        template_name,

        active_farm=active_farm,

        result=result,

        form_data=form_data,

        soil_report=saved_soil

    )


# =========================================================
# CROP RECOMMENDATION API V2
# =========================================================

@app.route(
    "/api/crop-recommendation",
    methods=["POST"]
)
def api_crop_recommendation():

    farmer_id = require_login()

    if farmer_id is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please add a farm before using "
                "AI Crop Recommendation."

        }), 400

    saved_soil = get_latest_soil_report(
        active_farm
    )

    if saved_soil is None:

        return jsonify({

            "success":
                False,

            "error":
                "No soil report is available for "
                "this farm. Analyze the soil report "
                "first."

        }), 400

    form_data = build_crop_form_data(
        {},
        active_farm
    )

    result = run_crop_recommendation(

        form_data,

        active_farm

    )

    if result is None:

        result = {

            "success":
                False,

            "error":
                "Crop recommendation returned "
                "no result."

        }

    return jsonify(
        result
    )


# =========================================================
# AI DISEASE DETECTION
# =========================================================

@app.route(
    "/ai/disease-detection",
    methods=["GET", "POST"]
)
def disease_detection():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            "AI Disease Detection.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    template_name = (
        "ai-tools/disease-detection.html"
    )

    result = None

    if request.method == "POST":

        if detect_plant_disease is None:

            result = {

                "success":
                    False,

                "error":
                    "disease_detection.py could not "
                    "be imported."

            }

        else:

            image_file = request.files.get(
                "plant_image"
            )

            crop_name = request.form.get(
                "crop_name",
                ""
            ).strip()

            if (
                not image_file
                or not image_file.filename
            ):

                result = {

                    "success":
                        False,

                    "error":
                        "Please upload a plant or "
                        "leaf image."

                }

            else:

                result = detect_plant_disease(

                    image_file,

                    crop_name

                )

                # -------------------------------------------------
                # SAVE LATEST DISEASE ANALYSIS
                # -------------------------------------------------

                if (
                    isinstance(result, dict)
                    and result.get("success")
                ):

                    save_latest_disease_analysis(
                        result,
                        active_farm
                    )

                # -------------------------------------------------
                # SAVE SUCCESSFUL DISEASE ANALYSIS TO AI HISTORY
                # -------------------------------------------------

                if (
                    isinstance(result, dict)
                    and result.get("success")
                ):

                    try:

                        history_data = {

                            "_farm_id":
                                active_farm.get(
                                    "farm_id"
                                ),

                            "crop":
                                result.get(
                                    "crop",
                                    ""
                                ),

                            "disease":
                                result.get(
                                    "disease",
                                    ""
                                ),

                            "confidence":
                                result.get(
                                    "confidence",
                                    0
                                ),

                            "severity":
                                result.get(
                                    "severity",
                                    "Unknown"
                                ),

                            "image_quality":
                                result.get(
                                    "image_quality",
                                    "Unknown"
                                ),

                            "symptoms":
                                result.get(
                                    "symptoms",
                                    []
                                ),

                            "possible_causes":
                                result.get(
                                    "possible_causes",
                                    []
                                ),

                            "recommendations":
                                result.get(
                                    "recommendations",
                                    []
                                ),

                            "prevention":
                                result.get(
                                    "prevention",
                                    []
                                ),

                            "warning":
                                result.get(
                                    "warning",
                                    ""
                                )
                        }

                        question = (
                            f"Disease detection for "
                            f"{crop_name or 'unknown crop'}"
                        )

                        answer = json.dumps(

                            history_data,

                            ensure_ascii=False

                        )

                        add_ai_history(

                            farmer_id,

                            "disease_detection",

                            question,

                            answer

                        )

                        print(
                            "AI History: Disease "
                            "analysis saved."
                        )

                    except Exception as error:

                        print(
                            "AI History save error:",
                            error
                        )

    return render_template(

        template_name,

        active_farm=active_farm,

        result=result

    )


# =========================================================
# AI HISTORY
# =========================================================

@app.route("/ai-history")
def ai_history():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    try:

        history = get_ai_history(
            farmer_id
        )

    except Exception as error:

        print(
            "AI History load error:",
            error
        )

        history = []

        flash(
            "Unable to load AI history.",
            "error"
        )

    return render_template(

        "ai_history.html",

        history=history

    )


# =========================================================
# AI CROP HEALTH
# =========================================================

@app.route(
    "/ai/crop-health",
    methods=["GET", "POST"]
)
def crop_health():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            "Crop Health Analysis.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    result = None

    if request.method == "POST":

        if detect_crop_health is None:

            result = {

                "success":
                    False,

                "error":
                    "crop_health.py could not "
                    "be imported."

            }

        else:

            image_file = request.files.get(
                "crop_image"
            )

            crop_name = request.form.get(
                "crop_name",
                ""
            ).strip()

            if (
                not image_file
                or not image_file.filename
            ):

                result = {

                    "success":
                        False,

                    "error":
                        "Please upload a crop image."

                }

            else:

                result = detect_crop_health(

                    image_file=image_file,

                    crop_name=crop_name,

                    farm=active_farm

                )

                # -------------------------------------------------
                # SAVE LATEST CROP HEALTH ANALYSIS
                # -------------------------------------------------

                if (
                    isinstance(result, dict)
                    and result.get("success")
                ):

                    save_latest_crop_health_analysis(
                        result,
                        active_farm
                    )

                # -------------------------------------------------
                # SAVE SUCCESSFUL CROP HEALTH ANALYSIS
                # TO AI HISTORY
                # -------------------------------------------------

                if (
                    isinstance(result, dict)
                    and result.get("success")
                ):

                    try:

                        history_result = result.get(
                            "result",
                            {}
                        )

                        history_data = {

                            "_farm_id":
                                active_farm.get(
                                    "farm_id"
                                )

                        }

                        if isinstance(
                            history_result,
                            dict
                        ):

                            history_data.update(
                                history_result
                            )

                        question = (
                            f"Crop health analysis for "
                            f"{crop_name or history_result.get('crop', 'unknown crop')}"
                        )

                        answer = json.dumps(
                            history_data,
                            ensure_ascii=False
                        )

                        add_ai_history(
                            farmer_id,
                            "crop_health",
                            question,
                            answer
                        )

                        print(
                            "AI History: Crop health "
                            "analysis saved."
                        )

                    except Exception as error:

                        print(
                            "AI History save error:",
                            error
                        )

    return render_template(

        "ai-tools/crop-health.html",

        active_farm=active_farm,

        result=result

    )


# =========================================================
# AI FERTILIZER ADVISOR
# =========================================================

@app.route(
    "/ai/fertilizer-advisor",
    methods=["GET", "POST"]
)
def fertilizer_advisor():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using "
            "AI Fertilizer Advisor.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    # ---------------------------------------------------------
    # SAVED SOIL REPORT
    # ---------------------------------------------------------

    saved_soil = get_latest_soil_report(
        active_farm
    )

    # ---------------------------------------------------------
    # LATEST DISEASE DETECTION
    # ---------------------------------------------------------

    latest_disease = get_latest_feature_analysis(

        farmer_id,

        "disease_detection",

        active_farm

    )

    # ---------------------------------------------------------
    # LATEST CROP HEALTH
    # ---------------------------------------------------------

    latest_crop_health = get_latest_feature_analysis(

        farmer_id,

        "crop_health",

        active_farm

    )

    result = None

    crop_name = ""

    # ---------------------------------------------------------
    # SOIL REPORT IS REQUIRED
    # ---------------------------------------------------------

    if saved_soil is None:

        result = {

            "success":
                False,

            "error":
                "No soil report is available for this farm. "
                "Please analyze the soil report first."

        }

        return render_template(

            "ai-tools/fertilizer-advisor.html",

            active_farm=active_farm,

            soil_report=None,

            disease_analysis=latest_disease,

            crop_health_analysis=latest_crop_health,

            result=result,

            crop_name=""

        )

    # ---------------------------------------------------------
    # POST
    # ---------------------------------------------------------

    if request.method == "POST":

        crop_name = request.form.get(
            "crop_name",
            ""
        ).strip()

        if not crop_name:

            result = {

                "success":
                    False,

                "error":
                    "Please enter the current crop name."

            }

        elif analyze_fertilizer is None:

            result = {

                "success":
                    False,

                "error":
                    "fertilizer_advisor.py could not be imported."

            }

        else:

            soil_data = dict(

                saved_soil.get(
                    "values"
                )
                or {}

            )

            result = analyze_fertilizer(

                crop_name=crop_name,

                farm=active_farm,

                soil_data=soil_data,

                disease_data=latest_disease,

                crop_health_data=latest_crop_health

            )

            # -------------------------------------------------
            # SAVE SUCCESSFUL FERTILIZER ADVICE
            # -------------------------------------------------

            if (
                isinstance(result, dict)
                and result.get("success")
            ):

                try:

                    history_result = dict(
                        result.get("result") or {}
                    )

                    history_result["_farm_id"] = active_farm.get(
                        "farm_id"
                    )

                    history_result["_crop_name"] = crop_name

                    question = (
                        f"Fertilizer advice for "
                        f"{crop_name or 'unknown crop'}"
                    )

                    answer = json.dumps(

                        history_result,

                        ensure_ascii=False

                    )

                    add_ai_history(

                        farmer_id,

                        "fertilizer_advisor",

                        question,

                        answer

                    )

                    print(
                        "AI History: Fertilizer "
                        "advice saved."
                    )

                except Exception as error:

                    print(
                        "AI History save error:",
                        error
                    )

    return render_template(

        "ai-tools/fertilizer-advisor.html",

        active_farm=active_farm,

        soil_report=saved_soil,

        disease_analysis=latest_disease,

        crop_health_analysis=latest_crop_health,

        result=result,

        crop_name=crop_name

    )


# =========================================================
# AI IRRIGATION PLANNER
# SIMPLE WATER IRRIGATION DECISION SUPPORT
# =========================================================

OPEN_METEO_IRRIGATION_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


def irrigation_clean_text(value):
    """Return a safe trimmed string."""
    if value is None:
        return ""

    return str(value).strip()


def irrigation_to_float(value):
    """Convert a value to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def irrigation_farm_value(
    farm,
    key,
    default=""
):
    """Read farm data safely from a dict-like farm object."""
    try:
        value = farm.get(
            key,
            default
        )
    except AttributeError:
        try:
            value = farm[key]
        except (
            KeyError,
            IndexError,
            TypeError
        ):
            value = default

    if value is None:
        return default

    return value


def fetch_irrigation_weather(
    farm
):
    """
    Read weather for the SAVED FARM LOCATION.

    This deliberately does not use the computer or phone location.
    """

    latitude = irrigation_to_float(
        irrigation_farm_value(
            farm,
            "latitude"
        )
    )

    longitude = irrigation_to_float(
        irrigation_farm_value(
            farm,
            "longitude"
        )
    )

    if (
        latitude is None
        or longitude is None
    ):
        return {
            "success": False,
            "error":
                "Farm coordinates are not available. "
                "Please locate this farm first."
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
            OPEN_METEO_IRRIGATION_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        weather_json = response.json()

    except (
        requests.RequestException,
        ValueError
    ) as error:

        return {
            "success": False,
            "error":
                "Weather service is unavailable right now. "
                + str(error)
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

    rain_probability = hourly.get(
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

        current_index = (
            len(times) // 2
            if times
            else 0
        )

    past_values = precipitation[
        max(
            0,
            current_index - 24
        ):
        current_index
    ]

    future_values = precipitation[
        current_index + 1:
        current_index + 25
    ]

    future_probability_values = (
        rain_probability[
            current_index + 1:
            current_index + 25
        ]
    )

    future_temperature_values = [

        irrigation_to_float(value)

        for value in temperatures[
            current_index + 1:
            current_index + 25
        ]

        if irrigation_to_float(value)
        is not None
    ]

    future_humidity_values = [

        irrigation_to_float(value)

        for value in humidities[
            current_index + 1:
            current_index + 25
        ]

        if irrigation_to_float(value)
        is not None
    ]

    future_wind_values = [

        irrigation_to_float(value)

        for value in winds[
            current_index + 1:
            current_index + 25
        ]

        if irrigation_to_float(value)
        is not None
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
        ]
        or [0]
    )

    current_temperature = irrigation_to_float(
        current.get(
            "temperature_2m"
        )
    )

    current_humidity = irrigation_to_float(
        current.get(
            "relative_humidity_2m"
        )
    )

    current_precipitation = irrigation_to_float(
        current.get(
            "precipitation"
        )
    )

    current_wind = irrigation_to_float(
        current.get(
            "wind_speed_10m"
        )
    )

    max_temperature = (
        max(
            future_temperature_values
        )
        if future_temperature_values
        else None
    )

    min_humidity = (
        min(
            future_humidity_values
        )
        if future_humidity_values
        else None
    )

    max_wind = (
        max(
            future_wind_values
        )
        if future_wind_values
        else None
    )

    return {

        "success": True,

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

    crop_name = irrigation_clean_text(
        crop_name
    )

    growth_stage = irrigation_clean_text(
        growth_stage
    )

    soil_moisture = irrigation_clean_text(
        soil_moisture
    ).lower()

    field_observation = irrigation_clean_text(
        field_observation
    )

    if not crop_name:

        return {
            "success": False,
            "error": "Please enter the crop name."
        }

    if not growth_stage:

        return {
            "success": False,
            "error": "Please select the crop growth stage."
        }

    allowed_moisture = {
        "dry",
        "slightly_dry",
        "moist",
        "wet",
        "unknown"
    }

    if soil_moisture not in allowed_moisture:
        soil_moisture = "unknown"

    weather = fetch_irrigation_weather(
        farm
    )

    if not weather["success"]:

        return {

            "success": True,

            "status": "field_check",

            "status_label":
                "⚪ Field Check Required",

            "status_class":
                "field-check",

            "summary":
                "A reliable automatic irrigation "
                "decision cannot be made because "
                "farm weather is unavailable.",

            "reasons": [
                "Weather information could not be retrieved.",
                "Actual field moisture should be checked."
            ],

            "actions": [
                "Inspect the soil near the crop root zone.",
                "Use normal farm irrigation practice "
                "according to the field condition."
            ],

            "field_check":
                "Check whether the root-zone soil is "
                "dry, moist or wet.",

            "reassess":
                "Check again after the field inspection.",

            "warning":
                weather["error"],

            "weather": None,

            "effects": {

                "rainfall":
                    "Rainfall information is unavailable.",

                "weather":
                    "Weather information is unavailable.",

                "soil":
                    "Actual soil moisture should guide the decision.",

                "crop_stage":
                    (
                        f"Current crop stage: {growth_stage}."
                    ),

                "irrigation":
                    (
                        "Irrigation method: "
                        + irrigation_clean_text(
                            irrigation_farm_value(
                                farm,
                                "irrigation"
                            )
                        )
                    )
            }
        }

    current = weather["current"]

    rainfall = weather["rainfall"]

    forecast = weather["forecast"]

    recent_rain = rainfall[
        "recent_24h_mm"
    ]

    next_rain = rainfall[
        "next_24h_mm"
    ]

    next_rain_probability = rainfall[
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
        or dry_air_signal
        or windy_signal
    )

    useful_rain_expected = (

        next_rain >= 5

        or

        (
            next_rain >= 2
            and next_rain_probability >= 60
        )
    )

    meaningful_recent_rain = (
        recent_rain >= 5
    )

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

    soil_type = irrigation_clean_text(
        irrigation_farm_value(
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

    reasons = []

    actions = []

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

    elif soil_moisture == "dry":

        if useful_rain_expected:

            status = "monitor"

            status_label = "🟡 Monitor"

            status_class = "monitor"

            reasons.append(
                "The field is reported as dry."
            )

            reasons.append(
                "Rainfall is expected within the next 24 hours."
            )

            if sensitive_stage:

                reasons.append(
                    "The crop is at a moisture-sensitive "
                    "growth stage, so water stress should "
                    "be watched closely."
                )

            actions.append(
                "Check root-zone moisture before deciding "
                "to irrigate."
            )

        else:

            status = "needed"

            status_label = "🔴 Irrigation Needed"

            status_class = "needed"

            reasons.append(
                "The field is reported as dry."
            )

            reasons.append(
                "No useful rainfall is expected within "
                "the next 24 hours."
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
                "Delay irrigation and reassess after rainfall."
            )

        else:

            status = "monitor"

            status_label = "🟡 Monitor"

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
                    "The crop stage makes moisture monitoring "
                    "important."
                )

            actions.append(
                "Check root-zone moisture before irrigating."
            )

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
                "Delay irrigation and recheck after rainfall."
            )

        elif water_loss_signal:

            status = "monitor"

            status_label = "🟡 Monitor"

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
                "Delay irrigation while the soil remains "
                "adequately moist."
            )

    else:

        if (
            meaningful_recent_rain
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

            status_label = "🟡 Monitor"

            status_class = "monitor"

            reasons.append(
                "No useful rainfall is expected and "
                "weather may increase water loss."
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

    rainfall_effect = (

        f"Recent 24-hour rainfall: "
        f"{recent_rain:.1f} mm. "
        f"Expected next 24-hour rainfall: "
        f"{next_rain:.1f} mm. "
        f"Rain probability: "
        f"{next_rain_probability:.0f}%."
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
        "growth stage, so water stress should be "
        "monitored closely."

        if sensitive_stage

        else

        f"{growth_stage} is included as crop-stage "
        "context for the irrigation decision."
    )

    irrigation_method = irrigation_clean_text(
        irrigation_farm_value(
            farm,
            "irrigation"
        )
    )

    water_source = irrigation_clean_text(
        irrigation_farm_value(
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

    field_check = (
        "Check the soil near the crop root zone. "
        "Do not judge only from the surface appearance."
    )

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

    warning = (
        "This is decision-support guidance, not a "
        "guaranteed irrigation requirement. Local "
        "field conditions may differ from weather data."
    )

    return {

        "success": True,

        "status": status,

        "status_label": status_label,

        "status_class": status_class,

        "summary":
            reasons[0]
            if reasons
            else status_label,

        "reasons": reasons,

        "actions": actions,

        "field_check": field_check,

        "reassess": reassess,

        "warning": warning,

        "weather": weather,

        "effects": {

            "rainfall": rainfall_effect,

            "weather": weather_effect,

            "soil": soil_effect,

            "crop_stage": crop_stage_effect,

            "irrigation": irrigation_effect
        },

        "inputs": {

            "farm_name":
                irrigation_clean_text(
                    irrigation_farm_value(
                        farm,
                        "farm_name"
                    )
                ),

            "crop_name": crop_name,

            "growth_stage": growth_stage,

            "soil_type": soil_type,

            "irrigation": irrigation_method,

            "water_source": water_source,

            "soil_moisture": soil_moisture,

            "field_observation": field_observation
        }
    }


@app.route(
    "/ai/irrigation-planner",
    methods=["GET", "POST"]
)
def irrigation_planner():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using Smart Irrigation Planner.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    result = None

    form_data = {

        "crop_name": "",

        "growth_stage": "",

        "soil_moisture": "unknown",

        "field_observation": ""
    }

    if request.method == "POST":

        form_data = {

            "crop_name":
                request.form.get(
                    "crop_name",
                    ""
                ).strip(),

            "growth_stage":
                request.form.get(
                    "growth_stage",
                    ""
                ).strip(),

            "soil_moisture":
                request.form.get(
                    "soil_moisture",
                    "unknown"
                ).strip(),

            "field_observation":
                request.form.get(
                    "field_observation",
                    ""
                ).strip()
        }

        try:

            result = analyze_irrigation(

                farm=active_farm,

                crop_name=
                    form_data["crop_name"],

                growth_stage=
                    form_data["growth_stage"],

                soil_moisture=
                    form_data["soil_moisture"],

                field_observation=
                    form_data["field_observation"]
            )

        except Exception as error:

            result = {

                "success": False,

                "error":
                    "Irrigation analysis failed: "
                    + str(error)
            }

    return render_template(

        "ai-tools/irrigation-planner.html",

        active_farm=active_farm,

        result=result,

        form_data=form_data
    )


# =========================================================
# AI CROP CALENDAR
# SIMPLE CROP TIMELINE DECISION SUPPORT
# =========================================================

CROP_CALENDAR_DURATION_DAYS = {

    "onion": 120,
    "tomato": 140,
    "potato": 100,
    "soybean": 100,
    "maize": 90,
    "cotton": 150,
    "wheat": 120,
    "rice": 125,
    "french bean": 70,
    "ridge gourd": 125,
    "okra": 90
}


def crop_calendar_duration(crop_name):

    name = str(crop_name or "").strip().lower()

    for crop, days in CROP_CALENDAR_DURATION_DAYS.items():

        if crop in name:
            return days

    return None


def add_days_to_date(date_value, days):

    from datetime import timedelta

    return date_value + timedelta(
        days=int(days)
    )


def format_calendar_date(date_value):

    return date_value.strftime(
        "%d %b %Y"
    )


def build_crop_calendar(
    crop_name,
    variety,
    season,
    sowing_date,
    expected_duration=""
):
    """
    Build a simple farm planning calendar.

    The duration is an approximate planning value.
    Variety, location, weather and management can change the
    actual crop duration.
    """

    from datetime import datetime

    crop_name = str(
        crop_name or ""
    ).strip()

    variety = str(
        variety or ""
    ).strip()

    season = str(
        season or ""
    ).strip()

    if not crop_name:

        return {
            "success": False,
            "error": "Please enter the crop name."
        }

    if not sowing_date:

        return {
            "success": False,
            "error": "Please select the sowing or transplanting date."
        }

    try:

        start_date = datetime.strptime(
            sowing_date,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return {
            "success": False,
            "error": "Please select a valid date."
        }

    auto_duration = crop_calendar_duration(
        crop_name
    )

    duration_source = ""

    if auto_duration is not None:

        duration_days = auto_duration

        duration_source = (
            "Approximate planning duration based on a "
            "starter crop reference."
        )

    else:

        try:

            duration_days = int(
                float(expected_duration)
            )

        except (TypeError, ValueError):

            return {
                "success": False,
                "error": (
                    "This crop does not have a configured planning "
                    "duration yet. Enter its expected crop duration "
                    "in days."
                )
            }

        if duration_days < 30 or duration_days > 500:

            return {
                "success": False,
                "error": (
                    "Expected crop duration should be between "
                    "30 and 500 days."
                )
            }

        duration_source = (
            "Duration supplied by the farmer for this crop."
        )

    harvest_date = add_days_to_date(
        start_date,
        duration_days
    )

    # --------------------------------------------------------
    # PLANNING STAGE WINDOWS
    # --------------------------------------------------------

    stages = [

        {
            "name": "Sowing / Transplanting",
            "start": 0,
            "end": 0,
            "activity": (
                "Complete sowing or transplanting and ensure "
                "the field has suitable moisture."
            ),
            "irrigation": (
                "Check soil moisture after planting and avoid "
                "both water shortage and unnecessary excess water."
            ),
            "nutrient": (
                "Follow the crop's locally recommended nutrient plan."
            ),
            "disease": (
                "Watch for poor emergence, damping-off or early stress."
            ),
            "action": "Confirm uniform planting and field condition."
        },

        {
            "name": "Germination / Establishment",
            "start": 1,
            "end": 10,
            "activity": (
                "Monitor emergence and early plant establishment."
            ),
            "irrigation": (
                "Maintain suitable moisture according to soil and crop condition."
            ),
            "nutrient": (
                "Check early crop growth and follow the recommended nutrient schedule."
            ),
            "disease": (
                "Inspect young plants regularly for early symptoms or abnormal growth."
            ),
            "action": "Check plant population and early growth."
        },

        {
            "name": "Vegetative Growth",
            "start": 10,
            "end": 40,
            "activity": (
                "Monitor canopy growth, weeds and overall crop development."
            ),
            "irrigation": (
                "Monitor root-zone moisture and adjust irrigation to current weather and soil condition."
            ),
            "nutrient": (
                "Check crop growth and use the recommended crop-stage nutrient schedule."
            ),
            "disease": (
                "Inspect leaves and stems regularly for disease or pest symptoms."
            ),
            "action": "Keep the crop uniformly growing and inspect the field regularly."
        },

        {
            "name": "Flowering",
            "start": 40,
            "end": 60,
            "activity": (
                "Monitor flowering and avoid unnecessary crop stress."
            ),
            "irrigation": (
                "Pay close attention to moisture because water stress can affect sensitive stages."
            ),
            "nutrient": (
                "Follow the locally recommended nutrient plan for the flowering stage."
            ),
            "disease": (
                "Increase scouting for visible disease and crop stress."
            ),
            "action": "Check crop moisture, flowering and visible stress."
        },

        {
            "name": "Fruit / Bulb / Pod Development",
            "start": 60,
            "end": 85,
            "activity": (
                "Monitor development of the harvested plant part and overall crop condition."
            ),
            "irrigation": (
                "Maintain suitable moisture while considering rainfall and forecast conditions."
            ),
            "nutrient": (
                "Follow the crop-specific nutrient plan for development."
            ),
            "disease": (
                "Continue regular scouting for visible symptoms and quality problems."
            ),
            "action": "Check development, moisture and crop health."
        },

        {
            "name": "Maturity",
            "start": 85,
            "end": 100,
            "activity": (
                "Monitor maturity signs and prepare for harvest."
            ),
            "irrigation": (
                "Avoid unnecessary irrigation and reassess according to crop condition and weather."
            ),
            "nutrient": (
                "Avoid making unplanned nutrient changes close to harvest."
            ),
            "disease": (
                "Continue checking for late disease or quality issues."
            ),
            "action": "Check maturity indicators and plan harvesting."
        },

        {
            "name": "Harvest",
            "start": 100,
            "end": 100,
            "activity": (
                "Harvest when the crop reaches the appropriate maturity for its purpose."
            ),
            "irrigation": (
                "Use irrigation decisions appropriate to the crop's harvest stage and local practice."
            ),
            "nutrient": (
                "No new nutrient recommendation is generated by this basic calendar."
            ),
            "disease": (
                "Inspect harvested produce and handle it carefully."
            ),
            "action": "Prepare labour, equipment and post-harvest handling."
        }
    ]

    timeline = []

    for stage in stages:

        start_day = round(
            duration_days * stage["start"] / 100
        )

        end_day = round(
            duration_days * stage["end"] / 100
        )

        stage_start = add_days_to_date(
            start_date,
            start_day
        )

        stage_end = add_days_to_date(
            start_date,
            end_day
        )

        timeline.append({

            "name": stage["name"],

            "start_day": start_day,

            "end_day": end_day,

            "start_date": format_calendar_date(
                stage_start
            ),

            "end_date": format_calendar_date(
                stage_end
            ),

            "expected_period": (
                format_calendar_date(stage_start)
                if stage_start == stage_end
                else (
                    f"{format_calendar_date(stage_start)}"
                    f" – {format_calendar_date(stage_end)}"
                )
            ),

            "activity": stage["activity"],

            "irrigation": stage["irrigation"],

            "nutrient": stage["nutrient"],

            "disease": stage["disease"],

            "action": stage["action"]
        })

    return {

        "success": True,

        "crop": crop_name,

        "variety": variety,

        "season": season,

        "sowing_date": format_calendar_date(
            start_date
        ),

        "harvest_date": format_calendar_date(
            harvest_date
        ),

        "duration_days": duration_days,

        "duration_source": duration_source,

        "timeline": timeline,

        "warning": (
            "This is a planning calendar, not a guaranteed crop schedule. "
            "Actual growth and maturity can change with variety, weather, "
            "soil, planting method and local farm conditions."
        )
    }


@app.route(
    "/ai/crop-calendar",
    methods=["GET", "POST"]
)
def crop_calendar():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using AI Crop Calendar.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    result = None

    form_data = {

        "crop_name": "",

        "variety": "",

        "season": active_farm.get(
            "season",
            ""
        ),

        "sowing_date": "",

        "expected_duration": ""
    }

    if request.method == "POST":

        form_data = {

            "crop_name": request.form.get(
                "crop_name",
                ""
            ).strip(),

            "variety": request.form.get(
                "variety",
                ""
            ).strip(),

            "season": request.form.get(
                "season",
                ""
            ).strip(),

            "sowing_date": request.form.get(
                "sowing_date",
                ""
            ).strip(),

            "expected_duration": request.form.get(
                "expected_duration",
                ""
            ).strip()
        }

        result = build_crop_calendar(

            crop_name=form_data["crop_name"],

            variety=form_data["variety"],

            season=form_data["season"],

            sowing_date=form_data["sowing_date"],

            expected_duration=form_data["expected_duration"]
        )

        if isinstance(result, dict) and result.get("success"):

            try:
                calendar_history = dict(result)
                calendar_history["_farm_id"] = active_farm.get("farm_id")

                add_ai_history(
                    farmer_id,
                    "crop_calendar",
                    f"Crop calendar for {form_data['crop_name']}",
                    json.dumps(calendar_history, ensure_ascii=False)
                )
            except Exception as error:
                print("AI History crop calendar save error:", error)

    return render_template(

        "ai-tools/crop-calendar.html",

        active_farm=active_farm,

        result=result,

        form_data=form_data
    )


# =========================================================
# AI WEATHER INTELLIGENCE
# SIMPLE CROP WEATHER IMPACT ANALYSIS
# =========================================================

WEATHER_INTELLIGENCE_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


def weather_intel_text(value):
    if value is None:
        return ""
    return str(value).strip()


def weather_intel_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_weather_intelligence_weather(farm):
    """
    Get current and next-24-hour weather for the SAVED FARM location.
    """

    latitude = weather_intel_float(
        farm.get("latitude")
    )

    longitude = weather_intel_float(
        farm.get("longitude")
    )

    if latitude is None or longitude is None:

        return {
            "success": False,
            "error":
                "Farm coordinates are not available. "
                "Please locate this farm first."
        }

    params = {

        "latitude": latitude,

        "longitude": longitude,

        "timezone": "auto",

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "weather_code,"
            "cloud_cover,"
            "wind_speed_10m"
        ),

        "hourly": (
            "precipitation,"
            "precipitation_probability,"
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m"
        ),

        "forecast_hours": 24
    }

    try:

        response = requests.get(
            WEATHER_INTELLIGENCE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError
    ) as error:

        return {
            "success": False,
            "error":
                "Weather service is unavailable right now. "
                + str(error)
        }

    current = data.get("current", {}) or {}
    hourly = data.get("hourly", {}) or {}

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

    future_rain = [
        weather_intel_float(value)
        for value in precipitation[:24]
        if weather_intel_float(value) is not None
    ]

    future_probability = [
        weather_intel_float(value)
        for value in precipitation_probability[:24]
        if weather_intel_float(value) is not None
    ]

    future_temperature = [
        weather_intel_float(value)
        for value in temperatures[:24]
        if weather_intel_float(value) is not None
    ]

    future_humidity = [
        weather_intel_float(value)
        for value in humidities[:24]
        if weather_intel_float(value) is not None
    ]

    future_wind = [
        weather_intel_float(value)
        for value in winds[:24]
        if weather_intel_float(value) is not None
    ]

    return {

        "success": True,

        "timezone": data.get(
            "timezone",
            "auto"
        ),

        "current": {

            "temperature": weather_intel_float(
                current.get("temperature_2m")
            ),

            "humidity": weather_intel_float(
                current.get("relative_humidity_2m")
            ),

            "precipitation": weather_intel_float(
                current.get("precipitation")
            ),

            "wind": weather_intel_float(
                current.get("wind_speed_10m")
            ),

            "cloud_cover": weather_intel_float(
                current.get("cloud_cover")
            ),

            "weather_code": current.get(
                "weather_code"
            )
        },

        "forecast": {

            "rain_24h": round(
                sum(future_rain),
                1
            ),

            "rain_probability": round(
                max(future_probability)
                if future_probability
                else 0
            ),

            "max_temperature": (
                round(max(future_temperature), 1)
                if future_temperature
                else None
            ),

            "min_humidity": (
                round(min(future_humidity), 1)
                if future_humidity
                else None
            ),

            "max_wind": (
                round(max(future_wind), 1)
                if future_wind
                else None
            )
        }
    }


def analyze_weather_intelligence(
    farm,
    crop_name,
    growth_stage
):
    """
    Simple, explainable crop-weather screening.

    These are decision-support screening rules, not guaranteed
    agronomic thresholds for every crop or locality.
    """

    crop_name = weather_intel_text(crop_name)
    growth_stage = weather_intel_text(growth_stage)

    if not crop_name:

        return {
            "success": False,
            "error": "Please enter the crop name."
        }

    if not growth_stage:

        return {
            "success": False,
            "error": "Please select the crop growth stage."
        }

    weather = fetch_weather_intelligence_weather(
        farm
    )

    if not weather["success"]:

        return {
            "success": False,
            "error": weather["error"]
        }

    current = weather["current"]
    forecast = weather["forecast"]

    temperature = current["temperature"]
    humidity = current["humidity"]
    current_rain = current["precipitation"]
    current_wind = current["wind"]
    cloud_cover = current["cloud_cover"]

    rain_24h = forecast["rain_24h"]
    rain_probability = forecast["rain_probability"]
    max_temperature = forecast["max_temperature"]
    min_humidity = forecast["min_humidity"]
    max_wind = forecast["max_wind"]

    # ========================================================
    # RAIN RISK
    # ========================================================

    if (
        rain_24h >= 20
        or (
            rain_24h >= 10
            and rain_probability >= 70
        )
    ):

        rain_risk = "High"
        rain_class = "high"
        rain_reason = (
            "Substantial rainfall is expected in the next 24 hours."
        )

    elif (
        rain_24h >= 5
        or rain_probability >= 60
    ):

        rain_risk = "Medium"
        rain_class = "medium"
        rain_reason = (
            "Rainfall is possible and may affect field operations."
        )

    else:

        rain_risk = "Low"
        rain_class = "low"
        rain_reason = (
            "No strong rainfall signal is present for the next 24 hours."
        )

    # ========================================================
    # HEAT RISK
    # ========================================================

    if (
        max_temperature is not None
        and max_temperature >= 38
    ):

        heat_risk = "High"
        heat_class = "high"
        heat_reason = (
            "Forecast heat may increase crop stress and water loss."
        )

    elif (
        (
            max_temperature is not None
            and max_temperature >= 35
        )
        or (
            temperature is not None
            and temperature >= 32
        )
    ):

        heat_risk = "Medium"
        heat_class = "medium"
        heat_reason = (
            "Warm conditions may increase crop water demand."
        )

    else:

        heat_risk = "Low"
        heat_class = "low"
        heat_reason = (
            "No strong heat signal is present."
        )

    # ========================================================
    # WIND RISK
    # ========================================================

    if (
        max_wind is not None
        and max_wind >= 45
    ):

        wind_risk = "High"
        wind_class = "high"
        wind_reason = (
            "Strong winds may increase moisture loss and affect plants."
        )

    elif (
        (
            max_wind is not None
            and max_wind >= 30
        )
        or (
            current_wind is not None
            and current_wind >= 25
        )
    ):

        wind_risk = "Medium"
        wind_class = "medium"
        wind_reason = (
            "Wind may increase moisture loss and interfere with some farm work."
        )

    else:

        wind_risk = "Low"
        wind_class = "low"
        wind_reason = (
            "No strong wind signal is present."
        )

    # ========================================================
    # HUMIDITY / DISEASE-FRIENDLY CONDITIONS
    # ========================================================

    if (
        min_humidity is not None
        and min_humidity >= 80
        and rain_24h >= 5
    ):

        humidity_risk = "High"
        humidity_class = "high"
        humidity_reason = (
            "High humidity combined with rainfall can create conditions "
            "favourable to some fungal or moisture-related problems."
        )

    elif (
        (
            humidity is not None
            and humidity >= 75
        )
        or (
            min_humidity is not None
            and min_humidity >= 70
        )
    ):

        humidity_risk = "Medium"
        humidity_class = "medium"
        humidity_reason = (
            "Higher humidity means disease-prone conditions should be monitored."
        )

    else:

        humidity_risk = "Low"
        humidity_class = "low"
        humidity_reason = (
            "No strong humidity-related risk signal is present."
        )

    # ========================================================
    # OVERALL IMPACT
    # ========================================================

    risk_values = [
        rain_risk,
        heat_risk,
        wind_risk,
        humidity_risk
    ]

    high_count = risk_values.count("High")
    medium_count = risk_values.count("Medium")

    if high_count >= 2:

        overall = "High"
        overall_class = "high"
        overall_icon = "🔴"

    elif (
        high_count == 1
        or medium_count >= 2
    ):

        overall = "Moderate"
        overall_class = "medium"
        overall_icon = "🟡"

    else:

        overall = "Low"
        overall_class = "low"
        overall_icon = "🟢"

    # ========================================================
    # CROP IMPACT
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

    crop_impact = []

    if heat_risk in ("High", "Medium"):

        crop_impact.append(
            f"Warm conditions may increase water demand for {crop_name}."
        )

    if rain_risk in ("High", "Medium"):

        crop_impact.append(
            "Rainfall may affect irrigation timing and field operations."
        )

    if wind_risk in ("High", "Medium"):

        crop_impact.append(
            "Wind may increase moisture loss and create plant stress."
        )

    if humidity_risk in ("High", "Medium"):

        crop_impact.append(
            "Humid conditions mean the crop should be monitored for disease symptoms."
        )

    if sensitive_stage:

        crop_impact.append(
            f"Because {growth_stage} is a moisture-sensitive stage, "
            "weather changes should be monitored closely."
        )

    if not crop_impact:

        crop_impact.append(
            f"Current weather conditions show no strong immediate weather stress signal for {crop_name}."
        )

    # ========================================================
    # FARMER ACTION
    # ========================================================

    actions = []

    if rain_risk == "High":

        actions.append(
            "Monitor rainfall before scheduling field operations or irrigation."
        )

    elif rain_risk == "Medium":

        actions.append(
            "Check the short-term rain forecast before irrigation and field work."
        )

    if heat_risk == "High":

        actions.append(
            "Check crop moisture and stress more frequently during hot conditions."
        )

    elif heat_risk == "Medium":

        actions.append(
            "Monitor root-zone moisture because warm weather may increase water demand."
        )

    if wind_risk == "High":

        actions.append(
            "Avoid unnecessary exposed field work during strong winds and inspect the crop afterward."
        )

    if humidity_risk in ("High", "Medium"):

        actions.append(
            "Inspect leaves and crop canopy for disease symptoms, especially after wet conditions."
        )

    if not actions:

        actions.append(
            "Continue normal crop monitoring and follow the farm-specific irrigation plan."
        )

    # ========================================================
    # WEATHER SUMMARY
    # ========================================================

    weather_summary_parts = []

    if temperature is not None:
        weather_summary_parts.append(
            f"Current temperature {temperature:.1f}°C"
        )

    if humidity is not None:
        weather_summary_parts.append(
            f"humidity {humidity:.0f}%"
        )

    if current_wind is not None:
        weather_summary_parts.append(
            f"wind {current_wind:.0f} km/h"
        )

    if current_rain is not None:
        weather_summary_parts.append(
            f"current precipitation {current_rain:.1f} mm"
        )

    weather_summary = (
        ", ".join(weather_summary_parts)
        if weather_summary_parts
        else "Current weather data is incomplete."
    )

    # ========================================================
    # REASSESSMENT
    # ========================================================

    reassess = (
        "Check again with the next weather update and after any major rainfall or heat change."
    )

    # ========================================================
    # WARNING
    # ========================================================

    warning = (
        "This is weather-based decision support, not a crop-specific guarantee. "
        "Actual field conditions, local microclimate and crop response may differ."
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "success": True,

        "crop": crop_name,

        "growth_stage": growth_stage,

        "overall": overall,

        "overall_class": overall_class,

        "overall_icon": overall_icon,

        "weather_summary": weather_summary,

        "rain": {
            "risk": rain_risk,
            "class": rain_class,
            "reason": rain_reason
        },

        "heat": {
            "risk": heat_risk,
            "class": heat_class,
            "reason": heat_reason
        },

        "wind": {
            "risk": wind_risk,
            "class": wind_class,
            "reason": wind_reason
        },

        "humidity": {
            "risk": humidity_risk,
            "class": humidity_class,
            "reason": humidity_reason
        },

        "crop_impact": crop_impact,

        "actions": actions,

        "reassess": reassess,

        "warning": warning,

        "weather": weather
    }


@app.route(
    "/ai/weather-intelligence",
    methods=["GET", "POST"]
)
def weather_intelligence():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using Weather Intelligence.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    result = None

    form_data = {

        "crop_name": "",

        "growth_stage": ""
    }

    if request.method == "POST":

        form_data = {

            "crop_name": request.form.get(
                "crop_name",
                ""
            ).strip(),

            "growth_stage": request.form.get(
                "growth_stage",
                ""
            ).strip()
        }

        result = analyze_weather_intelligence(

            farm=active_farm,

            crop_name=form_data["crop_name"],

            growth_stage=form_data["growth_stage"]
        )

    return render_template(

        "ai-tools/weather-intelligence.html",

        active_farm=active_farm,

        result=result,

        form_data=form_data
    )


# =========================================================
# AI FARM RISK & YIELD ANALYSIS
# =========================================================


def farm_risk_text(value):

    if value is None:
        return ""

    return str(value).strip()


def farm_risk_number(value):

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def farm_risk_level_meta(level):

    level = farm_risk_text(level).lower()

    if level == "high":
        return {
            "label": "High",
            "class": "high",
            "icon": "🔴"
        }

    if level == "medium":
        return {
            "label": "Moderate",
            "class": "medium",
            "icon": "🟡"
        }

    if level == "low":
        return {
            "label": "Low",
            "class": "low",
            "icon": "🟢"
        }

    return {
        "label": "Not Assessed",
        "class": "unknown",
        "icon": "⚪"
    }


def farm_risk_from_weather(weather_result):

    if not isinstance(weather_result, dict):
        return "unknown", "Weather Intelligence did not return a result."

    if not weather_result.get("success"):
        return "unknown", weather_result.get(
            "error",
            "Weather information is unavailable."
        )

    overall = farm_risk_text(
        weather_result.get("overall")
    ).lower()

    if overall == "high":
        return "high", "Weather Intelligence detected a high overall weather impact."

    if overall in ("moderate", "medium"):
        return "medium", "Weather Intelligence detected moderate weather-related risk."

    if overall == "low":
        return "low", "No strong immediate weather risk was detected."

    return "unknown", "Weather risk could not be classified."


def farm_risk_from_irrigation(irrigation_result):

    if not isinstance(irrigation_result, dict):
        return "unknown", "Irrigation analysis did not return a result."

    if not irrigation_result.get("success"):
        return "unknown", irrigation_result.get(
            "error",
            "Irrigation information is unavailable."
        )

    status = farm_risk_text(
        irrigation_result.get("status")
    ).lower()

    mapping = {
        "needed": (
            "high",
            "The irrigation planner indicates that the crop may need water."
        ),
        "monitor": (
            "medium",
            "The irrigation planner recommends close moisture monitoring."
        ),
        "delay": (
            "low",
            "The irrigation planner indicates irrigation can be delayed for now."
        ),
        "field_check": (
            "unknown",
            "A field inspection is required before making a confident water-risk decision."
        )
    }

    return mapping.get(
        status,
        (
            "unknown",
            "Irrigation risk could not be classified."
        )
    )


def farm_risk_from_disease(disease_data):

    if not isinstance(disease_data, dict):
        return "unknown", "Disease Detection has not been assessed for this farm."

    disease = farm_risk_text(
        disease_data.get("disease")
    )
    severity = farm_risk_text(
        disease_data.get("severity")
    ).lower()
    confidence = farm_risk_number(
        disease_data.get("confidence")
    )

    disease_lower = disease.lower()

    if any(
        phrase in disease_lower
        for phrase in (
            "no disease",
            "healthy",
            "none detected",
            "no significant disease"
        )
    ):
        return "low", "The latest disease analysis did not flag a disease."

    if confidence is not None and confidence < 50:
        return "unknown", "The latest disease result has low confidence and should be verified in the field."

    if severity in ("critical", "severe", "high"):
        return "high", "The latest disease analysis indicates high disease severity."

    if severity in ("moderate", "medium"):
        return "medium", "The latest disease analysis indicates moderate disease severity."

    if severity in ("mild", "low"):
        return "low", "The latest disease analysis indicates mild disease severity."

    return "unknown", "Disease information is available, but severity is not clear enough to classify the risk."


def farm_risk_from_health(health_data):

    if not isinstance(health_data, dict):
        return "unknown", "Crop Health Analysis has not been assessed for this farm."

    status = farm_risk_text(
        health_data.get("health_status")
    ).lower()

    score = farm_risk_number(
        health_data.get("health_score")
    )

    if "critical" in status:
        return "high", "The latest Crop Health Analysis reports critical visible crop stress."

    if "moderate" in status:
        return "medium", "The latest Crop Health Analysis reports moderate visible crop stress."

    if "mild" in status:
        return "medium", "The latest Crop Health Analysis reports mild visible crop stress."

    if "healthy" in status:
        return "low", "The latest Crop Health Analysis reports healthy visible crop condition."

    if score is not None:
        if score < 40:
            return "high", "The latest crop-health score indicates substantial visible stress."
        if score < 70:
            return "medium", "The latest crop-health score indicates some visible stress."
        return "low", "The latest crop-health score does not indicate strong visible stress."

    return "unknown", "Crop health could not be classified from the available result."


def farm_risk_from_soil(soil_result, saved_soil):

    if not isinstance(saved_soil, dict):
        return "unknown", "No saved soil report is available for this farm."

    if not isinstance(soil_result, dict) or not soil_result.get("success"):
        return "unknown", "The saved soil report could not be re-analysed."

    score = farm_risk_number(
        soil_result.get("score")
    )

    if score is None:
        return "unknown", "Soil risk could not be classified from the available report."

    if score >= 80:
        return "low", "The soil report score is in the good range."

    if score >= 50:
        return "medium", "The soil report shows some soil parameters that need attention."

    return "high", "The soil report shows important soil-management concerns."


def farm_risk_overall(levels):
    """
    Explainable overall rule:
    - 2 or more high risks -> High
    - 1 high + at least 1 moderate -> High
    - 1 high -> Moderate
    - 2 or more moderate -> Moderate
    - otherwise -> Low

    Unknown categories do not increase the risk score.
    """

    known = [
        level
        for level in levels
        if level in ("high", "medium", "low")
    ]

    if not known:
        return "unknown"

    high_count = known.count("high")
    medium_count = known.count("medium")

    if high_count >= 2:
        return "high"

    if high_count == 1 and medium_count >= 1:
        return "high"

    if high_count == 1:
        return "medium"

    if medium_count >= 2:
        return "medium"

    return "low"


def analyze_farm_risk(
    farm,
    farmer_id,
    crop_name,
    growth_stage
):

    crop_name = farm_risk_text(crop_name)
    growth_stage = farm_risk_text(growth_stage)

    if not crop_name:
        return {
            "success": False,
            "error": "Please enter the current crop name."
        }

    if not growth_stage:
        return {
            "success": False,
            "error": "Please select the current crop growth stage."
        }

    # ---------------------------------------------------------
    # LOAD EXISTING FARM-SPECIFIC RESULTS
    # ---------------------------------------------------------

    saved_soil = get_latest_soil_report(farm)

    disease_data = get_latest_feature_analysis(
        farmer_id,
        "disease_detection",
        farm
    )

    health_data = get_latest_feature_analysis(
        farmer_id,
        "crop_health",
        farm
    )

    # ---------------------------------------------------------
    # REUSE EXISTING SOIL ANALYZER
    # ---------------------------------------------------------

    soil_result = None

    if isinstance(saved_soil, dict):

        soil_values = saved_soil.get("values") or {}

        soil_form_data = {
            "ph": soil_values.get("ph", ""),
            "nitrogen": soil_values.get("nitrogen", ""),
            "phosphorus": soil_values.get("phosphorus", ""),
            "potassium": soil_values.get("potassium", ""),
            "organic_carbon": soil_values.get("organic_carbon", ""),
            "electrical_conductivity": soil_values.get(
                "electrical_conductivity", ""
            ),
            "soil_type": farm.get("soil_type", ""),
            "season": farm.get("season", ""),
            "crop": crop_name
        }

        try:
            soil_result = run_soil_analysis(
                soil_form_data,
                farm
            )
        except Exception as error:
            print("Farm risk soil analysis error:", error)
            soil_result = None

    # ---------------------------------------------------------
    # WEATHER INTELLIGENCE
    # ---------------------------------------------------------

    try:
        weather_result = analyze_weather_intelligence(
            farm,
            crop_name,
            growth_stage
        )
    except Exception as error:
        print("Farm risk weather analysis error:", error)
        weather_result = {
            "success": False,
            "error": str(error)
        }

    # ---------------------------------------------------------
    # IRRIGATION PLANNER
    # ---------------------------------------------------------

    try:
        irrigation_result = analyze_irrigation(
            farm=farm,
            crop_name=crop_name,
            growth_stage=growth_stage,
            soil_moisture="unknown",
            field_observation=""
        )
    except Exception as error:
        print("Farm risk irrigation analysis error:", error)
        irrigation_result = {
            "success": False,
            "error": str(error)
        }

    # ---------------------------------------------------------
    # CONVERT EACH SOURCE INTO A RISK CATEGORY
    # ---------------------------------------------------------

    weather_level, weather_reason = farm_risk_from_weather(
        weather_result
    )

    water_level, water_reason = farm_risk_from_irrigation(
        irrigation_result
    )

    disease_level, disease_reason = farm_risk_from_disease(
        disease_data
    )

    health_level, health_reason = farm_risk_from_health(
        health_data
    )

    soil_level, soil_reason = farm_risk_from_soil(
        soil_result,
        saved_soil
    )

    risk_sources = {

        "weather": {
            "title": "Weather Risk",
            "icon": "🌦️",
            "level": weather_level,
            "reason": weather_reason
        },

        "water": {
            "title": "Water Risk",
            "icon": "💧",
            "level": water_level,
            "reason": water_reason
        },

        "disease": {
            "title": "Disease Risk",
            "icon": "🦠",
            "level": disease_level,
            "reason": disease_reason
        },

        "health": {
            "title": "Crop Health Risk",
            "icon": "🌱",
            "level": health_level,
            "reason": health_reason
        },

        "soil": {
            "title": "Soil / Nutrient Risk",
            "icon": "🧪",
            "level": soil_level,
            "reason": soil_reason
        }
    }

    for item in risk_sources.values():
        meta = farm_risk_level_meta(item["level"])
        item.update(meta)

    overall_level = farm_risk_overall([
        item["level"]
        for item in risk_sources.values()
    ])

    overall_meta = farm_risk_level_meta(
        overall_level
    )

    # ---------------------------------------------------------
    # MAIN RISK FACTORS
    # ---------------------------------------------------------

    risk_priority = {
        "high": 0,
        "medium": 1,
        "low": 2,
        "unknown": 3
    }

    ranked_factors = sorted(
        [
            item for item in risk_sources.values()
            if item["level"] in ("high", "medium")
        ],
        key=lambda item: risk_priority.get(
            item["level"],
            9
        )
    )

    main_risk_factors = [
        item["reason"]
        for item in ranked_factors[:3]
    ]

    if not main_risk_factors:
        main_risk_factors = [
            "No major assessed risk factor is currently flagged. Continue regular field monitoring."
        ]

    # ---------------------------------------------------------
    # YIELD OUTLOOK
    # ---------------------------------------------------------
    # No numeric yield estimate is generated here because the
    # current project source contains no calibrated farm/crop
    # yield model or populated historical yield table.
    # ---------------------------------------------------------

    if overall_level == "high":
        yield_outlook = "High risk to yield"
        yield_class = "high"
    elif overall_level == "medium":
        yield_outlook = "Moderate yield risk"
        yield_class = "medium"
    elif overall_level == "low":
        yield_outlook = "Favorable yield outlook"
        yield_class = "low"
    else:
        yield_outlook = "Yield outlook cannot be assessed"
        yield_class = "unknown"

    yield_message = (
        "A numeric yield estimate requires a calibrated crop/yield dataset "
        "or reliable historical yield records for this farm and crop. "
        "This version intentionally does not invent a yield number."
    )

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------

    actions = []

    for item in ranked_factors:
        if item["level"] == "high":
            actions.append(
                item["reason"]
                + " Review the related Smart Kisan analysis before taking action."
            )

    if weather_level == "medium":
        actions.append(
            "Monitor the weather forecast before irrigation and sensitive field operations."
        )

    if water_level == "medium":
        actions.append(
            "Check root-zone moisture and reassess irrigation soon."
        )

    if disease_level == "unknown":
        actions.append(
            "Inspect the crop for visible disease symptoms because disease assessment is incomplete."
        )

    if health_level == "unknown":
        actions.append(
            "Run Crop Health Analysis on a clear crop image for better crop-condition assessment."
        )

    if soil_level == "unknown":
        actions.append(
            "Run Soil Report Analyzer to improve soil-risk assessment."
        )

    if not actions:
        actions.append(
            "Continue regular crop, soil, weather and irrigation monitoring."
        )

    warning = (
        "This is decision-support analysis, not a guaranteed risk or yield forecast. "
        "Actual field conditions, local microclimate, management and crop response can differ."
    )

    data_available = sum(
        1 for item in risk_sources.values()
        if item["level"] != "unknown"
    )

    return {

        "success": True,

        "farm_name": farm.get("farm_name", ""),

        "crop": crop_name,

        "growth_stage": growth_stage,

        "farm_area": farm.get("area", ""),

        "farm_area_unit": farm.get("area_unit", ""),

        "overall": overall_meta["label"],

        "overall_class": overall_meta["class"],

        "overall_icon": overall_meta["icon"],

        "risk_summary": (
            "Overall farm risk is "
            + overall_meta["label"].lower()
            + " based on the currently available farm analyses."
        ),

        "risks": risk_sources,

        "main_risk_factors": main_risk_factors,

        "yield_outlook": yield_outlook,

        "yield_class": yield_class,

        "yield_estimate": None,

        "yield_message": yield_message,

        "actions": actions,

        "warning": warning,

        "data_available": data_available,

        "data_total": len(risk_sources),

        "weather_analysis": weather_result,

        "irrigation_analysis": irrigation_result,

        "soil_analysis": soil_result,

        "disease_analysis": disease_data,

        "crop_health_analysis": health_data
    }


@app.route(
    "/ai/farm-risk",
    methods=["GET", "POST"]
)
def farm_risk():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using Farm Risk & Yield Analysis.",
            "error"
        )

        return redirect(
            url_for(
                "farm_details",
                new="1"
            )
        )

    latest_health = get_latest_feature_analysis(
        farmer_id,
        "crop_health",
        active_farm
    )

    latest_disease = get_latest_feature_analysis(
        farmer_id,
        "disease_detection",
        active_farm
    )

    form_data = {

        "crop_name": (
            farm_risk_text(
                latest_health.get("crop")
            )
            if isinstance(latest_health, dict)
            else ""
        )
        or (
            farm_risk_text(
                latest_disease.get("crop")
            )
            if isinstance(latest_disease, dict)
            else ""
        ),

        "growth_stage": (
            farm_risk_text(
                latest_health.get("growth_stage")
            )
            if isinstance(latest_health, dict)
            else ""
        )
    }

    result = None

    if request.method == "POST":

        form_data = {

            "crop_name": request.form.get(
                "crop_name",
                ""
            ).strip(),

            "growth_stage": request.form.get(
                "growth_stage",
                ""
            ).strip()
        }

        try:

            result = analyze_farm_risk(
                farm=active_farm,
                farmer_id=farmer_id,
                crop_name=form_data["crop_name"],
                growth_stage=form_data["growth_stage"]
            )

        except Exception as error:

            print("Farm risk analysis error:", error)

            result = {

                "success": False,

                "error":
                    "Farm risk analysis failed: "
                    + str(error)
            }

        # -----------------------------------------------------
        # SAVE SUCCESSFUL FARM RISK ANALYSIS TO AI HISTORY
        # -----------------------------------------------------

        if (
            isinstance(result, dict)
            and result.get("success")
        ):

            try:

                history_data = {

                    "_farm_id": active_farm.get(
                        "farm_id"
                    ),

                    "crop": result.get(
                        "crop",
                        ""
                    ),

                    "growth_stage": result.get(
                        "growth_stage",
                        ""
                    ),

                    "overall": result.get(
                        "overall",
                        ""
                    ),

                    "risks": result.get(
                        "risks",
                        {}
                    ),

                    "main_risk_factors": result.get(
                        "main_risk_factors",
                        []
                    ),

                    "yield_outlook": result.get(
                        "yield_outlook",
                        ""
                    ),

                    "yield_estimate": result.get(
                        "yield_estimate"
                    ),

                    "actions": result.get(
                        "actions",
                        []
                    ),

                    "warning": result.get(
                        "warning",
                        ""
                    )
                }

                add_ai_history(
                    farmer_id,
                    "farm_risk",
                    "Farm risk and yield analysis for "
                    + form_data["crop_name"],
                    json.dumps(
                        history_data,
                        ensure_ascii=False
                    )
                )

                print(
                    "AI History: Farm risk analysis saved."
                )

            except Exception as error:

                print(
                    "AI History farm risk save error:",
                    error
                )

    return render_template(

        "ai-tools/farm-risk.html",

        active_farm=active_farm,

        result=result,

        form_data=form_data
    )


# =========================================================
# AI FARMING ASSISTANT
# EXPLAINABLE FARM CONTEXT ASSISTANT
# =========================================================


def farming_assistant_text(value):

    if value is None:
        return ""

    return str(value).strip()


def farming_assistant_list(value):

    if isinstance(value, list):
        return [
            farming_assistant_text(item)
            for item in value
            if farming_assistant_text(item)
        ]

    if value in (None, ""):
        return []

    return [farming_assistant_text(value)]


def farming_assistant_first_analysis(
    farmer_id,
    active_farm,
    feature
):

    data = get_latest_feature_analysis(
        farmer_id,
        feature,
        active_farm
    )

    return data if isinstance(data, dict) else None


def farming_assistant_soil(
    active_farm,
    crop_name=""
):

    saved_soil = get_latest_soil_report(
        active_farm
    )

    if not isinstance(saved_soil, dict):
        return None

    values = saved_soil.get("values") or {}

    try:
        soil_result = run_soil_analysis(
            {
                "ph": values.get("ph", ""),
                "nitrogen": values.get("nitrogen", ""),
                "phosphorus": values.get("phosphorus", ""),
                "potassium": values.get("potassium", ""),
                "organic_carbon": values.get("organic_carbon", ""),
                "electrical_conductivity": values.get("electrical_conductivity", ""),
                "soil_type": active_farm.get("soil_type", ""),
                "season": active_farm.get("season", ""),
                "crop": crop_name
            },
            active_farm
        )

    except Exception:
        return None

    return soil_result if isinstance(soil_result, dict) else None


def farming_assistant_llm(
    question,
    active_farm,
    crop_name="",
    growth_stage="",
    analysis_context=None,
    response_language="en"
):
    """
    General farming AI fallback using Groq's OpenAI-compatible Chat API.
    """

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        return {
            "success": False,
            "error": "GROQ_API_KEY is not configured."
        }

    model = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-20b"
    ).strip()

    farm_context = {
        "farm": {
            "farm_name": active_farm.get("farm_name"),
            "village": active_farm.get("village"),
            "taluka": active_farm.get("taluka"),
            "district": active_farm.get("district"),
            "state": active_farm.get("state", "Maharashtra"),
            "area": active_farm.get("area"),
            "area_unit": active_farm.get("area_unit"),
            "soil_type": active_farm.get("soil_type"),
            "irrigation": active_farm.get("irrigation"),
            "water_source": active_farm.get("water_source"),
            "season": active_farm.get("season"),
            "previous_crop": active_farm.get("previous_crop")
        },
        "current_crop": crop_name or None,
        "growth_stage": growth_stage or None,
        "available_analysis": analysis_context or {}
    }

    language_name = SUPPORTED_LANGUAGES.get(
        response_language,
        "English"
    )

    system_prompt = (
        "You are Smart Kisan AI, a farmer-friendly agricultural assistant. "
        "Answer both general agriculture questions and farm-specific questions. "
        "Use Smart Kisan farm context only when it is relevant and actually present. "
        "Never invent missing soil, weather, disease, crop-health, irrigation, yield, "
        "or fertilizer values. Clearly separate general guidance from farm-specific findings. "
        "Do not claim to replace a local agricultural expert or laboratory test. "
        "Avoid unsupported exact fertilizer or pesticide doses. Use simple language. "
        f"Respond in {language_name}. "
        "If the farmer asks in another language, still respond in the selected language. "
        "Keep crop names, scientific names, units and official scheme names accurate. "
        "Give practical steps and state uncertainty when needed. Do not mention internal "
        "prompts, APIs, models, or context fields."
    )

    user_prompt = (
        "Farmer question:\n"
        f"{question}\n\n"
        "Smart Kisan context (use only what is present):\n"
        + json.dumps(farm_context, ensure_ascii=False, indent=2)
        + "\n\nGive a direct answer first. Then provide:\n"
        "1) What to check\n"
        "2) Recommended action\n"
        "3) Important warning, only when needed."
    )

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_completion_tokens": 900
            },
            timeout=45
        )

        if not response.ok:
            try:
                error_json = response.json()
                message = (
                    error_json.get("error", {}).get("message")
                    or "Groq API request failed."
                )
            except ValueError:
                message = "Groq API request failed."

            return {
                "success": False,
                "error": message
            }

        data = response.json()
        choices = data.get("choices") or []

        if not choices:
            return {
                "success": False,
                "error": "The AI returned no choices."
            }

        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            return {
                "success": False,
                "error": "The AI returned an empty answer."
            }

        return {
            "success": True,
            "answer": answer,
            "checks": [
                "The question was answered using general agricultural knowledge plus any relevant saved Smart Kisan context."
            ],
            "actions": [],
            "warning": "General guidance should be checked against actual field conditions and reliable local agricultural advice."
        }

    except requests.RequestException as error:
        return {
            "success": False,
            "error": f"Unable to reach the AI service: {error}"
        }
    except (ValueError, KeyError, TypeError, IndexError) as error:
        return {
            "success": False,
            "error": f"Invalid AI response: {error}"
        }


def farming_assistant_answer(
    question,
    active_farm,
    farmer_id,
    crop_name="",
    growth_stage=""
):
    """
    Answer common farming questions using available farm-specific
    Smart Kisan analysis results. No values are invented when data
    is unavailable.
    """

    question = farming_assistant_text(question)
    crop_name = farming_assistant_text(crop_name)
    growth_stage = farming_assistant_text(growth_stage)

    if not question:
        return {
            "success": False,
            "error": "Please enter your farming question."
        }

    latest_health = farming_assistant_first_analysis(
        farmer_id, active_farm, "crop_health"
    )

    latest_disease = farming_assistant_first_analysis(
        farmer_id, active_farm, "disease_detection"
    )

    detected_crop = crop_name or farming_assistant_text(
        (latest_health or {}).get("crop")
    ) or farming_assistant_text(
        (latest_disease or {}).get("crop")
    )

    detected_stage = growth_stage or farming_assistant_text(
        (latest_health or {}).get("growth_stage")
    )

    q = question.lower()

    intent = "general"

    if any(word in q for word in (
        "irrigation", "water", "watering", "paani", "sinchai"
    )):
        intent = "irrigation"

    elif any(word in q for word in (
        "disease", "infection", "leaf spot", "fungus", "pest", "कीड", "रोग"
    )):
        intent = "disease"

    elif any(word in q for word in (
        "health", "healthy", "yellow", "stress", "growth", "पीक"
    )):
        intent = "health"

    elif any(word in q for word in (
        "soil", "ph", "nitrogen", "phosphorus", "potassium", "fertilizer", "खत", "माती"
    )):
        intent = "soil"

    elif any(word in q for word in (
        "weather", "rain", "temperature", "humidity", "wind", "पाऊस", "हवामान"
    )):
        intent = "weather"

    elif any(word in q for word in (
        "risk", "yield", "production", "नुकसान", "उत्पादन"
    )):
        intent = "risk"

    # ---------------------------------------------------------
    # IRRIGATION
    # ---------------------------------------------------------
    if intent == "irrigation":

        if not detected_crop or not detected_stage:
            return {
                "success": True,
                "intent": intent,
                "answer": (
                    "For an irrigation decision, I need the current crop and growth stage. "
                    "Enter them above, then ask again. Also check actual root-zone soil moisture before irrigating."
                ),
                "checks": [
                    "Actual soil moisture",
                    "Rain forecast",
                    "Current crop stage"
                ],
                "warning": "Do not irrigate only because a fixed schedule says it is time."
            }

        try:
            irrigation = analyze_irrigation(
                active_farm,
                detected_crop,
                detected_stage
            )
        except Exception as error:
            irrigation = {
                "success": False,
                "error": str(error)
            }

        if not irrigation.get("success"):
            return {
                "success": True,
                "intent": intent,
                "answer": (
                    "I could not make an automatic irrigation assessment right now. "
                    "Check root-zone moisture and the latest forecast before irrigating."
                ),
                "checks": ["Field moisture", "Latest forecast"],
                "warning": irrigation.get("error", "Weather data is unavailable.")
            }

        status = farming_assistant_text(
            irrigation.get("status_label") or irrigation.get("status")
        )

        reasons = farming_assistant_list(
            irrigation.get("reasons")
        )

        actions = farming_assistant_list(
            irrigation.get("actions")
        )

        answer = (
            f"For {detected_crop} at the {detected_stage} stage, the irrigation planner says: {status}."
        )

        return {
            "success": True,
            "intent": intent,
            "answer": answer,
            "checks": reasons or ["Check actual root-zone soil moisture."],
            "actions": actions,
            "warning": farming_assistant_text(
                irrigation.get("warning")
            ) or "Field conditions should be checked before irrigation."
        }

    # ---------------------------------------------------------
    # WEATHER
    # ---------------------------------------------------------
    if intent == "weather":

        if not detected_crop:
            detected_crop = "the current crop"

        stage_for_weather = detected_stage or "current stage"

        try:
            weather = analyze_weather_intelligence(
                active_farm,
                detected_crop,
                stage_for_weather
            )
        except Exception as error:
            weather = {
                "success": False,
                "error": str(error)
            }

        if not weather.get("success"):
            return {
                "success": True,
                "intent": intent,
                "answer": "Weather data could not be retrieved right now. Use the Live Weather page to check the latest farm forecast.",
                "checks": [],
                "warning": weather.get("error", "Weather service unavailable.")
            }

        return {
            "success": True,
            "intent": intent,
            "answer": (
                f"For {detected_crop}, current weather impact is {weather.get('overall', 'not assessed')}. "
                f"{weather.get('weather_summary', '')}"
            ),
            "checks": [
                farming_assistant_text(weather.get("rain", {}).get("reason")),
                farming_assistant_text(weather.get("heat", {}).get("reason")),
                farming_assistant_text(weather.get("wind", {}).get("reason")),
                farming_assistant_text(weather.get("humidity", {}).get("reason"))
            ],
            "actions": farming_assistant_list(weather.get("actions")),
            "warning": farming_assistant_text(weather.get("warning"))
        }

    # ---------------------------------------------------------
    # DISEASE
    # ---------------------------------------------------------
    if intent == "disease":

        if not latest_disease:
            return {
                "success": True,
                "intent": intent,
                "answer": "No recent Disease Detection result is available for this farm. Upload a clear plant or leaf image in Disease Detection before relying on a disease-specific answer.",
                "checks": ["Clear leaf/plant image", "Visible symptoms"],
                "warning": "An assistant cannot confirm a disease without a suitable image or field assessment."
            }

        disease = farming_assistant_text(latest_disease.get("disease")) or "Not clear"
        severity = farming_assistant_text(latest_disease.get("severity")) or "Unknown"
        confidence = latest_disease.get("confidence")

        return {
            "success": True,
            "intent": intent,
            "answer": (
                f"The latest disease analysis reports {disease} with {severity} severity"
                + (f" and {confidence}% confidence." if confidence not in (None, "") else ".")
            ),
            "checks": farming_assistant_list(latest_disease.get("symptoms")) or ["Inspect the affected leaves and nearby plants."],
            "actions": farming_assistant_list(latest_disease.get("recommendations")),
            "warning": farming_assistant_text(latest_disease.get("warning")) or "Do not treat a crop solely from an uncertain image-based diagnosis."
        }

    # ---------------------------------------------------------
    # HEALTH
    # ---------------------------------------------------------
    if intent == "health":

        if not latest_health:
            return {
                "success": True,
                "intent": intent,
                "answer": "No recent Crop Health Analysis is available for this farm. Upload a clear crop image to assess visible crop condition.",
                "checks": ["Leaf colour", "Visible stress", "Growth condition"],
                "warning": "Image-based health analysis is a screening tool and should be checked against field conditions."
            }

        status = farming_assistant_text(latest_health.get("health_status")) or "Not clear"
        score = latest_health.get("health_score")

        return {
            "success": True,
            "intent": intent,
            "answer": (
                f"The latest Crop Health Analysis reports {status}"
                + (f" with a health score of {score}." if score not in (None, "") else ".")
            ),
            "checks": farming_assistant_list(latest_health.get("visible_stress")),
            "actions": farming_assistant_list(latest_health.get("recommendations")),
            "warning": farming_assistant_text(latest_health.get("warning")) or "Check the whole plant and field conditions, not only one image."
        }

    # ---------------------------------------------------------
    # SOIL / FERTILIZER
    # ---------------------------------------------------------
    if intent == "soil":

        soil_result = farming_assistant_soil(
            active_farm,
            detected_crop
        )

        if not soil_result:
            return {
                "success": True,
                "intent": intent,
                "answer": "No recent soil report is available for this farm. Run Soil Report Analyzer first so I can answer using your actual soil values.",
                "checks": ["pH", "N", "P", "K", "Organic Carbon"],
                "warning": "Do not apply fertilizer based only on a generic recommendation."
            }

        return {
            "success": True,
            "intent": intent,
            "answer": farming_assistant_text(soil_result.get("summary")) or "Your latest soil analysis is available.",
            "checks": [
                farming_assistant_text(item.get("message"))
                for item in (soil_result.get("analysis") or {}).values()
                if isinstance(item, dict) and farming_assistant_text(item.get("message"))
            ][:5],
            "actions": farming_assistant_list(soil_result.get("priorities")) + farming_assistant_list(soil_result.get("recommendations")),
            "warning": "Fertilizer choice and dose should follow the soil report, crop requirement and local agronomic guidance."
        }

    # ---------------------------------------------------------
    # FARM RISK / YIELD
    # ---------------------------------------------------------
    if intent == "risk":

        if not detected_crop or not detected_stage:
            return {
                "success": True,
                "intent": intent,
                "answer": "For farm-risk questions, enter the current crop and growth stage above so I can combine the available farm analyses.",
                "checks": ["Crop", "Growth stage"],
                "warning": "Yield is an estimate only and requires suitable historical data for a numeric forecast."
            }

        try:
            risk = analyze_farm_risk(
                active_farm,
                farmer_id,
                detected_crop,
                detected_stage
            )
        except Exception as error:
            risk = {
                "success": False,
                "error": str(error)
            }

        if not risk.get("success"):
            return {
                "success": True,
                "intent": intent,
                "answer": "Farm risk analysis could not be completed right now.",
                "checks": [],
                "warning": risk.get("error", "Unknown analysis error.")
            }

        return {
            "success": True,
            "intent": intent,
            "answer": (
                f"Current overall farm risk is {risk.get('overall', 'not assessed')}. "
                f"Yield outlook: {risk.get('yield_outlook', 'not assessed')}."
            ),
            "checks": [
                f"{item.get('title', key)}: {item.get('label', 'Not assessed')} — {item.get('reason', '')}"
                for key, item in (risk.get("risks") or {}).items()
                if isinstance(item, dict)
            ],
            "actions": farming_assistant_list(risk.get("actions")),
            "warning": farming_assistant_text(risk.get("warning"))
        }

    # ---------------------------------------------------------
    # GENERAL
    # ---------------------------------------------------------

    location = ", ".join(
        part for part in (
            active_farm.get("village"),
            active_farm.get("taluka"),
            active_farm.get("district")
        )
        if farming_assistant_text(part)
    )

    profile = []

    if detected_crop:
        profile.append(f"Current crop: {detected_crop}.")

    if detected_stage:
        profile.append(f"Growth stage: {detected_stage}.")

    if active_farm.get("soil_type"):
        profile.append(
            f"Soil type: {active_farm.get('soil_type')}."
        )

    if active_farm.get("irrigation"):
        profile.append(
            f"Irrigation: {active_farm.get('irrigation')}."
        )

    # ---------------------------------------------------------
    # GENERAL AI FALLBACK
    # ---------------------------------------------------------

    analysis_context = {}

    if latest_health:
        analysis_context["crop_health"] = {
            "health_status": latest_health.get("health_status"),
            "health_score": latest_health.get("health_score"),
            "visible_stress": latest_health.get("visible_stress"),
            "recommendations": latest_health.get("recommendations"),
            "warning": latest_health.get("warning")
        }

    if latest_disease:
        analysis_context["disease_detection"] = {
            "disease": latest_disease.get("disease"),
            "confidence": latest_disease.get("confidence"),
            "severity": latest_disease.get("severity"),
            "symptoms": latest_disease.get("symptoms"),
            "recommendations": latest_disease.get("recommendations"),
            "warning": latest_disease.get("warning")
        }

    llm_result = farming_assistant_llm(
        question=question,
        active_farm=active_farm,
        crop_name=detected_crop,
        growth_stage=detected_stage,
        analysis_context=analysis_context,
        response_language=session.get("farmer_language", "en")
    )

    if llm_result.get("success"):
        llm_result["intent"] = intent
        return llm_result

    return {
        "success": True,
        "intent": intent,
        "answer": (
            "I could not reach the general AI assistant right now. "
            "The saved Smart Kisan analyses are still available for farm-specific questions."
        ),
        "checks": [
            (f"Farm location: {location}" if location else "Saved farm profile"),
            "General AI service unavailable in this request."
        ],
        "actions": [
            "Try the question again after checking the AI service configuration."
        ],
        "warning": llm_result.get(
            "error",
            "General guidance should be checked against actual field conditions and reliable local agricultural advice."
        )
    }


@app.route(
    "/ai/farming-assistant",
    methods=["GET", "POST"]
)
def farming_assistant():

    farmer_id = require_login()

    if farmer_id is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    active_farm = get_active_farm(
        farmer_id
    )

    if active_farm is None:

        flash(
            "Please add a farm before using AI Farming Assistant.",
            "error"
        )

        return redirect(
            url_for("farm_details", new="1")
        )

    form_data = {
        "question": "",
        "crop_name": "",
        "growth_stage": ""
    }

    result = None

    if request.method == "POST":

        form_data = {
            "question": request.form.get("question", "").strip(),
            "crop_name": request.form.get("crop_name", "").strip(),
            "growth_stage": request.form.get("growth_stage", "").strip()
        }

        try:
            result = farming_assistant_answer(
                question=form_data["question"],
                active_farm=active_farm,
                farmer_id=farmer_id,
                crop_name=form_data["crop_name"],
                growth_stage=form_data["growth_stage"]
            )

        except Exception as error:
            print("Farming assistant error:", error)
            result = {
                "success": False,
                "error": "Farming Assistant failed: " + str(error)
            }

        if isinstance(result, dict) and result.get("success"):
            try:
                history_data = {
                    "_farm_id": active_farm.get("farm_id"),
                    "question": form_data["question"],
                    "crop": form_data["crop_name"],
                    "growth_stage": form_data["growth_stage"],
                    "answer": result.get("answer", ""),
                    "checks": result.get("checks", []),
                    "actions": result.get("actions", []),
                    "warning": result.get("warning", "")
                }

                add_ai_history(
                    farmer_id,
                    "farming_assistant",
                    form_data["question"],
                    json.dumps(history_data, ensure_ascii=False)
                )

            except Exception as error:
                print("AI History farming assistant save error:", error)

    return render_template(
        "ai-tools/farming-assistant.html",
        active_farm=active_farm,
        form_data=form_data,
        result=result
    )


# =========================================================
# SMART REMINDER
# =========================================================

def get_latest_farm_history_record(
    farmer_id,
    feature,
    active_farm
):
    """Return the newest farm-specific JSON history record."""

    try:
        history = get_ai_history(
            farmer_id,
            100
        )
    except Exception as error:
        print("Smart Reminder history error:", error)
        return None

    candidates = []

    for item in history or []:

        if hasattr(item, "keys"):
            try:
                item = dict(item)
            except Exception:
                pass

        if not isinstance(item, dict):
            continue

        if item.get("feature") != feature:
            continue

        answer = item.get("answer", "")

        if not answer:
            continue

        try:
            data = json.loads(answer)
        except (TypeError, ValueError):
            continue

        if not isinstance(data, dict):
            continue

        saved_farm_id = data.get("_farm_id")

        if saved_farm_id is None:
            continue

        if str(saved_farm_id) != str(
            active_farm.get("farm_id")
        ):
            continue

        data.pop("_farm_id", None)

        candidates.append({
            "created_at": item.get("created_at", ""),
            "data": data
        })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: str(item.get("created_at", "")),
        reverse=True
    )

    return candidates[0]["data"]


def smart_reminder_clean(value):
    return str(value or "").strip()


def smart_reminder_stage_from_calendar(calendar_result):
    """Find the current calendar stage using today's date."""

    if not isinstance(calendar_result, dict):
        return None

    timeline = calendar_result.get("timeline") or []
    today = date.today()

    for stage in timeline:
        if not isinstance(stage, dict):
            continue

        try:
            start = datetime.strptime(
                str(stage.get("start_date", "")),
                "%d %b %Y"
            ).date()
            end = datetime.strptime(
                str(stage.get("end_date", "")),
                "%d %b %Y"
            ).date()
        except ValueError:
            continue

        if start <= today <= end:
            return stage

    return None


def smart_reminder_add_task(tasks, title, detail, icon="🌾"):
    title = smart_reminder_clean(title)
    detail = smart_reminder_clean(detail)

    if not title or not detail:
        return

    tasks.append({
        "icon": icon,
        "title": title,
        "detail": detail
    })


@app.route(
    "/smart-reminder"
)
def smart_reminder():

    farmer_id = require_login()

    if farmer_id is None:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    active_farm = get_active_farm(farmer_id)

    if active_farm is None:
        flash(
            "Please add a farm before using Smart Reminder.",
            "error"
        )
        return redirect(
            url_for("farm_details", new="1")
        )

    # ---------------------------------------------------------
    # AVAILABLE FARM-SPECIFIC ANALYSES
    # ---------------------------------------------------------

    calendar_result = get_latest_farm_history_record(
        farmer_id,
        "crop_calendar",
        active_farm
    )

    fertilizer_result = get_latest_farm_history_record(
        farmer_id,
        "fertilizer_advisor",
        active_farm
    )

    latest_disease = get_latest_feature_analysis(
        farmer_id,
        "disease_detection",
        active_farm
    )

    latest_health = get_latest_feature_analysis(
        farmer_id,
        "crop_health",
        active_farm
    )

    today_tasks = []
    upcoming_tasks = []
    alerts = []
    sources = []

    crop_name = ""
    growth_stage = ""

    # ---------------------------------------------------------
    # CROP CALENDAR
    # ---------------------------------------------------------

    current_stage = smart_reminder_stage_from_calendar(
        calendar_result
    )

    if calendar_result:
        crop_name = smart_reminder_clean(
            calendar_result.get("crop")
        )
        sources.append("Crop Calendar")

    if current_stage:
        growth_stage = smart_reminder_clean(
            current_stage.get("name")
        )

        smart_reminder_add_task(
            today_tasks,
            "Crop activity",
            current_stage.get("activity", "Follow the current crop-calendar activity."),
            "🌱"
        )

        smart_reminder_add_task(
            today_tasks,
            "Field action",
            current_stage.get("action", "Inspect the crop and field condition."),
            "🚜"
        )

        smart_reminder_add_task(
            today_tasks,
            "Disease monitoring",
            current_stage.get("disease", "Inspect the crop for visible symptoms or stress."),
            "🦠"
        )

        stage_end = current_stage.get("end_date")
        if stage_end:
            try:
                end_date = datetime.strptime(
                    str(stage_end),
                    "%d %b %Y"
                ).date()
                if end_date >= date.today():
                    days_left = (end_date - date.today()).days
                    if days_left > 0:
                        upcoming_tasks.append({
                            "icon": "📅",
                            "title": "Current stage ends",
                            "detail": f"{current_stage.get('name', 'Current stage')} is expected to end around {end_date.strftime('%d %b %Y')} ({days_left} day(s) from today)."
                        })
            except ValueError:
                pass

        timeline = calendar_result.get("timeline") or []
        today = date.today()
        future_stages = []

        for stage in timeline:
            if not isinstance(stage, dict):
                continue
            try:
                start = datetime.strptime(
                    str(stage.get("start_date", "")),
                    "%d %b %Y"
                ).date()
            except ValueError:
                continue
            if start > today:
                future_stages.append((start, stage))

        future_stages.sort(key=lambda item: item[0])

        for start, stage in future_stages[:2]:
            upcoming_tasks.append({
                "icon": "📅",
                "title": stage.get("name", "Upcoming crop stage"),
                "detail": f"Expected around {start.strftime('%d %b %Y')}. {stage.get('action', '')}".strip()
            })

        smart_reminder_add_task(
            today_tasks,
            "Irrigation check",
            current_stage.get("irrigation", "Check soil moisture before irrigation."),
            "💧"
        )

        smart_reminder_add_task(
            today_tasks,
            "Nutrient task",
            current_stage.get("nutrient", "Follow the crop-specific nutrient plan."),
            "🧪"
        )

    # ---------------------------------------------------------
    # IRRIGATION + WEATHER INTELLIGENCE
    # ---------------------------------------------------------

    if crop_name and growth_stage:
        try:
            irrigation_result = analyze_irrigation(
                active_farm,
                crop_name,
                growth_stage,
                "unknown",
                ""
            )
        except Exception as error:
            irrigation_result = {
                "success": False,
                "error": str(error)
            }

        if irrigation_result.get("success"):
            sources.append("Irrigation Planner")
            irrigation_status = smart_reminder_clean(
                irrigation_result.get("decision")
                or irrigation_result.get("status")
                or irrigation_result.get("recommendation")
            )
            irrigation_reason = smart_reminder_clean(
                irrigation_result.get("reason")
                or irrigation_result.get("summary")
            )

            if irrigation_status:
                smart_reminder_add_task(
                    today_tasks,
                    "Irrigation planner",
                    f"{irrigation_status}. {irrigation_reason}".strip(),
                    "💧"
                )

        try:
            weather_result = analyze_weather_intelligence(
                active_farm,
                crop_name,
                growth_stage
            )
        except Exception as error:
            weather_result = {
                "success": False,
                "error": str(error)
            }

        if weather_result.get("success"):
            sources.append("Weather Intelligence")

            overall = smart_reminder_clean(
                weather_result.get("overall")
            )
            if overall:
                alerts.append({
                    "icon": weather_result.get("overall_icon", "🌦️"),
                    "title": "Weather impact",
                    "detail": overall + ". " + smart_reminder_clean(weather_result.get("weather_summary"))
                })

            for key, icon, label in (
                ("rain", "🌧️", "Rain risk"),
                ("heat", "🌡️", "Heat risk"),
                ("wind", "💨", "Wind risk"),
                ("humidity", "💦", "Humidity risk")
            ):
                item = weather_result.get(key) or {}
                risk = smart_reminder_clean(item.get("risk"))
                reason = smart_reminder_clean(item.get("reason"))
                if risk and risk.lower() not in {"low", "none"}:
                    alerts.append({
                        "icon": icon,
                        "title": label,
                        "detail": f"{risk}. {reason}".strip()
                    })

            for action in weather_result.get("actions") or []:
                smart_reminder_add_task(
                    today_tasks,
                    "Weather action",
                    action,
                    "🌦️"
                )

    # ---------------------------------------------------------
    # DISEASE / HEALTH
    # ---------------------------------------------------------

    if latest_disease:
        sources.append("Disease Detection")
        severity = smart_reminder_clean(latest_disease.get("severity"))
        disease = smart_reminder_clean(latest_disease.get("disease"))
        warning = smart_reminder_clean(latest_disease.get("warning"))

        if disease and disease.lower() not in {"healthy", "none", "no disease detected", "unknown"}:
            smart_reminder_add_task(
                today_tasks,
                "Disease monitoring",
                f"Latest analysis reported {disease} with severity {severity or 'not specified'}. Review the latest recommendations and inspect the field.",
                "🦠"
            )

        if warning:
            alerts.append({
                "icon": "⚠️",
                "title": "Disease warning",
                "detail": warning
            })

    if latest_health:
        sources.append("Crop Health")
        health_status = smart_reminder_clean(
            latest_health.get("health_status")
        )
        health_warning = smart_reminder_clean(
            latest_health.get("warning")
        )

        if health_status:
            smart_reminder_add_task(
                today_tasks,
                "Crop health check",
                f"Latest crop-health assessment: {health_status}. Inspect the crop and compare current field condition with the latest analysis.",
                "🌱"
            )

        if health_warning:
            alerts.append({
                "icon": "⚠️",
                "title": "Crop health warning",
                "detail": health_warning
            })

    # ---------------------------------------------------------
    # FERTILIZER ADVICE
    # ---------------------------------------------------------

    if fertilizer_result:
        sources.append("Fertilizer Advisor")

        recommendations = (
            fertilizer_result.get("recommendations")
            or fertilizer_result.get("actions")
            or fertilizer_result.get("fertilizer_recommendation")
        )

        if isinstance(recommendations, str):
            recommendations = [recommendations]

        for item in recommendations or []:
            if isinstance(item, dict):
                text = smart_reminder_clean(
                    item.get("recommendation")
                    or item.get("action")
                    or item.get("reason")
                )
            else:
                text = smart_reminder_clean(item)

            if text:
                smart_reminder_add_task(
                    today_tasks,
                    "Nutrient guidance",
                    text,
                    "🧪"
                )

    # ---------------------------------------------------------
    # NO-DATA STATE
    # ---------------------------------------------------------

    if not sources:
        upcoming_tasks.append({
            "icon": "📅",
            "title": "Set up your crop calendar",
            "detail": "Create a Crop Calendar for the active farm so Smart Reminder can generate crop-stage tasks."
        })

    if not today_tasks and sources:
        today_tasks.append({
            "icon": "🔎",
            "title": "Field check",
            "detail": "No specific task was triggered by the available analyses. Inspect the crop and soil moisture before taking action."
        })

    warning = (
        "Smart Reminder only surfaces actions supported by the available "
        "farm analyses. It does not invent fertilizer doses, irrigation volumes "
        "or fixed schedules. Verify actual field conditions before acting."
    )

    return render_template(
        "smart-reminder.html",
        active_farm=active_farm,
        crop_name=crop_name,
        growth_stage=growth_stage,
        today_tasks=today_tasks,
        upcoming_tasks=upcoming_tasks,
        alerts=alerts,
        sources=sources,
        generated_on=date.today().strftime("%d %b %Y"),
        warning=warning
    )


# =========================================================
# CROP REPORT
# =========================================================


def crop_report_text(value):
    if value is None:
        return ""
    return str(value).strip()


def crop_report_list(value):
    if isinstance(value, list):
        return [
            crop_report_text(item)
            for item in value
            if crop_report_text(item)
        ]
    if value in (None, ""):
        return []
    return [crop_report_text(value)]


def crop_report_feature_status(data, available_label="Available"):
    if isinstance(data, dict) and data:
        return available_label
    return "Not available"


@app.route(
    "/crop-report"
)
def crop_report():

    farmer_id = require_login()

    if farmer_id is None:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    active_farm = get_active_farm(farmer_id)

    if active_farm is None:
        flash(
            "Please add a farm before using Crop Report.",
            "error"
        )
        return redirect(url_for("farm_details", new="1"))

    # ---------------------------------------------------------
    # LATEST SAVED ANALYSES
    # ---------------------------------------------------------

    soil_report = get_latest_soil_report(active_farm)

    disease_analysis = get_latest_feature_analysis(
        farmer_id,
        "disease_detection",
        active_farm
    )

    crop_health_analysis = get_latest_feature_analysis(
        farmer_id,
        "crop_health",
        active_farm
    )

    crop_calendar = get_latest_farm_history_record(
        farmer_id,
        "crop_calendar",
        active_farm
    )

    fertilizer_analysis = get_latest_farm_history_record(
        farmer_id,
        "fertilizer_advisor",
        active_farm
    )

    farm_risk_analysis = get_latest_farm_history_record(
        farmer_id,
        "farm_risk",
        active_farm
    )

    # ---------------------------------------------------------
    # CURRENT CROP / STAGE
    # ---------------------------------------------------------

    crop_name = ""
    growth_stage = ""

    if isinstance(crop_calendar, dict):
        crop_name = crop_report_text(crop_calendar.get("crop"))

        timeline = crop_calendar.get("timeline") or []
        today = date.today()

        for stage in timeline:
            if not isinstance(stage, dict):
                continue

            try:
                start = datetime.strptime(
                    str(stage.get("start_date", "")),
                    "%d %b %Y"
                ).date()
                end = datetime.strptime(
                    str(stage.get("end_date", "")),
                    "%d %b %Y"
                ).date()
            except ValueError:
                continue

            if start <= today <= end:
                growth_stage = crop_report_text(stage.get("name"))
                break

    if not crop_name and isinstance(crop_health_analysis, dict):
        crop_name = crop_report_text(crop_health_analysis.get("crop"))
        growth_stage = growth_stage or crop_report_text(
            crop_health_analysis.get("growth_stage")
        )

    if not crop_name and isinstance(disease_analysis, dict):
        crop_name = crop_report_text(disease_analysis.get("crop"))

    if not crop_name and isinstance(farm_risk_analysis, dict):
        crop_name = crop_report_text(farm_risk_analysis.get("crop"))
        growth_stage = growth_stage or crop_report_text(
            farm_risk_analysis.get("growth_stage")
        )

    # ---------------------------------------------------------
    # WEATHER
    # ---------------------------------------------------------

    weather = None
    weather_intelligence = None

    try:
        weather = fetch_weather_intelligence_weather(active_farm)
    except Exception as error:
        print("Crop Report weather error:", error)

    if crop_name and growth_stage:
        try:
            weather_intelligence = analyze_weather_intelligence(
                farm=active_farm,
                crop_name=crop_name,
                growth_stage=growth_stage
            )
        except Exception as error:
            print("Crop Report weather intelligence error:", error)

    # ---------------------------------------------------------
    # IRRIGATION
    # ---------------------------------------------------------

    irrigation_analysis = None

    if crop_name and growth_stage:
        try:
            irrigation_analysis = analyze_irrigation(
                farm=active_farm,
                crop_name=crop_name,
                growth_stage=growth_stage,
                soil_moisture="unknown",
                field_observation=""
            )
        except Exception as error:
            print("Crop Report irrigation error:", error)

    # ---------------------------------------------------------
    # CROP RECOMMENDATION
    # ---------------------------------------------------------

    crop_recommendation_result = None

    if soil_report is not None:
        try:
            crop_recommendation_result = run_crop_recommendation(
                {},
                active_farm
            )
        except Exception as error:
            print("Crop Report recommendation error:", error)

    # ---------------------------------------------------------
    # COMBINED ACTIONS / WARNINGS
    # ---------------------------------------------------------

    important_actions = []
    warnings = []

    if isinstance(weather_intelligence, dict) and weather_intelligence.get("success"):
        important_actions.extend(
            crop_report_list(weather_intelligence.get("actions"))
        )
        if weather_intelligence.get("warning"):
            warnings.append(weather_intelligence.get("warning"))

    if isinstance(irrigation_analysis, dict) and irrigation_analysis.get("success"):
        status = crop_report_text(
            irrigation_analysis.get("status_label")
            or irrigation_analysis.get("status")
        )
        if status:
            important_actions.append(
                f"Irrigation status: {status}."
            )
        important_actions.extend(
            crop_report_list(irrigation_analysis.get("farmer_action"))
        )
        if irrigation_analysis.get("warning"):
            warnings.append(irrigation_analysis.get("warning"))

    if isinstance(crop_health_analysis, dict):
        important_actions.extend(
            crop_report_list(crop_health_analysis.get("recommendations"))
        )
        if crop_health_analysis.get("warning"):
            warnings.append(crop_health_analysis.get("warning"))

    if isinstance(disease_analysis, dict):
        important_actions.extend(
            crop_report_list(disease_analysis.get("recommendations"))
        )
        if disease_analysis.get("warning"):
            warnings.append(disease_analysis.get("warning"))

    if isinstance(fertilizer_analysis, dict):
        important_actions.extend(
            crop_report_list(
                fertilizer_analysis.get("recommendations")
                or fertilizer_analysis.get("actions")
            )
        )
        if fertilizer_analysis.get("warning"):
            warnings.append(fertilizer_analysis.get("warning"))

    if isinstance(farm_risk_analysis, dict):
        important_actions.extend(
            crop_report_list(farm_risk_analysis.get("actions"))
        )
        if farm_risk_analysis.get("warning"):
            warnings.append(farm_risk_analysis.get("warning"))

    # Keep report readable and remove duplicates.
    def unique_items(items, limit=8):
        output = []
        seen = set()
        for item in items:
            item = crop_report_text(item)
            key = item.lower()
            if not item or key in seen:
                continue
            seen.add(key)
            output.append(item)
            if len(output) >= limit:
                break
        return output

    important_actions = unique_items(important_actions)
    warnings = unique_items(warnings, limit=5)

    if not important_actions:
        important_actions = [
            "Continue regular crop, soil and field monitoring."
        ]

    if not warnings:
        warnings = [
            "This report uses only the Smart Kisan analyses currently available for this farm."
        ]

    # ---------------------------------------------------------
    # SOURCE STATUS
    # ---------------------------------------------------------

    sources = [
        {
            "name": "Farm Details",
            "status": "Available"
        },
        {
            "name": "Live Weather",
            "status": crop_report_feature_status(weather)
        },
        {
            "name": "Weather Intelligence",
            "status": crop_report_feature_status(weather_intelligence)
        },
        {
            "name": "Soil Report",
            "status": crop_report_feature_status(soil_report)
        },
        {
            "name": "Crop Recommendation",
            "status": crop_report_feature_status(
                crop_recommendation_result
                if isinstance(crop_recommendation_result, dict)
                and crop_recommendation_result.get("success")
                else None
            )
        },
        {
            "name": "Disease Detection",
            "status": crop_report_feature_status(disease_analysis)
        },
        {
            "name": "Crop Health",
            "status": crop_report_feature_status(crop_health_analysis)
        },
        {
            "name": "Irrigation Planner",
            "status": crop_report_feature_status(
                irrigation_analysis
                if isinstance(irrigation_analysis, dict)
                and irrigation_analysis.get("success")
                else None
            )
        },
        {
            "name": "Fertilizer Advisor",
            "status": crop_report_feature_status(fertilizer_analysis)
        },
        {
            "name": "Crop Calendar",
            "status": crop_report_feature_status(crop_calendar)
        },
        {
            "name": "Farm Risk",
            "status": crop_report_feature_status(farm_risk_analysis)
        }
    ]

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    return render_template(
        "crop-report.html",
        active_farm=active_farm,
        crop_name=crop_name or "Not recorded",
        growth_stage=growth_stage or "Not recorded",
        soil_report=soil_report,
        weather=weather,
        weather_intelligence=weather_intelligence,
        crop_recommendation=crop_recommendation_result,
        disease_analysis=disease_analysis,
        crop_health_analysis=crop_health_analysis,
        irrigation_analysis=irrigation_analysis,
        fertilizer_analysis=fertilizer_analysis,
        crop_calendar=crop_calendar,
        farm_risk_analysis=farm_risk_analysis,
        important_actions=important_actions,
        warnings=warnings,
        sources=sources,
        generated_on=date.today().strftime("%d %b %Y")
    )


# =========================================================
# GOVERNMENT SCHEMES
# =========================================================

GOVERNMENT_SCHEMES = [
    {
        "id": "pm_kisan",
        "name": "PM-KISAN Samman Nidhi",
        "type": "Central",
        "icon": "💰",
        "purpose": (
            "Income support for landholding farmer families. "
            "The official PM-KISAN portal states support of ₹6,000 per year "
            "in three equal instalments, subject to the scheme guidelines "
            "and exclusions."
        ),
        "eligibility": (
            "Landholding farmer family status is required, and the scheme has "
            "specific exclusion categories. State authorities identify eligible families."
        ),
        "benefits": [
            "₹6,000 per year in three equal instalments, subject to eligibility and exclusions.",
            "Direct transfer to the beneficiary bank account."
        ],
        "documents": [
            "Land ownership / land-record details as required by the state process.",
            "Aadhaar and bank-account details as applicable.",
            "Any additional verification documents requested by the authorities."
        ],
        "process": (
            "Use the official PM-KISAN portal to check status and complete any required "
            "eKYC or verification steps."
        ),
        "official_url": "https://pmkisan.gov.in/",
        "source": "PM-KISAN official portal",
        "verified_on": "04 Oct 2026"
    },
    {
        "id": "pmfby",
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "type": "Central",
        "icon": "🛡️",
        "purpose": (
            "Crop insurance protection against covered non-preventable natural risks. "
            "The official portal provides farmer application, premium calculation, policy-status "
            "and crop-loss/grievance services."
        ),
        "eligibility": (
            "Eligibility depends on the notified crop, season, area/unit and the applicable "
            "state/district notification."
        ),
        "benefits": [
            "Insurance cover for eligible notified crops and risks under the applicable PMFBY notification.",
            "Online premium calculator and policy-status services are available on the official portal."
        ],
        "documents": [
            "Crop and cultivation details.",
            "Land / tenancy or other documents required under the applicable notification.",
            "Bank and identity details as required for enrolment."
        ],
        "process": (
            "Check the official PMFBY portal for the current notified crop/season in your area, "
            "then use the official farmer application or the prescribed channel."
        ),
        "official_url": "https://pmfby.gov.in/",
        "source": "PMFBY official portal",
        "verified_on": "04 Oct 2026"
    },
    {
        "id": "pmksy_micro",
        "name": "PMKSY – Per Drop More Crop (Micro-Irrigation)",
        "type": "Maharashtra Farmer Scheme",
        "icon": "💧",
        "purpose": (
            "Promotes micro-irrigation and improved on-farm water-use efficiency through "
            "precision and water-saving irrigation systems."
        ),
        "eligibility": (
            "The current Maharashtra MahaDBT page lists Aadhaar, 7/12 and 8-A records, "
            "specific conditions for the irrigation setup, and an eligible area limit of 5 hectares."
        ),
        "benefits": [
            "The current Maharashtra page lists 55% subsidy for small and marginal farmers and 45% for other farmers."
        ],
        "documents": [
            "Aadhaar Card",
            "7/12 Certificate",
            "8-A Certificate",
            "Recent electricity bill where the applicable pump-connection condition applies",
            "Invoice proof and pre-sanction letter where applicable"
        ],
        "process": (
            "Apply/check status through the Maharashtra MahaDBT Farmer portal and follow the "
            "current component-specific pre-sanction and purchase/installation procedure."
        ),
        "official_url": "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=E9DDFA703C38E51A7CB56240D6D84F28",
        "source": "MahaDBT Farmer Scheme page",
        "verified_on": "04 Oct 2026"
    },
    {
        "id": "farm_mechanization",
        "name": "Sub-Mission on Farm Mechanization",
        "type": "Maharashtra Farmer Scheme",
        "icon": "🚜",
        "purpose": (
            "Promotes farm mechanization and provides financial assistance for procurement of "
            "farm machinery and implements."
        ),
        "eligibility": (
            "The Maharashtra page lists Aadhaar and land records, category-specific documents where applicable, "
            "and restrictions related to previously assisted equipment/components."
        ),
        "benefits": [
            "Financial assistance is provided for eligible farm machinery/implements under the current component rules."
        ],
        "documents": [
            "Aadhaar Card",
            "7/12 Certificate",
            "8-A Certificate",
            "Equipment quotation and required testing certificate",
            "Caste certificate for SC/ST beneficiaries where applicable",
            "Self Declaration and Pre-Sanction Letter where applicable"
        ],
        "process": (
            "Use the MahaDBT Farmer portal and check the current component, application window and "
            "selection conditions before applying."
        ),
        "official_url": "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=E9DDFA703C38E51A23C0254248DAFF28",
        "source": "MahaDBT Farmer Scheme page",
        "verified_on": "04 Oct 2026"
    },
    {
        "id": "dr_ambedkar_krushi",
        "name": "Dr. Babasaheb Ambedkar Krushi Swavalamban Yojana",
        "type": "Maharashtra Farmer Scheme",
        "icon": "🌱",
        "purpose": (
            "Supports SC / Nav-Buddhist farmers with irrigation and moisture-management related components "
            "under the Maharashtra Agriculture Department."
        ),
        "eligibility": (
            "The current Maharashtra page requires SC category, valid caste certificate, 7/12 and 8-A records, "
            "annual income up to ₹1.50 lakh, and landholding of 0.20–6 hectares (0.40–6 hectares for a new well). "
            "The current page also lists district exclusions for this scheme."
        ),
        "benefits": [
            "The current page lists support components such as new well, well repair, pumps, electricity connection charges, "
            "farm-pond lining and micro-irrigation, subject to component conditions."
        ],
        "documents": [
            "Valid SC caste certificate",
            "7/12 and 8-A land records",
            "Income certificate where required",
            "Component-specific supporting documents and field/authority certificates as applicable"
        ],
        "process": (
            "Check the current MahaDBT component details and application status before applying because eligibility "
            "and documents vary by the selected component."
        ),
        "official_url": "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=E9DDFA703C38E51A986837A04E50D9EF",
        "source": "MahaDBT Farmer Scheme page",
        "verified_on": "04 Oct 2026"
    }
]


def government_scheme_text(value):
    if value is None:
        return ""
    return str(value).strip()


def government_scheme_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def government_scheme_area_ha(area, unit):
    value = government_scheme_number(area)
    if value is None or value <= 0:
        return None

    unit = government_scheme_text(unit).lower()

    if unit.startswith("hect"):
        return value
    if unit.startswith("acre"):
        return value * 0.4046856422
    if "guntha" in unit or "gunta" in unit:
        return value * 0.010117141

    return value


def government_scheme_status(score, strong_match=False):
    if strong_match:
        return "Possibly Eligible"
    if score >= 2:
        return "Possibly Eligible"
    return "Verification Required"


def match_government_schemes(farmer, farm, answers):
    farmer = dict(farmer or {})
    farm = dict(farm or {})
    answers = dict(answers or {})

    district = government_scheme_text(farm.get("district"))
    season = government_scheme_text(farm.get("season"))
    crop = government_scheme_text(answers.get("crop_name"))
    soil_type = government_scheme_text(farm.get("soil_type"))
    irrigation = government_scheme_text(farm.get("irrigation"))
    purpose = government_scheme_text(answers.get("support_need")).lower()
    category = government_scheme_text(answers.get("category")).upper()
    income = government_scheme_number(answers.get("annual_income"))
    area_ha = government_scheme_area_ha(
        farm.get("area"),
        farm.get("area_unit")
    )
    electricity = government_scheme_text(
        answers.get("electricity_connection")
    ).lower()

    results = []

    for scheme in GOVERNMENT_SCHEMES:
        score = 0
        reasons = []
        verification = []
        strong_match = False

        if scheme["id"] == "pm_kisan":
            if area_ha and area_ha > 0:
                score += 2
                reasons.append("Your farm has a recorded land area.")
            if crop:
                score += 1
                reasons.append("A crop is recorded for the farm/application.")
            verification.extend([
                "Landholding/family status and PM-KISAN exclusion conditions must be verified.",
                "eKYC/status should be checked on the official PM-KISAN portal."
            ])

        elif scheme["id"] == "pmfby":
            if crop:
                score += 2
                reasons.append("A crop is available for insurance matching.")
            if season:
                score += 1
                reasons.append(f"The farm season is recorded as {season}.")
            verification.extend([
                "The crop, insurance unit, season and applicable notification must be checked for this farm.",
                "Application timing and current notification must be verified before enrolment."
            ])

        elif scheme["id"] == "pmksy_micro":
            if "irrigation" in purpose or "water" in purpose or "drip" in purpose or "sprinkler" in purpose:
                score += 3
                reasons.append("You selected irrigation/water support.")
            if irrigation:
                score += 1
                reasons.append(f"Recorded irrigation method: {irrigation}.")
            if area_ha is not None and area_ha <= 5:
                score += 1
                reasons.append("Recorded farm area is within the current 5-hectare scheme limit.")
            elif area_ha is not None:
                verification.append("The current scheme page lists a 5-hectare eligible area limit for this component.")
            verification.extend([
                "Aadhaar and 7/12/8-A requirements must be satisfied.",
                "The applicable pump/electricity condition must be checked for the proposed setup."
            ])

        elif scheme["id"] == "farm_mechanization":
            if "machine" in purpose or "machinery" in purpose or "equipment" in purpose or "tractor" in purpose:
                score += 3
                reasons.append("You selected machinery/equipment support.")
            if area_ha:
                score += 1
                reasons.append("Farm area is available for component-level verification.")
            verification.extend([
                "The specific equipment/component and previous-benefit restrictions must be checked.",
                "Current application-window and pre-sanction rules must be verified."
            ])

        elif scheme["id"] == "dr_ambedkar_krushi":
            if category == "SC":
                score += 3
                reasons.append("You selected SC category, which is a mandatory condition on the current scheme page.")
            elif category:
                verification.append("This scheme is specifically for SC / Nav-Buddhist farmers according to the current page.")
            if income is not None and income <= 150000:
                score += 2
                reasons.append("Recorded annual income is within the current ₹1.50 lakh limit.")
            elif income is not None:
                verification.append("Recorded annual income is above the current ₹1.50 lakh limit shown on the scheme page.")
            if area_ha is not None and 0.20 <= area_ha <= 6:
                score += 1
                reasons.append("Recorded farm area falls within the current 0.20–6 hectare landholding range.")
            elif area_ha is not None:
                verification.append("Recorded landholding is outside the current 0.20–6 hectare range.")

            excluded_districts = {
                "mumbai",
                "sindhudurg",
                "ratnagiri",
                "satara",
                "sangli",
                "kolhapur"
            }
            if district.lower() in excluded_districts:
                verification.append(
                    f"The current Maharashtra scheme page excludes {district} from this scheme."
                )
                score = 0
            else:
                strong_match = category == "SC" and income is not None and income <= 150000 and area_ha is not None and 0.20 <= area_ha <= 6

            verification.extend([
                "A valid SC caste certificate and current land records are required.",
                "Exact component-wise documents and field conditions vary by the requested support item."
            ])

        status = government_scheme_status(score, strong_match=strong_match)

        if score == 0 and not reasons:
            reasons = ["The current saved profile does not provide enough information for a stronger match."]

        results.append({
            **scheme,
            "score": score,
            "status": status,
            "reasons": reasons,
            "verification": list(dict.fromkeys(verification)),
            "match_level": min(5, max(1, score))
        })

    # User-selected need first, then stronger rule matches.
    results.sort(key=lambda item: (item.get("score", 0), item.get("id") == "pm_kisan"), reverse=True)
    return results


@app.route(
    "/government-schemes",
    methods=["GET", "POST"]
)
def government_schemes():

    farmer_id = require_login()

    if farmer_id is None:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    active_farm = get_active_farm(farmer_id)

    if active_farm is None:
        flash(
            "Please add a farm before using Government Schemes.",
            "error"
        )
        return redirect(url_for("farm_details", new="1"))

    farmer = get_farmer_by_id(farmer_id) or {}

    form_data = {
        "crop_name": "",
        "category": "",
        "annual_income": "",
        "support_need": "",
        "electricity_connection": ""
    }

    results = []

    if request.method == "POST":
        form_data = {
            "crop_name": request.form.get("crop_name", "").strip(),
            "category": request.form.get("category", "").strip(),
            "annual_income": request.form.get("annual_income", "").strip(),
            "support_need": request.form.get("support_need", "").strip(),
            "electricity_connection": request.form.get("electricity_connection", "").strip()
        }

        results = match_government_schemes(
            farmer=farmer,
            farm=active_farm,
            answers=form_data
        )

        try:
            history_data = {
                "_farm_id": active_farm.get("farm_id"),
                "answers": form_data,
                "results": [
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "status": item["status"],
                        "score": item["score"]
                    }
                    for item in results
                ],
                "generated_on": date.today().isoformat()
            }

            add_ai_history(
                farmer_id,
                "government_schemes",
                "Government scheme matching",
                json.dumps(history_data, ensure_ascii=False)
            )
        except Exception as error:
            print("Government Schemes history save error:", error)

    return render_template(
        "government-schemes.html",
        farmer=farmer,
        active_farm=active_farm,
        form_data=form_data,
        results=results,
        generated_on=date.today().strftime("%d %b %Y")
    )


# =========================================================
# AI HISTORY API
# =========================================================

@app.route(
    "/api/ai-history",
    methods=["GET"]
)
def api_ai_history():

    farmer_id = require_login()

    if farmer_id is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401

    try:

        limit = request.args.get(
            "limit",
            default=20,
            type=int
        )

        limit = max(
            1,
            min(
                limit,
                100
            )
        )

        history = get_ai_history(

            farmer_id,

            limit

        )

        history_list = []

        for item in history:

            history_list.append({

                "id":
                    item["id"],

                "farmer_id":
                    item["farmer_id"],

                "feature":
                    item["feature"],

                "question":
                    item["question"],

                "answer":
                    item["answer"],

                "created_at":
                    item["created_at"]

            })

        return jsonify({

            "success":
                True,

            "history":
                history_list

        })

    except Exception as error:

        print(
            "AI History API error:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                "Unable to load AI history."

        }), 500


# =========================================================
# CLEAR AI HISTORY
# =========================================================

@app.route(
    "/api/ai-history/clear",
    methods=["POST"]
)
def api_clear_ai_history():

    farmer_id = require_login()

    if farmer_id is None:

        return jsonify({

            "success":
                False,

            "error":
                "Please login first."

        }), 401

    try:

        deleted = clear_ai_history(
            farmer_id
        )

        return jsonify({

            "success":
                True,

            "deleted":
                deleted,

            "message":
                "AI history cleared successfully."

        })

    except Exception as error:

        print(
            "AI History clear error:",
            error
        )

        return jsonify({

            "success":
                False,

            "error":
                "Unable to clear AI history."

        }), 500


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health"
)
def health():

    return {

        "status":
            "ok",

        "application":
            "Smart Kisan AI"

    }


# =========================================================
# 404 ERROR
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return redirect(
        url_for("home")
    )


# =========================================================
# 500 ERROR
# =========================================================

@app.errorhandler(500)
def internal_server_error(
    error
):

    return """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Smart Kisan AI</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    min-height: 100vh;

    display: grid;

    place-items: center;

    background: #f5faf7;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
}

.error-box {

    width: min(
        calc(100% - 40px),
        500px
    );

    padding: 40px;

    text-align: center;

    background: white;

    border-radius: 22px;

    box-shadow:
        0 20px 60px
        rgba(0,0,0,.08);
}

.error-icon {

    font-size: 45px;

    margin-bottom: 15px;
}

h1 {

    margin: 0 0 10px;

    color: #159447;
}

p {

    margin: 0;

    color: #66766d;

    font-size: 14px;

    line-height: 1.6;
}

a {

    display: inline-block;

    margin-top: 20px;

    padding: 12px 20px;

    border-radius: 10px;

    background: #159447;

    color: white;

    text-decoration: none;

    font-weight: 700;

    font-size: 13px;
}

a:hover {

    background: #0b6c32;
}

</style>

</head>

<body>

<div class="error-box">

    <div class="error-icon">
        🌾
    </div>

    <h1>
        Smart Kisan AI
    </h1>

    <p>
        Something went wrong while processing
        your request. Please return to the
        Smart Kisan home page.
    </p>

    <a href="/">
        Back to Home
    </a>

</div>

</body>

</html>
""", 500


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(

        host="127.0.0.1",

        port=5014,

        debug=True

    )