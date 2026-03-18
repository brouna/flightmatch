"""Airport coordinate lookup and distance utilities."""
import csv
import os
from functools import lru_cache
from typing import Optional

from geopy.distance import great_circle

# OurAirports dataset — downloaded at startup if missing
AIRPORTS_CSV = os.path.join(os.path.dirname(__file__), "../../data/airports.csv")

# Embedded minimal dataset of common ICAO codes for testing / fallback
_BUILTIN: dict[str, tuple[float, float]] = {
    "KATL": (33.6367, -84.4281),
    "KORD": (41.9742, -87.9073),
    "KLAX": (33.9425, -118.4081),
    "KJFK": (40.6398, -73.7789),
    "KDFW": (32.8998, -97.0403),
    "KDEN": (39.8561, -104.6737),
    "KSFO": (37.6213, -122.379),
    "KMDW": (41.7860, -87.7524),
    "KBOS": (42.3643, -71.0052),
    "KIAD": (38.9531, -77.4565),
    "KMSP": (44.8848, -93.2223),
    "KDTW": (42.2124, -83.3534),
    "KPHX": (33.4373, -112.0078),
    "KSEA": (47.4502, -122.3088),
    "KPHL": (39.8719, -75.2411),
    "KLAS": (36.0840, -115.1537),
    "KCLT": (35.2140, -80.9431),
    "KMCO": (28.4294, -81.3089),
    "KFLL": (26.0726, -80.1527),
    "KMIA": (25.7959, -80.2870),
    "KMKE": (42.9472, -87.8966),
    "KRIC": (37.5052, -77.3197),
    "KBWI": (39.1754, -76.6682),
    "KCVG": (39.0488, -84.6678),
    "KPIT": (40.4915, -80.2329),
    "KSTL": (38.7487, -90.3700),
    "KCLE": (41.4117, -81.8498),
    "KSNA": (33.6757, -117.8682),
    "KSLC": (40.7884, -111.9778),
    "KRDU": (35.8801, -78.7880),
}


@lru_cache(maxsize=None)
def _load_airports() -> dict[str, tuple[float, float]]:
    airports: dict[str, tuple[float, float]] = dict(_BUILTIN)
    try:
        with open(AIRPORTS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                icao = (row.get("ident") or "").strip().upper()
                if len(icao) == 4 and icao.startswith("K") or len(icao) == 4:
                    try:
                        lat = float(row["latitude_deg"])
                        lon = float(row["longitude_deg"])
                        airports[icao] = (lat, lon)
                    except (KeyError, ValueError):
                        pass
    except FileNotFoundError:
        pass  # Use builtin fallback
    return airports


def get_airport_coords(icao: str) -> Optional[tuple[float, float]]:
    """Return (lat, lon) for an ICAO code, or None if unknown."""
    return _load_airports().get(icao.upper())


def airport_distance_nm(icao1: str, icao2: str) -> Optional[float]:
    """Straight-line distance in nautical miles between two ICAO airports."""
    c1 = get_airport_coords(icao1)
    c2 = get_airport_coords(icao2)
    if c1 is None or c2 is None:
        return None
    km = great_circle(c1, c2).km
    return km * 0.539957  # km → nm
