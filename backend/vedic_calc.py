"""
vedic_calc.py — Vedic Astrology Calculation Engine
Requires: pip install pyswisseph pytz

Outputs structured D1–D60 divisional chart data ready to inject into Claude prompt.

CHANGELOG
─────────
v2.0
  • BUG FIX: Each divisional chart (D2–D60) now uses its OWN ascendant
    for house calculation, derived by applying the same divisional formula
    to the D1 ascendant longitude.  Previously all charts incorrectly
    used the D1 (Rasi) ascendant sign, producing wrong house numbers.
  • Added full divisional chart suite: D2 D3 D4 D5 D6 D7 D8 D9 D10
    D11 D12 D16 D20 D24 D27 D30 D40 D45 D60
  • format_for_prompt() now outputs all divisional charts.
  • calculate_chart() returns keys for every chart plus divisional
    ascendant indices stored under  "<key>_asc"  (e.g. "d9_asc").
"""

import swisseph as swe
import os
swe.set_ephe_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ephemeris'))
from datetime import datetime
from typing import Optional
import math

# ─── Constants ────────────────────────────────────────────────────────────────

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

PLANETS_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

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

# Navamsa (D9) starting sign by element group
NAVAMSA_START = {
    "fire":  0,   # Aries     — for Aries, Leo, Sagittarius
    "earth": 9,   # Capricorn — for Taurus, Virgo, Capricorn
    "air":   6,   # Libra     — for Gemini, Libra, Aquarius
    "water": 3,   # Cancer    — for Cancer, Scorpio, Pisces
}

# Element of each sign (0-indexed)
SIGN_ELEMENT = [
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water"
]

# Modality: 0 = movable/cardinal, 1 = fixed, 2 = mutable/dual
SIGN_MODALITY = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]

# ── D5 Panchamsa fixed sign sequences (Parashari standard) ───────────────────
# Odd signs  (sign_idx % 2 == 0): Aries, Aquarius, Sagittarius, Gemini, Libra
D5_ODD_SIGNS  = [0, 10, 8, 2, 6]
# Even signs (sign_idx % 2 == 1): Taurus, Virgo, Capricorn, Pisces, Scorpio
D5_EVEN_SIGNS = [1, 5, 9, 11, 7]

# ── D30 Trimshamsa: unequal divisions (Parashari standard) ───────────────────
# Odd signs:  Mars→Aries(0-5°), Saturn→Aquarius(5-10°), Jupiter→Sagittarius(10-18°),
#             Mercury→Gemini(18-25°), Venus→Libra(25-30°)
D30_ODD_BOUNDS = [5, 10, 18, 25, 30]
D30_ODD_SIGNS  = [0, 10, 8, 2, 6]      # Aries, Aquarius, Sagittarius, Gemini, Libra

# Even signs: Venus→Taurus(0-5°), Mercury→Virgo(5-12°), Jupiter→Pisces(12-20°),
#             Saturn→Capricorn(20-25°), Mars→Scorpio(25-30°)
D30_EVEN_BOUNDS = [5, 12, 20, 25, 30]
D30_EVEN_SIGNS  = [1, 5, 11, 9, 7]     # Taurus, Virgo, Pisces, Capricorn, Scorpio


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
    nak_size  = 360 / 27        # 13.333...°
    pada_size = nak_size / 4    # 3.333...°
    idx  = int(lon / nak_size) % 27
    pada = int((lon % nak_size) / pada_size) + 1
    return NAKSHATRAS[idx], pada, NAKSHATRA_LORDS[idx]


def get_sign_and_degree(lon: float) -> tuple[int, str, float]:
    """Return (sign_index, sign_name, degrees_within_sign)."""
    lon      = lon % 360
    sign_idx = int(lon / 30)
    deg      = lon % 30
    return sign_idx, SIGNS[sign_idx], deg


def whole_sign_house(planet_sign: int, asc_sign: int) -> int:
    """Whole Sign house number (1–12)."""
    return (planet_sign - asc_sign) % 12 + 1


def is_vargottam(d1_sign: int, d9_sign: int) -> bool:
    """Planet is vargottam when D1 and D9 signs are identical."""
    return d1_sign == d9_sign


# ─── Divisional chart sign functions ─────────────────────────────────────────
# Every function returns (sign_index: int, sign_name: str).
# Input: sidereal longitude in degrees (0–360).

def d1_sign(lon: float) -> tuple[int, str]:
    """D1 — Rasi (natal chart). Direct placement."""
    idx = int(lon / 30) % 12
    return idx, SIGNS[idx]


def hora_sign(lon: float) -> tuple[int, str]:
    """
    D2 — Hora.
    Odd signs  (Ar, Ge, Le, Li, Sg, Aq):  0-15° → Leo,    15-30° → Cancer
    Even signs (Ta, Ca, Vi, Sc, Cp, Pi):  0-15° → Cancer, 15-30° → Leo
    """
    sign_idx = int(lon / 30) % 12
    pos      = lon % 30
    if sign_idx % 2 == 0:               # odd sign (1st, 3rd, 5th …)
        d2 = 4 if pos < 15 else 3       # Leo (Sun hora) → Cancer (Moon hora)
    else:                               # even sign
        d2 = 3 if pos < 15 else 4       # Cancer → Leo
    return d2, SIGNS[d2]


def drekkana_sign(lon: float) -> tuple[int, str]:
    """
    D3 — Drekkana. Three equal parts of 10° each.
    Part 1 (0-10°):   same sign
    Part 2 (10-20°):  5th from same sign  (+4)
    Part 3 (20-30°):  9th from same sign  (+8)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 10)                # 0, 1, 2
    d3   = (sign_idx + part * 4) % 12
    return d3, SIGNS[d3]


def chaturthamsa_sign(lon: float) -> tuple[int, str]:
    """
    D4 — Chaturthamsa. Four equal parts of 7°30' each.
    Part 1 (0–7.5°):    same sign
    Part 2 (7.5–15°):   4th sign  (+3)
    Part 3 (15–22.5°):  7th sign  (+6)
    Part 4 (22.5–30°):  10th sign (+9)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 7.5)              # 0, 1, 2, 3
    d4   = (sign_idx + part * 3) % 12
    return d4, SIGNS[d4]


def panchamsa_sign(lon: float) -> tuple[int, str]:
    """
    D5 — Panchamsa. Five equal parts of 6° each.
    Odd  signs: Aries(0), Aquarius(10), Sagittarius(8), Gemini(2), Libra(6)
    Even signs: Taurus(1), Virgo(5), Capricorn(9), Pisces(11), Scorpio(7)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 6)                # 0-4
    if sign_idx % 2 == 0:
        d5 = D5_ODD_SIGNS[part]
    else:
        d5 = D5_EVEN_SIGNS[part]
    return d5, SIGNS[d5]


def shashthamsa_sign(lon: float) -> tuple[int, str]:
    """
    D6 — Shashthamsa. Six equal parts of 5° each.
    Odd  signs: count from same sign.
    Even signs: count from 7th sign (opposite).
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 5)                # 0-5
    if sign_idx % 2 == 0:
        d6 = (sign_idx + part) % 12
    else:
        d6 = (sign_idx + 6 + part) % 12
    return d6, SIGNS[d6]


def saptamsa_sign(lon: float) -> tuple[int, str]:
    """
    D7 — Saptamsa. Seven equal parts of ~4°17' each.
    Odd  signs: count from same sign.
    Even signs: count from 7th sign.
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / (30 / 7))         # 0-6
    if sign_idx % 2 == 0:
        d7 = (sign_idx + part) % 12
    else:
        d7 = (sign_idx + 6 + part) % 12
    return d7, SIGNS[d7]


def ashtamsa_sign(lon: float) -> tuple[int, str]:
    """
    D8 — Ashtamsa. Eight equal parts of 3°45' each.
    Movable signs (0,3,6,9):  count from same sign.
    Fixed   signs (1,4,7,10): count from 9th sign (+8).
    Dual    signs (2,5,8,11): count from 5th sign (+4).
    """
    sign_idx = int(lon / 30) % 12
    pos      = lon % 30
    part     = int(pos / 3.75)         # 0-7
    mod      = SIGN_MODALITY[sign_idx]
    offsets  = [0, 8, 4]               # movable, fixed, dual
    d8       = (sign_idx + offsets[mod] + part) % 12
    return d8, SIGNS[d8]


def navamsa_sign(lon: float) -> tuple[int, str]:
    """
    D9 — Navamsa. Nine equal parts of 3°20' each.
    Starting sign determined by the D1 sign's element:
        Fire  (Ar, Le, Sg) → Aries  (0)
        Earth (Ta, Vi, Cp) → Capricorn (9)
        Air   (Ge, Li, Aq) → Libra  (6)
        Water (Ca, Sc, Pi) → Cancer (3)
    """
    sign_idx    = int(lon / 30) % 12
    pos         = lon % 30
    nav_idx     = int(pos / (10.0 / 3.0))   # 3°20' = 10/3°
    element     = SIGN_ELEMENT[sign_idx]
    start       = NAVAMSA_START[element]
    d9          = (start + nav_idx) % 12
    return d9, SIGNS[d9]


def dasamsa_sign(lon: float) -> tuple[int, str]:
    """
    D10 — Dasamsa. Ten equal parts of 3° each.
    Odd  signs (sign_idx % 2 == 0): count from same sign.
    Even signs (sign_idx % 2 == 1): count from 9th sign (+8).
    """
    sign_idx = int(lon / 30) % 12
    pos      = lon % 30
    part     = int(pos / 3)            # 0-9
    if sign_idx % 2 == 0:
        d10 = (sign_idx + part) % 12
    else:
        d10 = (sign_idx + 8 + part) % 12
    return d10, SIGNS[d10]


def ekadasamsa_sign(lon: float) -> tuple[int, str]:
    """
    D11 — Ekadasamsa. Eleven equal parts of ~2°44' each.
    Odd  signs: count from same sign.
    Even signs: count from 7th sign.
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / (30 / 11))        # 0-10
    if sign_idx % 2 == 0:
        d11 = (sign_idx + part) % 12
    else:
        d11 = (sign_idx + 6 + part) % 12
    return d11, SIGNS[d11]


def dwadasamsa_sign(lon: float) -> tuple[int, str]:
    """
    D12 — Dwadasamsa. Twelve equal parts of 2°30' each.
    Always count from same sign through all 12 signs.
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 2.5)              # 0-11
    d12  = (sign_idx + part) % 12
    return d12, SIGNS[d12]


def shodasamsa_sign(lon: float) -> tuple[int, str]:
    """
    D16 — Shodasamsa. Sixteen equal parts of 1°52'30\" each.
    Movable signs → from Aries       (0)
    Fixed   signs → from Leo         (4)
    Dual    signs → from Sagittarius (8)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 1.875)            # 0-15
    mod  = SIGN_MODALITY[sign_idx]
    start_signs = [0, 4, 8]           # Aries, Leo, Sagittarius
    d16  = (start_signs[mod] + part) % 12
    return d16, SIGNS[d16]


def vimshamsa_sign(lon: float) -> tuple[int, str]:
    """
    D20 — Vimshamsa. Twenty equal parts of 1°30' each.
    Movable signs → from Aries       (0)
    Fixed   signs → from Sagittarius (8)
    Dual    signs → from Leo         (4)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 1.5)              # 0-19
    mod  = SIGN_MODALITY[sign_idx]
    start_signs = [0, 8, 4]           # Aries, Sagittarius, Leo
    d20  = (start_signs[mod] + part) % 12
    return d20, SIGNS[d20]


def chaturvimshamsa_sign(lon: float) -> tuple[int, str]:
    """
    D24 — Chaturvimshamsa / Siddhamsa. Twenty-four equal parts of 1°15' each.
    Odd  signs (sign_idx % 2 == 0): count from Leo    (4)
    Even signs (sign_idx % 2 == 1): count from Cancer (3)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 1.25)             # 0-23
    start = 4 if sign_idx % 2 == 0 else 3   # Leo or Cancer
    d24  = (start + part) % 12
    return d24, SIGNS[d24]


def saptavimshamsa_sign(lon: float) -> tuple[int, str]:
    """
    D27 — Saptavimshamsa / Nakshatramsa. Twenty-seven equal parts of ~1°6'40\" each.
    Fire  signs → from Aries      (0)
    Earth signs → from Cancer     (3)
    Air   signs → from Libra      (6)
    Water signs → from Capricorn  (9)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / (10.0 / 9.0))    # 0-26  (10/9° per part)
    elem  = SIGN_ELEMENT[sign_idx]
    starts = {"fire": 0, "earth": 3, "air": 6, "water": 9}
    d27  = (starts[elem] + part) % 12
    return d27, SIGNS[d27]


def trimshamsa_sign(lon: float) -> tuple[int, str]:
    """
    D30 — Trimshamsa. UNEQUAL divisions (Parashari).

    Odd signs:
        Mars    0– 5° → Aries       (0)
        Saturn  5–10° → Aquarius   (10)
        Jupiter 10–18° → Sagittarius(8)
        Mercury 18–25° → Gemini     (2)
        Venus   25–30° → Libra      (6)

    Even signs:
        Venus   0– 5° → Taurus      (1)
        Mercury 5–12° → Virgo       (5)
        Jupiter 12–20° → Pisces    (11)
        Saturn  20–25° → Capricorn  (9)
        Mars    25–30° → Scorpio    (7)
    """
    sign_idx = int(lon / 30) % 12
    pos = lon % 30
    if sign_idx % 2 == 0:   # odd sign
        for i, bound in enumerate(D30_ODD_BOUNDS):
            if pos < bound:
                return D30_ODD_SIGNS[i], SIGNS[D30_ODD_SIGNS[i]]
    else:                   # even sign
        for i, bound in enumerate(D30_EVEN_BOUNDS):
            if pos < bound:
                return D30_EVEN_SIGNS[i], SIGNS[D30_EVEN_SIGNS[i]]
    return sign_idx, SIGNS[sign_idx]   # fallback (pos == 30, edge case)


def khavedamsa_sign(lon: float) -> tuple[int, str]:
    """
    D40 — Khavedamsa. Forty equal parts of 0°45' each.
    Odd  signs: count from Aries (0).
    Even signs: count from Libra (6).
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 0.75)             # 0-39
    start = 0 if sign_idx % 2 == 0 else 6   # Aries or Libra
    d40  = (start + part) % 12
    return d40, SIGNS[d40]


def akshavedamsa_sign(lon: float) -> tuple[int, str]:
    """
    D45 — Akshavedamsa. Forty-five equal parts of 0°40' each.
    Movable signs → from Aries       (0)
    Fixed   signs → from Leo         (4)
    Dual    signs → from Sagittarius (8)
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / (2.0 / 3.0))     # 0-44
    mod  = SIGN_MODALITY[sign_idx]
    start_signs = [0, 4, 8]
    d45  = (start_signs[mod] + part) % 12
    return d45, SIGNS[d45]


def shashtiamsa_sign(lon: float) -> tuple[int, str]:
    """
    D60 — Shashtiamsa. Sixty equal parts of 0°30' each.
    Odd  signs: count from Aries (0).
    Even signs: count from Libra (6).
    """
    sign_idx = int(lon / 30) % 12
    pos  = lon % 30
    part = int(pos / 0.5)              # 0-59
    start = 0 if sign_idx % 2 == 0 else 6   # Aries or Libra
    d60  = (start + part) % 12
    return d60, SIGNS[d60]


# ─── Registry of all divisional charts ───────────────────────────────────────

DIVISIONAL_CHARTS: dict[str, callable] = {
    "d2":  hora_sign,
    "d3":  drekkana_sign,
    "d4":  chaturthamsa_sign,
    "d5":  panchamsa_sign,
    "d6":  shashthamsa_sign,
    "d7":  saptamsa_sign,
    "d8":  ashtamsa_sign,
    "d9":  navamsa_sign,
    "d10": dasamsa_sign,
    "d11": ekadasamsa_sign,
    "d12": dwadasamsa_sign,
    "d16": shodasamsa_sign,
    "d20": vimshamsa_sign,
    "d24": chaturvimshamsa_sign,
    "d27": saptavimshamsa_sign,
    "d30": trimshamsa_sign,
    "d40": khavedamsa_sign,
    "d45": akshavedamsa_sign,
    "d60": shashtiamsa_sign,
}

DIVISIONAL_NAMES: dict[str, str] = {
    "d2":  "Hora",
    "d3":  "Drekkana",
    "d4":  "Chaturthamsa",
    "d5":  "Panchamsa",
    "d6":  "Shashthamsa",
    "d7":  "Saptamsa",
    "d8":  "Ashtamsa",
    "d9":  "Navamsa",
    "d10": "Dasamsa",
    "d11": "Ekadasamsa",
    "d12": "Dwadasamsa",
    "d16": "Shodasamsa",
    "d20": "Vimshamsa",
    "d24": "Chaturvimshamsa",
    "d27": "Saptavimshamsa",
    "d30": "Trimshamsa",
    "d40": "Khavedamsa",
    "d45": "Akshavedamsa",
    "d60": "Shashtiamsa",
}

DIVISIONAL_PURPOSE: dict[str, str] = {
    "d2":  "Wealth & Financial Potential",
    "d3":  "Siblings, Courage & Short Journeys",
    "d4":  "Fortune, Property & Fixed Assets",
    "d5":  "Children, Intelligence & Past-Life Merits",
    "d6":  "Enemies, Debts, Disease & Service",
    "d7":  "Children & Progeny (detailed)",
    "d8":  "Obstacles, Longevity & Hidden Dangers",
    "d9":  "Soul's True Path, Dharma & Marriage",
    "d10": "Career, Status & Public Life",
    "d11": "Gains, Income & Social Network",
    "d12": "Parents & Ancestral Lineage",
    "d16": "Vehicles, Comforts & Happiness",
    "d20": "Spiritual Progress & Upasana",
    "d24": "Education, Learning & Wisdom",
    "d27": "Strength, Vitality & Innate Power",
    "d30": "Misfortunes, Karma & Challenges",
    "d40": "Maternal Legacy & Auspicious Effects",
    "d45": "Paternal Legacy & General Indications",
    "d60": "Past-Life Karma (most granular)",
}


# ─── Main calculation function ────────────────────────────────────────────────

def calculate_chart(
    dt_utc: datetime,
    lat: float,
    lon: float,
    ayanamsha: int = swe.SIDM_LAHIRI
) -> dict:
    """
    Main entry point. Returns full structured chart data (D1 through D60).

    Parameters
    ----------
    dt_utc    : Birth datetime in UTC (timezone-naive, assumed UTC)
    lat       : Birth latitude  (North positive)
    lon       : Birth longitude (East positive)
    ayanamsha : Default Lahiri (swe.SIDM_LAHIRI)

    Returns
    -------
    dict with keys:
        meta, core_trinity, d1,
        d2 … d60  (each divisional chart planet data),
        d2_asc … d60_asc  (each chart's own ascendant sign index)
    """
    swe.set_sid_mode(ayanamsha)
    jd = to_jd(dt_utc)

    # ── Ascendant (D1) ────────────────────────────────────────────────────
    swe.set_sid_mode(ayanamsha)
    houses_data   = swe.houses_ex(jd, lat, lon, b"W")   # Whole Sign
    ayanamsha_val = swe.get_ayanamsa_ut(jd)
    asc_tropical  = houses_data[1][0]
    asc_sidereal  = (asc_tropical - ayanamsha_val) % 360

    asc_sign_idx, asc_sign_name, asc_deg = get_sign_and_degree(asc_sidereal)
    asc_nak, asc_pada, asc_nak_lord      = get_nakshatra_info(asc_sidereal)

    # ── BUG FIX: Compute each divisional chart's OWN ascendant ───────────
    # Each Dx chart has its own rising sign, obtained by applying the same
    # divisional formula to the D1 ascendant longitude.
    # Houses for planets inside Dx are measured from that Dx ascendant.
    div_asc: dict[str, int] = {}
    for key, fn in DIVISIONAL_CHARTS.items():
        div_asc[key], _ = fn(asc_sidereal)

    # ── Collect raw planet data ───────────────────────────────────────────
    raw: dict[str, dict] = {}
    sun_lon: float | None = None

    for name, pid in PLANET_IDS.items():
        sid_lon, speed = sidereal_longitude(jd, pid)
        sid_lon = sid_lon % 360
        raw[name] = {"lon": sid_lon, "speed": speed}
        if name == "Sun":
            sun_lon = sid_lon

    # Ketu = Rahu + 180°
    raw["Ketu"] = {
        "lon":   (raw["Rahu"]["lon"] + 180) % 360,
        "speed": raw["Rahu"]["speed"]
    }

    # ── Build D1 data ─────────────────────────────────────────────────────
    d1: dict[str, dict] = {}

    for name in PLANETS_ORDER:
        lon_val = raw[name]["lon"]
        speed   = raw[name]["speed"]

        sign_idx, sign_name, deg_in_sign = get_sign_and_degree(lon_val)
        nak_name, pada, nak_lord         = get_nakshatra_info(lon_val)
        house = whole_sign_house(sign_idx, asc_sign_idx)

        # Retrograde (Rahu/Ketu always retrograde by mean-node convention)
        retro = (speed < 0) if name not in ("Rahu", "Ketu") else True

        # Combustion
        if name not in ("Sun", "Rahu", "Ketu"):
            orb = COMBUST_ORB.get(name, 0)
            if name == "Mercury" and retro:
                orb = 12.0
            if name == "Venus" and retro:
                orb = 8.0
            combust = angular_diff(lon_val, sun_lon) <= orb
        else:
            combust = False

        debilitated = (DEBILITATION_SIGN.get(name) == sign_idx)
        exalted     = (EXALTATION_SIGN.get(name)   == sign_idx)

        d9_sign_idx, _ = navamsa_sign(lon_val)
        vargottam = is_vargottam(sign_idx, d9_sign_idx)

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

    # ── Build all divisional chart data ──────────────────────────────────
    divisional_data: dict[str, dict[str, dict]] = {}

    for key, fn in DIVISIONAL_CHARTS.items():
        chart_asc = div_asc[key]   # THIS chart's own ascendant sign index
        chart_planets: dict[str, dict] = {}
        for name in PLANETS_ORDER:
            p_sign_idx, p_sign_name = fn(raw[name]["lon"])
            # ✓ House measured from this chart's own ascendant (the fix)
            p_house = whole_sign_house(p_sign_idx, chart_asc)
            chart_planets[name] = {
                "sign":     p_sign_name,
                "sign_idx": p_sign_idx,
                "house":    p_house,
            }
        divisional_data[key] = chart_planets

    # ── Core Trinity ─────────────────────────────────────────────────────
    moon_nak, moon_pada, moon_nak_lord = get_nakshatra_info(raw["Moon"]["lon"])
    _, sun_sign,  _                    = get_sign_and_degree(raw["Sun"]["lon"])
    _, moon_sign, _                    = get_sign_and_degree(raw["Moon"]["lon"])

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

    # ── Assemble result ───────────────────────────────────────────────────
    result: dict = {
        "meta": {
            "ayanamsha_val":  round(ayanamsha_val, 4),
            "ayanamsha_type": "Lahiri",
            "jd":             round(jd, 4),
        },
        "core_trinity": core_trinity,
        "d1":           d1,
    }

    # Divisional charts + their ascendant indices
    for key in DIVISIONAL_CHARTS:
        result[key]              = divisional_data[key]
        result[f"{key}_asc"]     = div_asc[key]          # e.g. "d9_asc" = 6 (Libra)

    return result


# ─── Formatter ────────────────────────────────────────────────────────────────

def _flags(p: dict) -> str:
    """Build a concise flag string, e.g. 'Retrograde | Combust | Vargottam'."""
    parts = []
    if p.get("retrograde"):   parts.append("Retrograde")
    if p.get("combust"):      parts.append("Combust")
    if p.get("debilitated"):  parts.append("Debilitated")
    if p.get("exalted"):      parts.append("Exalted")
    if p.get("vargottam"):    parts.append("Vargottam")
    return " | ".join(parts) if parts else "—"


def format_for_prompt(chart: dict) -> str:
    """
    Render the full chart dict into a structured text block for Claude.
    Includes D1 in full detail, then every divisional chart D2–D60
    with its own ascendant and house numbers.
    """
    ct = chart["core_trinity"]
    d1 = chart["d1"]
    lines: list[str] = []

    # ── Core Trinity ──────────────────────────────────────────────────────
    lines.append("THE CORE TRINITY")
    asc  = ct["ascendant"]
    moon = ct["moon"]
    sun  = ct["sun"]
    lines.append(f"Ascendant (Mask): {asc['sign']} {asc['degrees']:.1f}° | Nakshatra: {asc['nakshatra']} Pada {asc['pada']}")
    lines.append(f"Nakshatra (Star): {moon['nakshatra']} Pada {moon['pada']} (Lord: {moon['nak_lord']})")
    lines.append(f"Sun  (Ego):       {sun['sign']} | House {sun['house']} | {sun['nakshatra']} Pada {sun['pada']}")
    lines.append(f"Moon (Soul):      {moon['sign']} | House {moon['house']} | {moon['nakshatra']} Pada {moon['pada']}")
    lines.append("━" * 60)

    # ── D1 — Full detail ─────────────────────────────────────────────────
    lines.append("D1 RASI — Physical Reality & Life Blueprint")
    lines.append(f"  Ascendant: {ct['ascendant']['sign']}")
    lines.append(f"  {'Planet':<9} {'Sign':<14} {'House':>5} {'Deg':>6} {'Nakshatra':<24} {'Flags'}")
    lines.append("  " + "─" * 85)
    for name in PLANETS_ORDER:
        p = d1[name]
        row = (
            f"  {name:<9} "
            f"{p['sign']:<14} "
            f"{p['house']:>5} "
            f"{p['degrees']:>5.1f}° "
            f"{p['nakshatra'] + ' P' + str(p['pada']):<24} "
            f"{_flags(p)}"
        )
        lines.append(row)

    lines.append("")
    lines.append("━" * 60)

    # ── Divisional charts D2–D60 ──────────────────────────────────────────
    for key in DIVISIONAL_CHARTS:
        num      = key.upper()
        fullname = DIVISIONAL_NAMES[key]
        purpose  = DIVISIONAL_PURPOSE[key]
        asc_idx  = chart.get(f"{key}_asc", 0)
        asc_name = SIGNS[asc_idx]
        planets  = chart[key]

        lines.append(f"{num} {fullname} — {purpose}")
        lines.append(f"  Ascendant: {asc_name}")
        lines.append(f"  {'Planet':<9} {'Sign':<14} {'House':>5}")
        lines.append("  " + "─" * 32)
        for name in PLANETS_ORDER:
            p = planets[name]
            lines.append(f"  {name:<9} {p['sign']:<14} {p['house']:>5}")
        lines.append("")
        lines.append("━" * 60)

    return "\n".join(lines)


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test: Jan 1 1990, 12:00 IST = 06:30 UTC, Mumbai (18.97N, 72.83E)
    test_dt = datetime(1990, 1, 1, 6, 30, 0)
    chart   = calculate_chart(test_dt, lat=18.9667, lon=72.8333)

    print(format_for_prompt(chart))
    print("\nDivisional ascendants:")
    for key in DIVISIONAL_CHARTS:
        asc_idx = chart[f"{key}_asc"]
        print(f"  {key.upper():<4} ASC: {SIGNS[asc_idx]}")
    print("\nAll result keys:", list(chart.keys()))
