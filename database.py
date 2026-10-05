# =========================================================
# SMART KISAN AI
# DATABASE
# =========================================================

import os
import sqlite3

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# =========================================================
# DATABASE PATH
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE_NAME = os.path.join(
    BASE_DIR,
    "database.db"
)


# =========================================================
# CONNECTION
# =========================================================

def get_connection():

    conn = sqlite3.connect(
        DATABASE_NAME,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    conn = get_connection()

    try:

        cursor = conn.cursor()

        # =================================================
        # FARMERS
        # =================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers (

                farmer_id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                mobile TEXT NOT NULL UNIQUE,

                password TEXT NOT NULL,

                language TEXT NOT NULL DEFAULT 'en',

                state TEXT NOT NULL DEFAULT 'Maharashtra',

                district TEXT NOT NULL,

                taluka TEXT NOT NULL,

                village TEXT NOT NULL,

                created_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        # =================================================
        # FARMS
        # =================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farms (

                farm_id INTEGER PRIMARY KEY AUTOINCREMENT,

                farmer_id INTEGER NOT NULL,

                farm_name TEXT NOT NULL,

                area REAL NOT NULL,

                area_unit TEXT NOT NULL,

                soil_type TEXT NOT NULL,

                irrigation TEXT NOT NULL,

                water_source TEXT NOT NULL,

                season TEXT NOT NULL,

                previous_crop TEXT NOT NULL,

                state TEXT,

                district TEXT,

                taluka TEXT,

                village TEXT,

                latitude REAL,

                longitude REAL,

                location_level TEXT,

                created_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                updated_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (farmer_id)
                    REFERENCES farmers(farmer_id)
                    ON DELETE CASCADE
            )
        """)


        # =================================================
        # AI HISTORY
        # =================================================

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                farmer_id INTEGER NOT NULL,

                feature TEXT,

                question TEXT,

                answer TEXT,

                created_at
                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (farmer_id)
                    REFERENCES farmers(farmer_id)
                    ON DELETE CASCADE
            )
        """)


        # =================================================
        # MIGRATE OLD FARM TABLE
        # =================================================

        cursor.execute(
            "PRAGMA table_info(farms)"
        )

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_columns = {

            "state": "TEXT",
            "district": "TEXT",
            "taluka": "TEXT",
            "village": "TEXT",
            "location_level": "TEXT",
            "updated_at": "TIMESTAMP"
        }

        for column_name, column_type in required_columns.items():

            if column_name not in existing_columns:

                cursor.execute(
                    f"""
                    ALTER TABLE farms
                    ADD COLUMN
                    {column_name}
                    {column_type}
                    """
                )


        conn.commit()

    finally:

        conn.close()


# =========================================================
# FARMER
# =========================================================

def add_farmer(
    name,
    mobile,
    password,
    language,
    state,
    district,
    taluka,
    village
):

    conn = get_connection()

    try:

        password_hash = generate_password_hash(
            password
        )

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO farmers (
                name,
                mobile,
                password,
                language,
                state,
                district,
                taluka,
                village
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                mobile.strip(),
                password_hash,
                language.strip(),
                state.strip(),
                district.strip(),
                taluka.strip(),
                village.strip()
            )
        )

        conn.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:

        return None

    except sqlite3.Error as error:

        print(
            "DATABASE ERROR:",
            error
        )

        return None

    finally:

        conn.close()


# =========================================================
# LOGIN
# =========================================================

def check_farmer(
    mobile,
    password
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM farmers
            WHERE mobile = ?
            """,
            (
                mobile.strip(),
            )
        )

        farmer = cursor.fetchone()

    finally:

        conn.close()


    if farmer is None:

        return None


    try:

        valid = check_password_hash(
            farmer["password"],
            password
        )

    except (
        ValueError,
        TypeError
    ):

        valid = False


    if valid:

        return farmer

    return None


# =========================================================
# GET FARMER
# =========================================================

def get_farmer_by_id(
    farmer_id
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM farmers
            WHERE farmer_id = ?
            """,
            (
                farmer_id,
            )
        )

        farmer = cursor.fetchone()

    finally:

        conn.close()

    return farmer


# =========================================================
# GET FARMER BY MOBILE
# =========================================================

def get_farmer_by_mobile(
    mobile
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM farmers
            WHERE mobile = ?
            """,
            (
                mobile.strip(),
            )
        )

        farmer = cursor.fetchone()

    finally:

        conn.close()

    return farmer


# =========================================================
# ADD NEW FARM
# =========================================================
#
# IMPORTANT:
# Every call with farm_id=None creates a NEW farm.
#
# This means:
#
# Farmer 1
#   → Farm A
#   → Farm B
#   → Farm C
#
# are all independent records.
# =========================================================

def add_farm(
    farmer_id,
    farm_name,
    area,
    area_unit,
    soil_type,
    irrigation,
    water_source,
    season,
    previous_crop,
    state=None,
    district=None,
    taluka=None,
    village=None,
    latitude=None,
    longitude=None,
    location_level=None,
    farm_id=None
):

    conn = get_connection()

    try:

        cursor = conn.cursor()


        # =================================================
        # UPDATE EXISTING FARM
        # =================================================

        if farm_id is not None:

            cursor.execute(
                """
                UPDATE farms
                SET
                    farm_name = ?,
                    area = ?,
                    area_unit = ?,
                    soil_type = ?,
                    irrigation = ?,
                    water_source = ?,
                    season = ?,
                    previous_crop = ?,
                    state = ?,
                    district = ?,
                    taluka = ?,
                    village = ?,
                    latitude = ?,
                    longitude = ?,
                    location_level = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    farm_id = ?
                    AND farmer_id = ?
                """,
                (
                    farm_name.strip(),
                    area,
                    area_unit.strip(),
                    soil_type.strip(),
                    irrigation.strip(),
                    water_source.strip(),
                    season.strip(),
                    previous_crop.strip(),

                    state.strip()
                    if state
                    else None,

                    district.strip()
                    if district
                    else None,

                    taluka.strip()
                    if taluka
                    else None,

                    village.strip()
                    if village
                    else None,

                    latitude,
                    longitude,
                    location_level,

                    farm_id,
                    farmer_id
                )
            )

            conn.commit()

            if cursor.rowcount == 0:

                return None

            return farm_id


        # =================================================
        # INSERT NEW FARM
        # =================================================

        cursor.execute(
            """
            INSERT INTO farms (
                farmer_id,
                farm_name,
                area,
                area_unit,
                soil_type,
                irrigation,
                water_source,
                season,
                previous_crop,
                state,
                district,
                taluka,
                village,
                latitude,
                longitude,
                location_level
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                farmer_id,
                farm_name.strip(),
                area,
                area_unit.strip(),
                soil_type.strip(),
                irrigation.strip(),
                water_source.strip(),
                season.strip(),
                previous_crop.strip(),

                state.strip()
                if state
                else None,

                district.strip()
                if district
                else None,

                taluka.strip()
                if taluka
                else None,

                village.strip()
                if village
                else None,

                latitude,
                longitude,
                location_level
            )
        )

        conn.commit()

        return cursor.lastrowid


    except sqlite3.Error as error:

        conn.rollback()

        print(
            "DATABASE ERROR while saving farm:",
            error
        )

        return None

    finally:

        conn.close()


# =========================================================
# GET ALL FARMS FOR A FARMER
# =========================================================

def get_farms_by_farmer(
    farmer_id
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM farms
            WHERE farmer_id = ?
            ORDER BY farm_id ASC
            """,
            (
                farmer_id,
            )
        )

        farms = cursor.fetchall()

    finally:

        conn.close()

    return farms


# =========================================================
# GET ONE FARM
# =========================================================

def get_farm_by_id(
    farm_id,
    farmer_id=None
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        if farmer_id is None:

            cursor.execute(
                """
                SELECT *
                FROM farms
                WHERE farm_id = ?
                """,
                (
                    farm_id,
                )
            )

        else:

            cursor.execute(
                """
                SELECT *
                FROM farms
                WHERE
                    farm_id = ?
                    AND farmer_id = ?
                """,
                (
                    farm_id,
                    farmer_id
                )
            )

        farm = cursor.fetchone()

    finally:

        conn.close()

    return farm


# =========================================================
# GET ACTIVE / DEFAULT FARM
# =========================================================

def get_farm(
    farmer_id,
    farm_id=None
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        if farm_id is not None:

            cursor.execute(
                """
                SELECT *
                FROM farms
                WHERE
                    farm_id = ?
                    AND farmer_id = ?
                """,
                (
                    farm_id,
                    farmer_id
                )
            )

        else:

            cursor.execute(
                """
                SELECT *
                FROM farms
                WHERE farmer_id = ?
                ORDER BY updated_at DESC,
                         farm_id DESC
                LIMIT 1
                """,
                (
                    farmer_id,
                )
            )

        farm = cursor.fetchone()

    finally:

        conn.close()

    return farm


# =========================================================
# DELETE FARM
# =========================================================

def delete_farm(
    farm_id,
    farmer_id
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM farms
            WHERE
                farm_id = ?
                AND farmer_id = ?
            """,
            (
                farm_id,
                farmer_id
            )
        )

        deleted = cursor.rowcount > 0

        conn.commit()

        return deleted

    except sqlite3.Error as error:

        conn.rollback()

        print(
            "DATABASE ERROR:",
            error
        )

        return False

    finally:

        conn.close()


# =========================================================
# AI HISTORY
# =========================================================

def add_ai_history(
    farmer_id,
    feature,
    question,
    answer
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO ai_history (
                farmer_id,
                feature,
                question,
                answer
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                farmer_id,
                feature,
                question,
                answer
            )
        )

        conn.commit()

        return cursor.lastrowid

    except sqlite3.Error:

        conn.rollback()

        return None

    finally:

        conn.close()


# =========================================================
# GET AI HISTORY
# =========================================================

def get_ai_history(
    farmer_id,
    limit=20
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM ai_history
            WHERE farmer_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                farmer_id,
                int(limit)
            )
        )

        history = cursor.fetchall()

    finally:

        conn.close()

    return history


# =========================================================
# CLEAR AI HISTORY
# =========================================================

def clear_ai_history(
    farmer_id
):

    conn = get_connection()

    try:

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM ai_history
            WHERE farmer_id = ?
            """,
            (
                farmer_id,
            )
        )

        deleted_rows = cursor.rowcount

        conn.commit()

        return deleted_rows

    except sqlite3.Error:

        conn.rollback()

        return 0

    finally:

        conn.close()


# =========================================================
# INITIALIZE
# =========================================================

if __name__ == "__main__":

    create_tables()

    print(
        "Smart Kisan database initialized successfully."
    )

    print(
        f"Database location: {DATABASE_NAME}"
    )