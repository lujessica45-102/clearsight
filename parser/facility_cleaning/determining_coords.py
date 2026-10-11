
import sqlite3
import requests
import time
from pathlib import Path

DB_PATH = Path("/Users/jessicalu/Desktop/fantastic-fiesta/parser/facilities.db")

GEOCODER_URL = (
    "https://geocoding.geo.census.gov/geocoder/"
    "locations/onelineaddress"
)


def geocode_address(address):
    """Return latitude, longitude, and matched address."""

    try:
        response = requests.get(
            GEOCODER_URL,
            params={
                "address": address,
                "benchmark": "Public_AR_Current",
                "format": "json",
            },
            timeout=20,
        )
        response.raise_for_status()

        matches = (
            response.json()
            .get("result", {})
            .get("addressMatches", [])
        )

        if not matches:
            return None, None, None

        match = matches[0]
        coordinates = match["coordinates"]

        # Census uses x for longitude and y for latitude.
        longitude = float(coordinates["x"])
        latitude = float(coordinates["y"])
        matched_address = match.get("matchedAddress", "")

        return latitude, longitude, matched_address

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        print(f"Error geocoding {address}: {error}")
        return None, None, None


def populate_coordinates():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Update DB_PATH to point to your existing database."
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        # Confirm that we opened the correct database.
        tables = {
            row[0]
            for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """).fetchall()
        }

        if "public_facilities" not in tables:
            raise RuntimeError(
                f"No public_facilities table found in {DB_PATH}"
            )

        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(public_facilities)"
            ).fetchall()
        }

        required_columns = {
            "id", "address", "latitude", "longitude"
        }

        missing = required_columns - columns

        if missing:
            raise RuntimeError(
                f"Missing required columns: {sorted(missing)}"
            )

        # Add optional geocoding audit columns if needed.
        for column in ("geocoded_address", "geocode_source"):
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE public_facilities "
                    f"ADD COLUMN {column} TEXT"
                )

        # Only process rows with missing coordinates.
        rows = connection.execute("""
            SELECT id, name, address
            FROM public_facilities
            WHERE latitude IS NULL
               OR longitude IS NULL
            ORDER BY id
        """).fetchall()

        print(f"Database: {DB_PATH}")
        print(f"Facilities missing coordinates: {len(rows)}")

        successful = 0
        unsuccessful = 0

        for facility_id, name, address in rows:
            if not address or not address.strip():
                print(f"SKIPPED: {name} has no address")
                unsuccessful += 1
                continue

            latitude, longitude, matched_address = (
                geocode_address(address)
            )

            if latitude is None or longitude is None:
                print(f"NO MATCH: {name} | {address}")
                unsuccessful += 1
                continue

            # Save coordinates to the existing facility record.
            connection.execute("""
                UPDATE public_facilities
                SET latitude = ?,
                    longitude = ?,
                    geocoded_address = ?,
                    geocode_source = ?
                WHERE id = ?
            """, (
                latitude,
                longitude,
                matched_address,
                "US Census Geocoder",
                facility_id,
            ))

            successful += 1

            print(
                f"OK: {name}\n"
                f"    Latitude: {latitude}\n"
                f"    Longitude: {longitude}\n"
                f"    Matched address: {matched_address}"
            )

            # Avoid sending requests too rapidly.
            time.sleep(0.2)

        # Save the updates to the database.
        connection.commit()

        remaining = connection.execute("""
            SELECT COUNT(*)
            FROM public_facilities
            WHERE latitude IS NULL
               OR longitude IS NULL
        """).fetchone()[0]

        print("\n--- GEOCODING SUMMARY ---")
        print(f"Successfully geocoded: {successful}")
        print(f"Unmatched or skipped: {unsuccessful}")
        print(f"Facilities still missing coordinates: {remaining}")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    populate_coordinates()
