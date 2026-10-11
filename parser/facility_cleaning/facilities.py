"""
Closure Call: Facility registration, geocoding, and SQLite storage.

Features:
- Register, search, retrieve, update, and delete facilities
- Geocode US addresses with the Census Geocoder
- Track permanent and temporary facility status
- Record status changes for auditing
- Track status sources and verification timestamps
- Detect stale or expired status information
- Migrate existing facilities.db databases without deleting records
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

import requests


CENSUS_GEOCODER_URL = (
    "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
)

DEFAULT_DATABASE_PATH = os.getenv(
    "FACILITIES_DATABASE",
    "/parser/facilities.db",
)

OPERATING_STATUSES = {
    "normal",
    "delayed_opening",
    "early_dismissal",
    "telework",
    "temporarily_closed",
    "unknown",
}

PERMANENT_STATUSES = {
    "open",
    "permanently_closed",
    "relocated",
    "unknown",
}

BOOLEAN_FIELDS = {
    "telework_available",
    "essential_staff_required",
    "transportation_support_needed",
    "accessibility_support_needed",
}


def current_timestamp():
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ==================================================
# GEOCODING
# ==================================================

def geocode_address(address, timeout=20):
    """
    Convert a US street address to latitude, longitude,
    and the matched address returned by the Census Geocoder.
    """
    response = requests.get(
        CENSUS_GEOCODER_URL,
        params={
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        },
        timeout=timeout,
    )
    response.raise_for_status()

    matches = (
        response.json()
        .get("result", {})
        .get("addressMatches", [])
    )

    if not matches:
        raise ValueError(
            "Address not found. Check the street address, city, "
            "state, and ZIP code."
        )

    match = matches[0]
    coordinates = match.get("coordinates", {})

    if "x" not in coordinates or "y" not in coordinates:
        raise ValueError("The geocoder returned no coordinates.")

    # Census Geocoder: x is longitude and y is latitude.
    latitude = float(coordinates["y"])
    longitude = float(coordinates["x"])
    matched_address = match.get("matchedAddress", address)

    return latitude, longitude, matched_address


# ==================================================
# FACILITY DATABASE
# ==================================================

class FacilityStore:
    """Create, search, retrieve, update, and delete facilities."""

    def __init__(self, database_path=DEFAULT_DATABASE_PATH):
        self.database_path = database_path
        self._initialize_database()
        self._migrate_database()

    def _connect(self):
        """Open a SQLite connection with foreign keys enabled."""
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_database(self):
        """Create the facilities table if it does not exist."""

        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS facilities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    opening_time TEXT NOT NULL,
                    closing_time TEXT NOT NULL,
                    telework_available INTEGER NOT NULL DEFAULT 0,
                    essential_staff_required INTEGER NOT NULL DEFAULT 0,
                    transportation_support_needed INTEGER NOT NULL DEFAULT 0,
                    accessibility_support_needed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,

                    permanent_status TEXT NOT NULL DEFAULT 'unknown',
                    operating_status TEXT NOT NULL DEFAULT 'unknown',

                    status_source TEXT,
                    status_source_url TEXT,
                    status_verified_at TEXT,
                    status_expires_at TEXT,

                    updated_at TEXT
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS facility_status_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id TEXT NOT NULL,

                    previous_status TEXT,
                    new_status TEXT NOT NULL,

                    previous_permanent_status TEXT,
                    new_permanent_status TEXT,

                    reason TEXT,
                    source TEXT,
                    source_url TEXT,
                    changed_by TEXT,
                    recorded_at TEXT NOT NULL,

                    FOREIGN KEY (facility_id)
                        REFERENCES facilities(id)
                        ON DELETE CASCADE
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_name
                ON facilities(name)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_operating_status
                ON facilities(operating_status)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_facility_permanent_status
                ON facilities(permanent_status)
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_history_facility
                ON facility_status_history(facility_id, recorded_at)
            """)

    def _migrate_database(self):
        """
        Add status-tracking columns to an older facilities table.

        Existing facility records are preserved. New status fields
        default to 'unknown' until they are verified.
        """

        new_columns = {
            "permanent_status":
                "TEXT NOT NULL DEFAULT 'unknown'",
            "operating_status":
                "TEXT NOT NULL DEFAULT 'unknown'",
            "status_source": "TEXT",
            "status_source_url": "TEXT",
            "status_verified_at": "TEXT",
            "status_expires_at": "TEXT",
            "updated_at": "TEXT",
        }

        with self._connect() as connection:
            existing_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(facilities)"
                ).fetchall()
            }

            for column_name, column_type in new_columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE facilities "
                        f"ADD COLUMN {column_name} {column_type}"
                    )

            connection.execute("""
                UPDATE facilities
                SET updated_at = created_at
                WHERE updated_at IS NULL
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS facility_status_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facility_id TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT NOT NULL,
                    previous_permanent_status TEXT,
                    new_permanent_status TEXT,
                    reason TEXT,
                    source TEXT,
                    source_url TEXT,
                    changed_by TEXT,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (facility_id)
                        REFERENCES facilities(id)
                        ON DELETE CASCADE
                )
            """)

    # ----------------------------------------------
    # Add and retrieve facilities
    # ----------------------------------------------

    def add(self, facility):
        """Save a facility dictionary to SQLite."""

        required_fields = [
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "opening_time",
            "closing_time",
            "telework_available",
            "essential_staff_required",
            "transportation_support_needed",
            "accessibility_support_needed",
        ]

        missing = [
            field for field in required_fields
            if field not in facility
        ]

        if missing:
            raise ValueError(
                f"Missing required fields: {', '.join(missing)}"
            )

        if not str(facility["name"]).strip():
            raise ValueError("Facility name cannot be empty.")

        if not str(facility["address"]).strip():
            raise ValueError("Facility address cannot be empty.")

        latitude = float(facility["latitude"])
        longitude = float(facility["longitude"])

        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        timestamp = current_timestamp()

        with self._connect() as connection:
            connection.execute("""
                INSERT INTO facilities (
                    id, name, address, latitude, longitude,
                    opening_time, closing_time,
                    telework_available, essential_staff_required,
                    transportation_support_needed,
                    accessibility_support_needed,
                    created_at, permanent_status, operating_status,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(facility["id"]),
                str(facility["name"]).strip(),
                str(facility["address"]).strip(),
                latitude,
                longitude,
                facility["opening_time"],
                facility["closing_time"],
                int(bool(facility["telework_available"])),
                int(bool(facility["essential_staff_required"])),
                int(bool(facility["transportation_support_needed"])),
                int(bool(facility["accessibility_support_needed"])),
                timestamp,
                "unknown",
                "unknown",
                timestamp,
            ))

            connection.execute("""
                INSERT INTO facility_status_history (
                    facility_id,
                    previous_status,
                    new_status,
                    previous_permanent_status,
                    new_permanent_status,
                    reason,
                    source,
                    changed_by,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(facility["id"]),
                None,
                "unknown",
                None,
                "unknown",
                "Facility registered; status requires verification.",
                "system",
                "system",
                timestamp,
            ))

    def get(self, facility_id):
        """Retrieve one facility by ID, or return None."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM facilities WHERE id = ?",
                (str(facility_id),),
            ).fetchone()

        return self._row_to_dict(row) if row else None

    def all(self, include_permanently_closed=True):
        """Return facilities ordered by name."""

        query = "SELECT * FROM facilities"
        parameters = []

        if not include_permanently_closed:
            query += " WHERE permanent_status != ?"
            parameters.append("permanently_closed")

        query += " ORDER BY name"

        with self._connect() as connection:
            rows = connection.execute(
                query, parameters
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def search(self, query, limit=50):
        """Search facility ID, name, or address."""

        query = query.strip()

        if not query:
            return []

        pattern = f"%{query}%"

        with self._connect() as connection:
            rows = connection.execute("""
                SELECT *
                FROM facilities
                WHERE id LIKE ?
                   OR name LIKE ?
                   OR address LIKE ?
                ORDER BY name
                LIMIT ?
            """, (
                pattern,
                pattern,
                pattern,
                int(limit),
            )).fetchall()

        return [self._row_to_dict(row) for row in rows]

    # ----------------------------------------------
    # Update facility profile
    # ----------------------------------------------

    def update(self, facility_id, updates):
        """Update permitted facility profile fields."""

        allowed_fields = {
            "name",
            "address",
            "latitude",
            "longitude",
            "opening_time",
            "closing_time",
            "telework_available",
            "essential_staff_required",
            "transportation_support_needed",
            "accessibility_support_needed",
        }

        changes = {
            key: value
            for key, value in updates.items()
            if key in allowed_fields
        }

        if not changes:
            return False

        if "name" in changes:
            if not str(changes["name"]).strip():
                raise ValueError("Facility name cannot be empty.")
            changes["name"] = str(changes["name"]).strip()

        if "address" in changes:
            if not str(changes["address"]).strip():
                raise ValueError("Facility address cannot be empty.")
            changes["address"] = str(changes["address"]).strip()

        if "latitude" in changes:
            if not -90 <= float(changes["latitude"]) <= 90:
                raise ValueError("Invalid latitude.")
            changes["latitude"] = float(changes["latitude"])

        if "longitude" in changes:
            if not -180 <= float(changes["longitude"]) <= 180:
                raise ValueError("Invalid longitude.")
            changes["longitude"] = float(changes["longitude"])

        for field in BOOLEAN_FIELDS.intersection(changes):
            changes[field] = int(bool(changes[field]))

        changes["updated_at"] = current_timestamp()

        assignments = ", ".join(
            f"{field} = ?" for field in changes
        )

        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE facilities
                SET {assignments}
                WHERE id = ?
                """,
                list(changes.values()) + [str(facility_id)],
            )

        return cursor.rowcount > 0

    def delete(self, facility_id):
        """Delete a facility and its status history."""

        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM facilities WHERE id = ?",
                (str(facility_id),),
            )

        return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row):
        """Convert a SQLite row into a regular dictionary."""

        facility = dict(row)

        for field in BOOLEAN_FIELDS:
            if field in facility:
                facility[field] = bool(facility[field])

        return facility


# ==================================================
# OPERATING-STATUS TRACKING
# ==================================================

def record_status_change(
    store,
    facility_id,
    new_status,
    new_permanent_status=None,
    reason=None,
    source=None,
    source_url=None,
    changed_by=None,
    verified_at=None,
    expires_at=None,
):
    """
    Update a facility's status and preserve a history record.

    new_status:
        normal, delayed_opening, early_dismissal,
        telework, temporarily_closed, unknown

    new_permanent_status:
        open, permanently_closed, relocated, unknown

    A missing new_permanent_status leaves the existing value
    unchanged. Only set a permanent closure or relocation when
    supported by an official source or authorized decision.
    """

    if new_status not in OPERATING_STATUSES:
        raise ValueError(f"Invalid operating status: {new_status}")

    if (
        new_permanent_status is not None
        and new_permanent_status not in PERMANENT_STATUSES
    ):
        raise ValueError(
            f"Invalid permanent status: {new_permanent_status}"
        )

    facility_id = str(facility_id)
    timestamp = current_timestamp()
    verified_at = verified_at or timestamp

    with store._connect() as connection:
        facility = connection.execute("""
            SELECT operating_status, permanent_status
            FROM facilities
            WHERE id = ?
        """, (facility_id,)).fetchone()

        if facility is None:
            raise ValueError(f"Facility not found: {facility_id}")

        previous_status = facility["operating_status"]
        previous_permanent = facility["permanent_status"]

        permanent_status = (
            new_permanent_status
            if new_permanent_status is not None
            else previous_permanent
        )

        connection.execute("""
            UPDATE facilities
            SET operating_status = ?,
                permanent_status = ?,
                status_source = ?,
                status_source_url = ?,
                status_verified_at = ?,
                status_expires_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            permanent_status,
            source,
            source_url,
            verified_at,
            expires_at,
            timestamp,
            facility_id,
        ))

        connection.execute("""
            INSERT INTO facility_status_history (
                facility_id,
                previous_status,
                new_status,
                previous_permanent_status,
                new_permanent_status,
                reason,
                source,
                source_url,
                changed_by,
                recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            facility_id,
            previous_status,
            new_status,
            previous_permanent,
            permanent_status,
            reason,
            source,
            source_url,
            changed_by,
            timestamp,
        ))


def get_status_history(store, facility_id):
    """Return status history from oldest to newest."""

    with store._connect() as connection:
        rows = connection.execute("""
            SELECT *
            FROM facility_status_history
            WHERE facility_id = ?
            ORDER BY recorded_at ASC, history_id ASC
        """, (str(facility_id),)).fetchall()

    return [dict(row) for row in rows]


def is_status_stale(store, facility_id, max_age_hours=24):
    """
    Return True when status is unverified, expired, or too old.

    A stale status does NOT mean a facility is closed. It means
    its status needs verification.
    """

    facility = store.get(facility_id)

    if facility is None:
        raise ValueError(f"Facility not found: {facility_id}")

    verified_at = facility.get("status_verified_at")

    if not verified_at:
        return True

    try:
        verified_time = datetime.fromisoformat(verified_at)

        if verified_time.tzinfo is None:
            verified_time = verified_time.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(timezone.utc)

        if now - verified_time > timedelta(hours=max_age_hours):
            return True

        expires_at = facility.get("status_expires_at")

        if expires_at:
            expiration_time = datetime.fromisoformat(expires_at)

            if expiration_time.tzinfo is None:
                expiration_time = expiration_time.replace(
                    tzinfo=timezone.utc
                )

            if now >= expiration_time:
                return True

    except (ValueError, TypeError):
        return True

    return False


# ==================================================
# REGISTRATION PROMPTS
# ==================================================

def ask_yes_no(prompt, default=False):
    """Prompt for yes/no input with a default."""

    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(prompt + suffix).strip().lower()

    if not answer:
        return default

    if answer in ("y", "yes"):
        return True

    if answer in ("n", "no"):
        return False

    print("Please enter yes or no.")
    return ask_yes_no(prompt, default)


def prompt_time(label, default):
    """Prompt for a valid 24-hour time in HH:MM format."""

    while True:
        value = input(
            f"{label} [{default}]: "
        ).strip() or default

        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError:
            print("Enter a time like 08:00 or 17:30.")


def register_facility(store):
    """Collect, geocode, and save a new facility."""

    print("\nRegister a facility")

    name = input("Facility name: ").strip()

    if not name:
        raise ValueError("Facility name cannot be empty.")

    address = input("Full US street address: ").strip()

    if not address:
        raise ValueError("Facility address cannot be empty.")

    print("Geocoding address...")

    latitude, longitude, matched_address = geocode_address(
        address
    )

    print(f"Matched address: {matched_address}")

    if not ask_yes_no("Use this address match?", default=True):
        raise ValueError(
            "Please restart registration with a corrected address."
        )

    facility_id = input(
        "Facility ID (press Enter to generate one): "
    ).strip()

    if not facility_id:
        facility_id = str(uuid.uuid4())

    facility = {
        "id": facility_id,
        "name": name,
        "address": matched_address,
        "latitude": latitude,
        "longitude": longitude,
        "opening_time": prompt_time(
            "Normal opening time", "08:00"
        ),
        "closing_time": prompt_time(
            "Normal closing time", "17:00"
        ),
        "telework_available": ask_yes_no(
            "Can eligible employees telework?",
            default=False,
        ),
        "essential_staff_required": ask_yes_no(
            "Are essential on-site staff required?",
            default=True,
        ),
        "transportation_support_needed": ask_yes_no(
            "Do employees rely on facility-provided transportation?",
            default=False,
        ),
        "accessibility_support_needed": ask_yes_no(
            "Are accessibility accommodations relevant to closure planning?",
            default=False,
        ),
    }

    store.add(facility)

    print(f"\nSaved facility: {name} (ID: {facility_id})")
    print("Operating status remains unknown until verified.")

    return facility


# ==================================================
# OPTIONAL COMMAND-LINE ENTRY POINT
# ==================================================

if __name__ == "__main__":
    store = FacilityStore()

    print("Closure Call facility database is ready.")
    print(f"Database: {os.path.abspath(store.database_path)}")

    while True:
        print("\n1. Register a facility")
        print("2. List facilities")
        print("3. Search facilities")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                register_facility(store)

            elif choice == "2":
                facilities = store.all()

                if not facilities:
                    print("No facilities registered.")
                else:
                    for facility in facilities:
                        print(
                            f"{facility['name']} | "
                            f"ID: {facility['id']} | "
                            f"Operating status: "
                            f"{facility['operating_status']} | "
                            f"Permanent status: "
                            f"{facility['permanent_status']}"
                        )

            elif choice == "3":
                query = input("Search name, ID, or address: ")
                results = store.search(query)

                if not results:
                    print("No matching facilities.")
                else:
                    for facility in results:
                        print(
                            f"{facility['name']} | "
                            f"{facility['address']} | "
                            f"ID: {facility['id']}"
                        )

            elif choice == "4":
                print("Goodbye.")
                break

            else:
                print("Choose 1, 2, 3, or 4.")

        except (ValueError, requests.RequestException,
                sqlite3.Error) as error:
            print(f"Error: {error}")