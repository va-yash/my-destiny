"""
vedic_calc.py — Vedic Astrology Calculation Engine
Requires: pip install pyswisseph pytz

Outputs structured D1 / D9 / D10 chart data ready to inject into Claude prompt.
"""

import swisseph as swe
import os
swe.set_ephe_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ephemeris'))
from datetime import datetime
from typing import Optional
import math

# ─── Constants ───────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_ABBR = ["Ar", "Ta", "Ge", "Ca", "Le", "Vi", "Li", "Sc", "Sa", "Cp", "Aq", "Pi"]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun",
    "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

# pyswisseph planet IDs
PLANET_IDS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mars":    swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus":   swe.VENUS,
    "Saturn":  swe.SATURN,
    "Rahu":    swe.MEAN_NODE,
}

# Debilitation sign indices (0 = Aries)
DEBILITATION_SIGN = {
    "Sun":     6,   # Libra
    "Moon":    7,   # Scorpio
    "Mars":    3,   # Cancer
    "Mercury": 11,  # Pisces
    "Jupiter": 9,   # Capricorn
    "Venus":   5,   # Virgo
    "Saturn":  0,   # Aries
    "Rahu":    7,   # Scorpio (Vaidik tradition)
    "Ketu":    1,   # Taurus
}

# Exaltation sign indices
EXALTATION_SIGN = {
    "Sun":     0,   # Aries
    "Moon":    1,   # Taurus
    "Mars":    9,   # Capricorn
    "Mercury": 5,   # Virgo
    "Jupiter": 3,   # Cancer
    "Venus":   11,  # Pisces
    "Saturn":  6,   # Libra
    "Rahu":    1,   # Taurus
    "Ketu":    7,   # Scorpio
}

# Combust orbs in degrees (from Sun)
COMBUST_ORB = {
    "Moon":    12.0,
    "Mars":    17.0,
    "Mercury": 14.0,   # 12 when retrograde
    "Jupiter": 11.0,
    "Venus":   10.0,   # 8 when retrograde
    "Saturn":  15.0,
}

# Navamsa starting sign by element group
NAVAMSA_START = {
    "fire":  0,   # Aries  — for Aries, Leo, Sagittarius
    "earth": 9,   # Capricorn — for Taurus, Virgo, Capricorn
    "air":   6,   # Libra  — for Gemini, Libra, Aquarius
    "water": 3,   # Cancer — for Cancer, Scorpio, Pisces
}
SIGN_ELEMENT = [
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water"
]


# ─── Utility functions ────────────────────────────────────────────────────────

def angular_diff(lon1: float, lon2: float) -> float:
    """Smallest angular distance between two longitudes (0–180)."""
    diff = abs(lon1 - lon2) % 360
    return min(diff, 360 - diff)


def to_jd(dt_utc: datetime) -> float:
    """Convert UTC datetime to Julian Day Number."""
    return swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )


def sidereal_longitude(jd: float, planet_id: int) -> tuple[float, float]:
    """
    Return (sidereal_longitude, speed) for a planet using Lahiri ayanamsha.
    Speed < 0 means retrograde.
    """
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0], result[3]  # longitude, speed


def get_nakshatra_info(lon: float) -> tuple[str, int, str]:
    """Return (nakshatra_name, pada, nakshatra_lord) for a sidereal longitude."""
    nak_size = 360 / 27          # 13.333...°
    pada_size = nak_size / 4     # 3.333...°
    idx = int(lon / nak_size) % 27
    pada = int((lon % nak_size) / pada_size) + 1
    return NAKSHATRAS[idx], pada, NAKSHATRA_LORDS[idx]


def get_sign_and_degree(lon: float) -> tuple[int, str, float]:
    """Return (sign_index, sign_name, degrees_within_sign)."""
    lon = lon % 360
    sign_idx = int(lon / 30)
    deg_in_sign = lon % 30
    return sign_idx, SIGNS[sign_idx], deg_in_sign


# ─── Divisional chart calculations ───────────────────────────────────────────

def navamsa_sign(lon: float) -> tuple[int, str]:
    """D9 — Navamsa sign from sidereal longitude."""
    sign_idx = int(lon / 30) % 12
    pos_in_sign = lon % 30
    nav_idx = int(pos_in_sign / (10.0 / 3.0))   # 3°20' = 10/3 degrees each
    element = SIGN_ELEMENT[sign_idx]
    start = NAVAMSA_START[element]
    d9_sign = (start + nav_idx) % 12
    return d9_sign, SIGNS[d9_sign]


def dasamsa_sign(lon: float) -> tuple[int, str]:
    """D10 — Dasamsa sign from sidereal longitude."""
    sign_idx = int(lon / 30) % 12
    pos_in_sign = lon % 30
    part = int(pos_in_sign / 3)   # 3° per part, 10 parts
    # Odd signs (0-indexed even): start from same sign
    # Even signs (0-indexed odd): start from 9th sign
    if sign_idx % 2 == 0:
        d10_sign = (sign_idx + part) % 12
    else:
        d10_sign = (sign_idx + 8 + part) % 12
    return d10_sign, SIGNS[d10_sign]


def whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    """Whole Sign house number (1–12)."""
    return (planet_sign - asc_sign) % 12 + 1


def is_vargottam(d1_sign: int, d9_sign: int) -> bool:
    """Planet is vargottam when D1 and D9 signs are identical."""
    return d1_sign == d9_sign


# ─── Main calculation function ────────────────────────────────────────────────

def calculate_chart(
    dt_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: int = swe.SIDM_LAHIRI
) -> dict:
    """
    Main entry point. Returns full structured chart data.

    Parameters
    ----------
    dt_utc  : Birth datetime in UTC (timezone-naive, assumed UTC)
    lat     : Birth latitude  (North positive)
    lon     : Birth longitude (East positive)
    ayanamsha: Default Lahiri (swe.SIDM_LAHIRI)

    Returns
    -------
    dict with keys: core_trinity, d1, d9, d10
    """
    swe.set_sid_mode(ayanamsha)
    jd = to_jd(dt_utc)

    # ── Ascendant ──────────────────────────────────────────────────────────
    swe.set_sid_mode(ayanamsha)
    houses_data = swe.houses_ex(jd, lat, lon, b"W")   # Whole Sign = "W"
    # houses_ex returns (cusps_tuple, ascmc_tuple)
    # ascmc[0] = Ascendant (tropical), need to subtract ayanamsha
    ayanamsha_val = swe.get_ayanamsa_ut(jd)
    asc_tropical = houses_data[1][0]
    asc_sidereal = (asc_tropical - ayanamsha_val) % 360
    asc_sign_idx, asc_sign_name, asc_deg = get_sign_and_degree(asc_sidereal)
    asc_nak, asc_pada, asc_nak_lord = get_nakshatra_info(asc_sidereal)

    # ── Collect raw planet data ────────────────────────────────────────────
    raw = {}
    sun_lon = None

    for name, pid in PLANET_IDS.items():
        sid_lon, speed = sidereal_longitude(jd, pid)
        sid_lon = sid_lon % 360
        raw[name] = {"lon": sid_lon, "speed": speed}
        if name == "Sun":
            sun_lon = sid_lon

    # Ketu = Rahu + 180°
    raw["Ketu"] = {"lon": (raw["Rahu"]["lon"] + 180) % 360, "speed": raw["Rahu"]["speed"]}

    # ── Build D1 data ──────────────────────────────────────────────────────
    planets_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    d1 = {}
    d9 = {}
    d10 = {}

    for name in planets_order:
        lon_val = raw[name]["lon"]
        speed   = raw[name]["speed"]

        sign_idx, sign_name, deg_in_sign = get_sign_and_degree(lon_val)
        nak_name, pada, nak_lord = get_nakshatra_info(lon_val)
        house = whole_sign_house(sign_idx, asc_sign_idx)

        # Retrograde (Rahu/Ketu are always retrograde by mean node convention)
        retro = (speed < 0) if name not in ("Rahu", "Ketu") else True

        # Combust
        if name not in ("Sun", "Rahu", "Ketu"):
            orb = COMBUST_ORB.get(name, 0)
            if name == "Mercury" and retro:
                orb = 12.0
            if name == "Venus" and retro:
                orb = 8.0
            combust = angular_diff(lon_val, sun_lon) <= orb
        else:
            combust = False

        # Debilitated
        debilitated = DEBILITATION_SIGN.get(name) == sign_idx

        # Exalted
        exalted = EXALTATION_SIGN.get(name) == sign_idx

        # Navamsa
        d9_sign_idx, d9_sign_name = navamsa_sign(lon_val)
        d9_house = whole_sign_house(d9_sign_idx, asc_sign_idx)

        # Vargottam
        vargottam = is_vargottam(sign_idx, d9_sign_idx)

        # Dasamsa
        d10_sign_idx, d10_sign_name = dasamsa_sign(lon_val)
        d10_house = whole_sign_house(d10_sign_idx, asc_sign_idx)

        d1[name] = {
            "sign":        sign_name,
            "sign_idx":    sign_idx,
            "house":       house,
            "degrees":     round(deg_in_sign, 2),
            "nakshatra":   nak_name,
            "pada":        pada,
            "nak_lord":    nak_lord,
            "retrograde":  retro,
            "combust":     combust,
            "debilitated": debilitated,
            "exalted":     exalted,
            "vargottam":   vargottam,
        }

        d9[name] = {
            "sign":     d9_sign_name,
            "sign_idx": d9_sign_idx,
            "house":    d9_house,
        }

        d10[name] = {
            "sign":     d10_sign_name,
            "sign_idx": d10_sign_idx,
            "house":    d10_house,
        }

    # ── Core Trinity ──────────────────────────────────────────────────────
    moon_nak, moon_pada, moon_nak_lord = get_nakshatra_info(raw["Moon"]["lon"])
    sun_sign_idx, sun_sign, _ = get_sign_and_degree(raw["Sun"]["lon"])
    moon_sign_idx, moon_sign, _ = get_sign_and_degree(raw["Moon"]["lon"])

    core_trinity = {
        "ascendant": {
            "sign":      asc_sign_name,
            "degrees":   round(asc_deg, 2),
            "nakshatra": asc_nak,
            "pada":      asc_pada,
        },
        "sun": {
            "sign":      sun_sign,
            "house":     d1["Sun"]["house"],
            "nakshatra": d1["Sun"]["nakshatra"],
            "pada":      d1["Sun"]["pada"],
        },
        "moon": {
            "sign":      moon_sign,
            "house":     d1["Moon"]["house"],
            "nakshatra": moon_nak,
            "pada":      moon_pada,
            "nak_lord":  moon_nak_lord,
        },
    }

    return {
        "meta": {
            "ayanamsha_val":  round(ayanamsha_val, 4),
            "ayanamsha_type": "Lahiri",
            "jd":             round(jd, 4),
        },
        "core_trinity": core_trinity,
        "d1":           d1,
        "d9":           d9,
        "d10":          d10,
    }


# ─── Formatter: convert dict → readable text block for Claude ─────────────────

def _flags(p: dict) -> str:
    """Build a concise flag string like 'Retrograde | Combust | Vargottam'."""
    flags = []
    if p.get("retrograde"):   flags.append("Retrograde")
    if p.get("combust"):      flags.append("Combust")
    if p.get("debilitated"):  flags.append("Debilitated")
    if p.get("exalted"):      flags.append("Exalted")
    if p.get("vargottam"):    flags.append("Vargottam")
    return " | ".join(flags) if flags else "—"


def format_for_prompt(chart: dict) -> str:
    """
    Render chart dict into the exact structured text block
    to be injected into the Claude system prompt.
    """
    ct  = chart["core_trinity"]
    d1  = chart["d1"]
    d9  = chart["d9"]
    d10 = chart["d10"]

    lines = []

    # ── Core Trinity ──────────────────────────────────────────────────────
    lines.append("THE CORE TRINITY")
    asc = ct["ascendant"]
    lines.append(f"Ascendant (Mask): {asc['sign']} {asc['degrees']:.1f}° | Nakshatra: {asc['nakshatra']} Pada {asc['pada']}")
    moon = ct["moon"]
    lines.append(f"Nakshatra (Star): {moon['nakshatra']} Pada {moon['pada']} (Lord: {moon['nak_lord']})")
    sun  = ct["sun"]
    lines.append(f"Sun  (Ego):       {sun['sign']} | House {sun['house']} | {sun['nakshatra']} Pada {sun['pada']}")
    lines.append(f"Moon (Soul):      {moon['sign']} | House {moon['house']} | {moon['nakshatra']} Pada {moon['pada']}")

    lines.append("━" * 40)

    # ── D1 ────────────────────────────────────────────────────────────────
    lines.append("D1 PLACEMENTS — Physical Reality")
    header = f"  {'Planet':<9} {'Sign':<14} {'House':>5} {'Deg':>6} {'Nakshatra':<22} {'Flags'}"
    lines.append(header)
    lines.append("  " + "─" * 80)

    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        p = d1[name]
        flags = _flags(p)
        row = (
            f"  {name:<9} "
            f"{p['sign']:<14} "
            f"{p['house']:>5} "
            f"{p['degrees']:>5.1f}° "
            f"{p['nakshatra'] + ' P' + str(p['pada']):<22} "
            f"{flags}"
        )
        lines.append(row)

    lines.append("")
    lines.append("━" * 40)

    # ── D9 ────────────────────────────────────────────────────────────────
    lines.append("D9 NAVAMSA — Soul's True Path")
    header9 = f"  {'Planet':<9} {'Sign':<14} {'House':>5}"
    lines.append(header9)
    lines.append("  " + "─" * 30)

    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        p = d9[name]
        lines.append(f"  {name:<9} {p['sign']:<14} {p['house']:>5}")

    lines.append("")
    lines.append("━" * 40)

    # ── D10 ───────────────────────────────────────────────────────────────
    lines.append("D10 DASAMSA — Career & Public Life")
    header10 = f"  {'Planet':<9} {'Sign':<14} {'House':>5}"
    lines.append(header10)
    lines.append("  " + "─" * 30)

    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        p = d10[name]
        lines.append(f"  {name:<9} {p['sign']:<14} {p['house']:>5}")

    return "\n".join(lines)


# ─── FastAPI route example ────────────────────────────────────────────────────
# In your main.py:
#
# from vedic_calc import calculate_chart, format_for_prompt
# from datetime import datetime, timezone
#
# @app.post("/chart")
# async def get_chart(birth: BirthInput):
#     dt_utc = birth.local_dt.astimezone(timezone.utc).replace(tzinfo=None)
#     chart  = calculate_chart(dt_utc, birth.lat, birth.lng)
#     text   = format_for_prompt(chart)
#     return {"chart_text": text, "chart_data": chart}


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with a known chart: Jan 1 1990, 12:00 UTC, Mumbai (18.96N, 72.82E)
    test_dt = datetime(1990, 1, 1, 6, 30, 0)   # 12:00 IST = 06:30 UTC
    chart = calculate_chart(test_dt, lat=18.9667, lon=72.8333)

    print(format_for_prompt(chart))
    print("\n\nRaw JSON keys:", list(chart.keys()))
