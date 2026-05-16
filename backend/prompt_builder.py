"""
prompt_builder.py — Yoga Detection + Vimshottari Dasha + Claude System Prompt Assembly

Depends on: vedic_calc.py
Install:    pip install pyswisseph python-dateutil

Entry point:
    from prompt_builder import build_system_prompt
    system_prompt = build_system_prompt(chart, birth_dt, query_date=datetime.utcnow())

CHANGELOG v4
------------
BUG FIXES
  • detect_extra_charts() now triggers on chart codes ("d7"), chart names
    ("saptamsa"), and bulk/listing queries ("list all charts", "all divisional").
    Previously none of these fired, causing Claude to hallucinate every
    divisional chart when asked about them by name or in bulk.
  • detect_yogas() now reads asc_idx directly from chart["d1_asc"] instead of
    deriving it from Moon sign/house — fragile when sign data is borderline.
  • _CHART_TRIGGERS: removed "career" from D4 (D4 = property, not career);
    removed "vehicle"/"car" from D4 and placed correctly in D16.

TOKEN OPTIMISATIONS (~750 tokens saved vs v3)
  • System prompt separators: === instead of 56-char Unicode box lines (-196 tok)
  • Dasha separators: --- instead of 56-char Unicode lines (-130 tok)
  • FULL VIMSHOTTARI SEQUENCE replaced with compact one-liner (-125 tok)
  • Yoga descriptions capped at 120 chars (-variable, ~100 tok avg)
  • HOW TO ANSWER instructions compressed without losing content (-80 tok)
  • DATA BOUNDARIES guard added (~40 tok) — net saving still ~750 tok

v3 (unchanged)
  • Added NATIVE DETAILS block at top of every system prompt.
  • format_dasha_block() annotates birth-lord MD with balance at birth.
  • Removed full Pratyantar table from prompt (~350 tokens saved).
  • build_system_prompt() accepts optional birth_details dict.
"""

from datetime import datetime, timedelta
from vedic_calc import SIGNS, SIGN_ABBR

# --- Vimshottari Dasha constants ---------------------------------------------

DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

# Nakshatra index (0-26) -> Dasha lord
NAK_DASHA_LORD = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

NAK_SIZE      = 360.0 / 27      # 13.3333...
TOTAL_YEARS   = 120.0
DAYS_PER_YEAR = 365.25          # Julian year — Vedic standard


# --- Core timing function ----------------------------------------------------

def _add_years(dt: datetime, years: float) -> datetime:
    """Add fractional years to a datetime. Uses Julian year (365.25 days)."""
    return dt + timedelta(days=years * DAYS_PER_YEAR)


# --- Dasha computation engine ------------------------------------------------

def _dasha_periods(start_dt: datetime, start_lord_idx: int, parent_years: float,
                   depth: int = 1) -> list[dict]:
    """
    Recursively compute dasha sub-periods.

    Parameters
    ----------
    start_dt        : exact start datetime of this level's first period
    start_lord_idx  : DASHA_ORDER index of the first lord at this level
    parent_years    : the parent period's total years
    depth           : 1=AD, 2=PD, 3=SD, 4=Prana
    """
    periods = []
    cur = start_dt
    for j in range(9):
        lord_idx = (start_lord_idx + j) % 9
        lord     = DASHA_ORDER[lord_idx]
        years    = parent_years * DASHA_YEARS[lord] / TOTAL_YEARS
        end      = _add_years(cur, years)
        entry    = {"lord": lord, "start": cur, "end": end, "years": years}
        if depth < 4:
            entry["sub"] = _dasha_periods(cur, lord_idx, years, depth + 1)
        periods.append(entry)
        cur = end
    return periods


def calculate_vimshottari(moon_lon: float, birth_dt: datetime) -> list[dict]:
    """
    Compute the full Vimshottari Dasha sequence anchored on Moon's exact
    sidereal longitude and the birth datetime.

    Returns 9 Mahadasha dicts, each with antardashas and all sub-levels.
    """
    moon_lon    = moon_lon % 360
    nak_idx     = int(moon_lon / NAK_SIZE) % 27
    birth_lord  = NAK_DASHA_LORD[nak_idx]
    pos_in_nak  = moon_lon % NAK_SIZE
    elapsed_frac = pos_in_nak / NAK_SIZE

    birth_lord_years = DASHA_YEARS[birth_lord]
    elapsed_years    = elapsed_frac * birth_lord_years

    md_start    = _add_years(birth_dt, -elapsed_years)
    birth_idx   = DASHA_ORDER.index(birth_lord)

    sequence = []
    cur_start = md_start

    for i in range(9):
        md_lord_idx = (birth_idx + i) % 9
        md_lord     = DASHA_ORDER[md_lord_idx]
        md_years    = DASHA_YEARS[md_lord]
        md_end      = _add_years(cur_start, md_years)

        antardashas = _dasha_periods(cur_start, md_lord_idx, md_years, depth=1)

        sequence.append({
            "lord":        md_lord,
            "start":       cur_start,
            "end":         md_end,
            "years":       md_years,
            "antardashas": antardashas,
        })
        cur_start = md_end

    return sequence


# --- Active period finder ----------------------------------------------------

def _find_active(periods: list[dict], query_date: datetime) -> dict | None:
    """Return the period dict that contains query_date."""
    for p in periods:
        if p["start"] <= query_date < p["end"]:
            return p
    return None


def get_active_dasha(sequence: list[dict], query_date: datetime) -> dict:
    """
    Return a dict with the full active chain: md, ad, pd, sd, prana.
    Each is a period dict {lord, start, end, years}. Missing levels are None.
    """
    result = {"md": None, "ad": None, "pd": None, "sd": None, "prana": None}

    md = _find_active(sequence, query_date)
    if not md:
        return result
    result["md"] = md

    ad = _find_active(md["antardashas"], query_date)
    if not ad:
        return result
    result["ad"] = ad

    pd = _find_active(ad.get("sub", []), query_date)
    if not pd:
        return result
    result["pd"] = pd

    sd = _find_active(pd.get("sub", []), query_date)
    if not sd:
        return result
    result["sd"] = sd

    prana = _find_active(sd.get("sub", []), query_date)
    result["prana"] = prana
    return result


# --- Dasha formatter ---------------------------------------------------------

_FMT_DATE = "%b %d, %Y"


def _fmt(dt: datetime) -> str:
    return dt.strftime(_FMT_DATE)


def _bar(fraction: float, width: int = 20) -> str:
    """Simple ASCII progress bar."""
    filled = int(fraction * width)
    return "#" * filled + "." * (width - filled)


def _elapsed_pct(p: dict, query_date: datetime) -> float:
    total = (p["end"] - p["start"]).total_seconds()
    done  = (query_date - p["start"]).total_seconds()
    return max(0.0, min(1.0, done / total)) if total else 0.0


def format_dasha_block(sequence: list[dict], query_date: datetime,
                       birth_dt: datetime | None = None) -> str:
    """
    Render dasha output for the Claude system prompt.

    Shows:
      1. Current active dasha chain — MD / AD / PD with progress bars
      2. Full Antardasha breakdown of the active Mahadasha
      3. Upcoming MD transitions (all future)
      4. Compact one-line MD sequence (replaces verbose full table)

    TOKEN SAVINGS vs v3:
    - ASCII separators (--- not unicode lines): ~130 tokens
    - Full sequence is now one compact line instead of 9 rows: ~125 tokens
    - Progress bar uses ASCII # and . chars (no Unicode blocks)
    """
    active = get_active_dasha(sequence, query_date)
    lines  = []

    # -- 1. Current active dasha chain (MD / AD / PD) -------------------------
    lines.append("CURRENT DASHA TIMELINE")
    lines.append("-" * 56)

    level_labels = [
        ("Mahadasha  ", "md"),
        ("Antardasha ", "ad"),
        ("Pratyantar ", "pd"),
    ]
    for label, key in level_labels:
        p = active.get(key)
        if p:
            pct       = _elapsed_pct(p, query_date)
            bar       = _bar(pct)
            days_left = int((p["end"] - query_date).total_seconds() / 86400)
            lines.append(
                f"  {label}: {p['lord']:<10} "
                f"{_fmt(p['start'])}  ->  {_fmt(p['end'])}"
            )
            lines.append(f"             {bar} {pct*100:.1f}%  |  {days_left}d left")
        else:
            lines.append(f"  {label}: -")

    lines.append("")

    # -- 2. Active MD — all Antardashas ---------------------------------------
    md = active.get("md")
    if md:
        lines.append(f"ALL ANTARDASHAS IN {md['lord'].upper()} MAHADASHA")
        lines.append("-" * 56)
        lines.append(f"  {'Lord':<10} {'Start':<16} {'End':<16} {'Dur':>7}")
        lines.append("  " + "-" * 52)
        for ad in md["antardashas"]:
            marker   = " << ACTIVE" if (active.get("ad") and ad["lord"] == active["ad"]["lord"]
                                        and ad["start"] == active["ad"]["start"]) else ""
            dur_days = (ad["end"] - ad["start"]).days
            lines.append(
                f"  {ad['lord']:<10} "
                f"{_fmt(ad['start']):<16} "
                f"{_fmt(ad['end']):<16} "
                f"{dur_days:>5}d{marker}"
            )
        lines.append("")

    # -- 3. Upcoming MD transitions (all future) ------------------------------
    upcoming = [p for p in sequence if p["start"] > query_date]
    if upcoming:
        lines.append("UPCOMING MAHADASHA TRANSITIONS")
        lines.append("-" * 56)
        for p in upcoming:
            days_away = (p["start"] - query_date).days
            lines.append(f"  -> {p['lord']:<10} begins {_fmt(p['start'])}  ({days_away}d away)")
        lines.append("")

    # -- 4. Compact MD sequence (one line, with birth balance annotation) -----
    parts = []
    for p in sequence:
        start_yr = p["start"].year
        end_yr   = p["end"].year
        tag = ""
        if md and p["lord"] == md["lord"] and p["start"] == md["start"]:
            tag = "*"  # currently active
        if birth_dt and p["start"] <= birth_dt < p["end"]:
            balance_days  = (p["end"] - birth_dt).days
            balance_years = balance_days / DAYS_PER_YEAR
            b_y = int(balance_years)
            b_m = int(round((balance_years - b_y) * 12))
            tag += f"[bal:{b_y}y{b_m}m]"
        parts.append(f"{p['lord']}{tag}({start_yr}-{str(end_yr)[2:]})")

    lines.append("MD SEQUENCE: " + " > ".join(parts))

    return "\n".join(lines)


# --- House-lord map ----------------------------------------------------------

SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]


def house_lords(asc_sign_idx: int) -> dict[int, str]:
    return {h: SIGN_LORDS[(asc_sign_idx + h - 1) % 12] for h in range(1, 13)}


# --- Yoga detection ----------------------------------------------------------

PLANETS_ALL = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
BENEFICS    = {"Jupiter", "Venus", "Moon", "Mercury"}
MALEFICS    = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
KENDRA      = {1, 4, 7, 10}
TRIKONA     = {1, 5, 9}
TRIK        = {6, 8, 12}


def detect_yogas(chart: dict) -> list[dict]:
    d1      = chart["d1"]
    # Use d1_asc directly — avoids fragile Moon-based derivation
    asc_idx = chart["d1_asc"]
    lords   = house_lords(asc_idx)
    yogas   = []

    def h(name):  return d1[name]["house"]
    def s(name):  return d1[name]["sign_idx"]

    def same_house(p1, p2):   return h(p1) == h(p2)
    def is_debil(name):       return d1[name].get("debilitated", False)
    def is_exalted(name):     return d1[name].get("exalted", False)

    # -- 1. Gaja Kesari Yoga --------------------------------------------------
    diff = abs(h("Moon") - h("Jupiter"))
    if diff in (0, 3, 6, 9) and h("Jupiter") in KENDRA:
        yogas.append({
            "name": "Gaja Kesari Yoga",
            "description": "Jupiter in a kendra from Moon — wisdom, renown, and moral authority.",
            "planets": ["Moon", "Jupiter"],
            "quality": "benefic"
        })

    # -- 2. Neecha Bhanga Raja Yoga -------------------------------------------
    DEBIL_SIGN = {"Sun":6,"Moon":7,"Mars":3,"Mercury":11,"Jupiter":9,"Venus":5,"Saturn":0,"Rahu":7,"Ketu":1}
    EXALT_SIGN = {"Sun":0,"Moon":1,"Mars":9,"Mercury":5,"Jupiter":3,"Venus":11,"Saturn":6}
    EXALT_LORD = {v: k for k, v in EXALT_SIGN.items()}

    for planet in PLANETS_ALL[:7]:
        if not is_debil(planet):
            continue
        debil_sign_idx = DEBIL_SIGN[planet]
        disp = SIGN_LORDS[debil_sign_idx]
        exalt_planet = EXALT_LORD.get(debil_sign_idx)
        cancellation = False
        reason = ""

        if h(disp) in KENDRA:
            cancellation = True
            reason = f"{disp} (lord of debil sign) in kendra H{h(disp)}"
        if exalt_planet and h(exalt_planet) in KENDRA:
            cancellation = True
            reason += ("; " if reason else "") + \
                      f"{exalt_planet} (exalt lord) in kendra H{h(exalt_planet)}"
        moon_sign = s("Moon")
        disp_from_moon = (s(disp) - moon_sign) % 12 + 1
        if disp_from_moon in KENDRA:
            cancellation = True
            reason += ("; " if reason else "") + f"{disp} in kendra from Moon"

        if cancellation:
            yogas.append({
                "name": f"Neecha Bhanga Raja Yoga — {planet}",
                "description": (
                    f"{planet} debilitated but fall cancelled: {reason}. "
                    "Weakness converts to latent royal power through adversity."
                ),
                "planets": [planet, disp],
                "quality": "mixed"
            })

    # -- 3. Viparita Raja Yoga ------------------------------------------------
    for trik_house in [6, 8, 12]:
        lord_of_trik = lords[trik_house]
        lord_house   = h(lord_of_trik)
        if lord_house in TRIK and lord_house != trik_house:
            yogas.append({
                "name": f"Viparita Raja Yoga ({trik_house}th lord in {lord_house}th)",
                "description": (
                    f"Lord of H{trik_house} ({lord_of_trik}) in H{lord_house} — "
                    "adversity becomes the source of unexpected power."
                ),
                "planets": [lord_of_trik],
                "quality": "benefic"
            })

    # -- 4. Kemadruma Yoga ----------------------------------------------------
    moon_sign = s("Moon")
    flanking  = [
        p for p in PLANETS_ALL
        if p not in ("Moon", "Rahu", "Ketu") and
        s(p) in ((moon_sign + 1) % 12, (moon_sign - 1) % 12)
    ]
    if not flanking:
        yogas.append({
            "name": "Kemadruma Yoga",
            "description": "No planets flank Moon — emotional isolation; inner strength must be self-built.",
            "planets": ["Moon"],
            "quality": "challenging"
        })

    # -- 5. Veshi Yoga --------------------------------------------------------
    sun_sign        = s("Sun")
    second_from_sun = (sun_sign + 1) % 12
    veshi_planets   = [
        p for p in PLANETS_ALL
        if p not in ("Sun", "Moon", "Rahu", "Ketu") and s(p) == second_from_sun
    ]
    if veshi_planets:
        is_ben = all(p in BENEFICS for p in veshi_planets)
        yogas.append({
            "name": "Veshi Yoga",
            "description": (
                f"{', '.join(veshi_planets)} in 2nd from Sun — solar vitality and eloquence. "
                + ("Benefic." if is_ben else "Malefic influence — complexity.")
            ),
            "planets": ["Sun"] + veshi_planets,
            "quality": "benefic" if is_ben else "mixed"
        })

    # -- 6. Dharma-Karmadhipati Yoga ------------------------------------------
    lord_9, lord_10 = lords[9], lords[10]
    if same_house(lord_9, lord_10):
        yogas.append({
            "name": "Dharma-Karmadhipati Yoga",
            "description": (
                f"9th lord ({lord_9}) + 10th lord ({lord_10}) conjunct in H{h(lord_9)} — "
                "dharma and career aligned; profession becomes calling."
            ),
            "planets": [lord_9, lord_10],
            "quality": "benefic"
        })
    elif s(lord_9) == (asc_idx + 9) % 12 and s(lord_10) == (asc_idx + 8) % 12:
        yogas.append({
            "name": "Dharma-Karmadhipati Yoga (Exchange)",
            "description": f"9th lord ({lord_9}) and 10th lord ({lord_10}) exchange signs — purpose and profession in powerful mutual activation.",
            "planets": [lord_9, lord_10],
            "quality": "benefic"
        })

    # -- 7. Raja Yoga (kendra + trikona lord conjunction) ---------------------
    kendra_lords  = {lords[h_] for h_ in KENDRA  if h_ != 1}
    trikona_lords = {lords[h_] for h_ in TRIKONA if h_ != 1}
    seen_raja = set()
    for p1 in PLANETS_ALL:
        for p2 in PLANETS_ALL:
            if p1 >= p2:
                continue
            if (p1 in kendra_lords or p2 in kendra_lords) and \
               (p1 in trikona_lords or p2 in trikona_lords) and \
               same_house(p1, p2):
                key = tuple(sorted([p1, p2]))
                if key not in seen_raja:
                    seen_raja.add(key)
                    yogas.append({
                        "name": f"Raja Yoga — {p1} + {p2}",
                        "description": (
                            f"{p1} and {p2} conjunct in H{h(p1)} — kendra and trikona lords meeting."
                        ),
                        "planets": [p1, p2],
                        "quality": "benefic"
                    })

    # -- 8. Parivartana Yoga --------------------------------------------------
    for i, p1 in enumerate(PLANETS_ALL):
        for p2 in PLANETS_ALL[i+1:]:
            if p1 in ("Rahu", "Ketu") or p2 in ("Rahu", "Ketu"):
                continue
            p1_owns = [idx for idx, lord in enumerate(SIGN_LORDS) if lord == p1]
            p2_owns = [idx for idx, lord in enumerate(SIGN_LORDS) if lord == p2]
            if s(p1) in p2_owns and s(p2) in p1_owns:
                h1, h2 = h(p1), h(p2)
                is_maha = (h1 in KENDRA | TRIKONA) and (h2 in KENDRA | TRIKONA)
                name    = "Maha Parivartana Yoga" if is_maha else "Parivartana Yoga"
                yogas.append({
                    "name": f"{name} — {p1} <-> {p2} (H{h1} <-> H{h2})",
                    "description": (
                        f"{p1} in {SIGNS[s(p1)]} exchanges with {p2} in {SIGNS[s(p2)]} — "
                        "houses merge energies; each planet gains strength of both."
                    ),
                    "planets": [p1, p2],
                    "quality": "benefic"
                })

    # Deduplicate
    seen, unique = set(), []
    for y in yogas:
        if y["name"] not in seen:
            seen.add(y["name"])
            unique.append(y)
    return unique


def format_yoga_block(yogas: list[dict]) -> str:
    if not yogas:
        return "ACTIVE YOGAS\nNone detected."
    benefic     = [y for y in yogas if y["quality"] == "benefic"]
    mixed       = [y for y in yogas if y["quality"] == "mixed"]
    challenging = [y for y in yogas if y["quality"] == "challenging"]
    lines = ["ACTIVE YOGAS & SPECIAL COMBINATIONS", ""]

    def _desc(y):
        # Cap description at 120 chars to save tokens
        d = y["description"]
        return d[:120] + "..." if len(d) > 120 else d

    if benefic:
        lines.append("Gifts & Blessings:")
        for y in benefic:
            lines.append(f"  + {y['name']}")
            lines.append(f"    {_desc(y)}")
        lines.append("")
    if mixed:
        lines.append("Latent Power (activated through challenge):")
        for y in mixed:
            lines.append(f"  + {y['name']}")
            lines.append(f"    {_desc(y)}")
        lines.append("")
    if challenging:
        lines.append("Challenges to work with:")
        for y in challenging:
            lines.append(f"  ! {y['name']}")
            lines.append(f"    {_desc(y)}")
    return "\n".join(lines)


# --- System Prompt Template --------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
{language_instruction}You are my personal Vedic astrology advisor — a masterful Jyotishi with deep \
roots in classical Parashari and Jaimini traditions. Below is my complete birth \
chart, divisional charts, dasha timeline, and yoga profile. This is the foundation \
of everything you tell me. Study it deeply before responding.

=== NATIVE DETAILS ===
{native_block}

=== BIRTH CHART DATA ===
{chart_block}
=== DASHA TIMELINE ===
{dasha_block}

=== YOGAS ===
{yoga_block}

=== DATA BOUNDARIES ===
The chart data above is ALL that is available in this session.
- If asked about a divisional chart NOT shown above, say: "That chart isn't \
loaded yet — ask me about [topic] specifically and I'll pull it in."
- NEVER guess or invent planetary positions. Every placement you state must \
exist verbatim in the data above.
- If a placement in the data conflicts with your training knowledge, trust the \
data — it was computed from pyswisseph for this exact birth.

YOUR ROLE
- Interpret personality, strengths, shadow traits, and karmic patterns
- Guide on relationships, career, spirituality, and major life decisions
- Read current transits and dashas against the natal chart
- Help navigate WITH the placements, not against them

HOW TO ANSWER
- Ground every insight in specific placements (house, sign, nakshatra, dasha). No generic astrology.
- For timing: name exact MD/AD period and explain WHY that planet's energy manifests as described.
- For challenges: pair the difficulty with (a) what it's teaching and (b) a concrete remedy or reframe.
- For strengths: show HOW to activate in practice — specific actions, not abstract affirmations.
- Neecha Bhanga / Viparita Raja Yogas: frame hardship as the launch mechanism, not the obstacle.
- Parivartana Yogas: those two houses are lived as one — weave both into any reading touching those planets.
- If ambiguous, ask: "Are you asking about [A] or [B]? My chart speaks differently to each."
- After answering, flag important unrequested findings: "Your chart also shows something about [X]..."

HOW TO ANSWER PREDICTIVE QUESTIONS
1. Check D1 first, then the relevant varga (D3 siblings, D9 spouse, D10 career, D7 children).
2. State what EACH chart shows separately before synthesising.
3. Name conflicts honestly rather than picking the cleaner answer.
4. Weight the karaka (significator planet) above sign heuristics when they disagree.
5. Match confidence to evidence — "chart suggests X but with uncertainty because Y."

SHOWING YOUR WORK
- Do NOT display the full calculation table in responses.
- Internally check all relevant charts, then surface only the synthesised conclusion.
- Briefly name the 1-2 strongest signals that drove your answer (1 sentence max).
- If the user wants full reasoning, they'll ask — default is clean, gist-only output.

TONE
Speak like a wise, direct friend who understands both Jyotish and modern life.
Warm but to the point — no vague spiritual filler, no flowery language.
Avoid: "inexplicably", "profound", "tapestry", "realm", "celestial journey".
When asked "what should I do", give actual steps.

FORMATTING
- Plain text by default. **Bold** only for key terms or important emphasis.
- Bullet points ONLY when listing 3 or more distinct items.
- No headers unless the answer has clearly separate topics.
- Reference chart factors in 3-5 words max (e.g. "Moon in Scorpio", "Saturn-Jupiter exchange").
- The user has seen their chart — they want insights, not a repeat of raw data.

RESPONSE LENGTH
Aim for 200-400 words. Be complete but not exhaustive.
If one paragraph covers it, stop there. Every response must end with a complete sentence.
"""


# --- Query-aware divisional chart selector -----------------------------------

# All non-default chart keys (everything except D9 and D10 which are always loaded)
_ALL_CHART_KEYS = [
    "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d11",
    "d12", "d16", "d20", "d24", "d27", "d30", "d40", "d45", "d60"
]

# Patterns that mean the user wants ALL charts at once
_BULK_PATTERNS = [
    "all chart", "all divisional", "all varga", "every chart",
    "list chart", "show chart", "divisional chart", "d1 to d60",
    "d1-d60", "all my chart", "full chart", "complete chart",
    "all placement", "show all", "every divisional", "all varga",
    "list all", "list my chart", "all d",
]

_CHART_TRIGGERS: dict[str, list[str]] = {
    "d2":  ["d2", "hora", "wealth", "financial", "money chart"],
    "d3":  ["d3", "drekkana", "sibling", "brother", "sister", "courage", "valor"],
    "d4":  ["d4", "chaturthamsa", "property", "home", "land", "real estate", "fixed asset"],
    "d5":  ["d5", "panchamsa", "mantra", "ishta devata", "deity", "pooja"],
    "d6":  ["d6", "shashthamsa", "health", "disease", "illness", "sick",
            "enemy", "debt", "competition", "legal", "lawsuit"],
    "d7":  ["d7", "saptamsa", "child", "children", "son", "daughter",
            "pregnant", "pregnancy", "fertility", "baby", "progeny"],
    "d8":  ["d8", "ashtamsa", "accident", "sudden event", "longevity",
            "mystery", "obstacle", "hidden danger"],
    "d11": ["d11", "rudramsa", "ekadasamsa", "gains", "income", "social network",
            "destruction", "transformation"],
    "d12": ["d12", "dwadasamsa", "father", "mother", "parent",
            "ancestor", "lineage", "family background", "ancestry"],
    "d16": ["d16", "shodasamsa", "vehicle", "car", "conveyance", "travel luck",
            "comforts", "happiness", "luxury"],
    "d20": ["d20", "vimsamsa", "vimshamsa", "spiritual", "worship", "meditation",
            "devotion", "moksha", "liberation", "upasana"],
    "d24": ["d24", "chaturvimsamsa", "siddhamsa", "education", "degree", "study",
            "college", "university", "learning", "knowledge", "student"],
    "d27": ["d27", "saptavimshamsa", "nakshatramsa", "strength",
            "vitality", "resistance", "sport", "physical", "stamina"],
    "d30": ["d30", "trimshamsa", "misfortune", "struggle", "hardship", "suffering"],
    "d40": ["d40", "khavedamsa", "maternal", "mother's family",
            "maternal uncle", "matrilineal", "mother side"],
    "d45": ["d45", "akshavedamsa", "paternal", "father's family",
            "patrilineal", "father side"],
    "d60": ["d60", "shashtiamsa", "shastiamsha", "past life", "karma",
            "fate", "destiny", "karmic debt", "previous birth", "soul purpose",
            "past karma", "purva karma"],
}


def detect_extra_charts(query: str) -> list[str]:
    """
    Return chart keys to inject beyond the default D1+D9+D10.

    BULK DETECTION: if the query matches a bulk/listing pattern, returns
    ALL 17 non-default chart keys so Claude has everything it needs.

    SPECIFIC DETECTION: returns only the chart(s) relevant to the query
    (by chart code, chart name, or topic keyword).
    """
    q = query.lower()

    # Bulk request -> return everything (user wants all charts)
    if any(pat in q for pat in _BULK_PATTERNS):
        return _ALL_CHART_KEYS

    extras: list[str] = []
    for key, keywords in _CHART_TRIGGERS.items():
        if any(kw in q for kw in keywords):
            extras.append(key)
    return extras


# --- Master builder ----------------------------------------------------------

def build_system_prompt(chart: dict, birth_dt: datetime, query_date: datetime = None,
                        language: str = "English",
                        extra_charts: list | None = None,
                        birth_details: dict | None = None) -> str:
    """
    Build the complete Claude system prompt from a calculated chart.

    Parameters
    ----------
    chart         : Output of vedic_calc.calculate_chart()
    birth_dt      : Actual birth datetime in UTC (for dasha timing)
    query_date    : Date for 'active dasha' calculation (default: now)
    language      : Language for responses (default: English)
    extra_charts  : Additional divisional chart keys beyond D1 + D9 + D10
    birth_details : Optional dict with {name, dob, tob, pob} from the
                    birth form. dob format: "YYYY-MM-DD", tob: "HH:MM"
    """
    if query_date is None:
        query_date = datetime.utcnow()

    from vedic_calc import format_for_prompt

    chart_block = format_for_prompt(chart, extra_charts=extra_charts)

    # Use raw full-precision Moon longitude for dasha accuracy
    if "raw_lons" in chart:
        moon_lon = chart["raw_lons"]["Moon"]
    else:
        moon_lon = chart["d1"]["Moon"]["sign_idx"] * 30 + chart["d1"]["Moon"]["degrees"]

    sequence    = calculate_vimshottari(moon_lon, birth_dt)
    dasha_block = format_dasha_block(sequence, query_date, birth_dt=birth_dt)

    yogas      = detect_yogas(chart)
    yoga_block = format_yoga_block(yogas)

    # -- Native details block -------------------------------------------------
    bd = birth_details or {}
    name_str = bd.get("name", "").strip()
    dob_str  = bd.get("dob", "")
    tob_str  = bd.get("tob", "")
    pob_str  = bd.get("pob", "")

    if dob_str:
        try:
            dob_dt        = datetime.strptime(dob_str, "%Y-%m-%d")
            dob_formatted = dob_dt.strftime("%B %d, %Y")
        except ValueError:
            dob_formatted = dob_str
    else:
        dob_formatted = birth_dt.strftime("%B %d, %Y")

    age = query_date.year - birth_dt.year
    if (query_date.month, query_date.day) < (birth_dt.month, birth_dt.day):
        age -= 1

    native_lines = []
    if name_str:
        native_lines.append(f"Name:  {name_str}")
    native_lines.append(f"DOB:   {dob_formatted}  |  TOB: {tob_str or birth_dt.strftime('%H:%M')} (local)")
    if pob_str:
        native_lines.append(f"Place: {pob_str}")
    native_lines.append(f"Age:   {age} years (as of {query_date.strftime('%B %Y')})")
    native_block = "\n".join(native_lines)

    # -- Language instruction -------------------------------------------------
    if language and language.lower() != "english":
        language_instruction = (
            f"LANGUAGE INSTRUCTION: Respond entirely in {language}. "
            f"All answers must be written in {language} only. Do not mix languages.\n\n"
        )
    else:
        language_instruction = ""

    return SYSTEM_PROMPT_TEMPLATE.format(
        chart_block=chart_block,
        dasha_block=dasha_block,
        yoga_block=yoga_block,
        language_instruction=language_instruction,
        native_block=native_block,
    )


# --- Quick test --------------------------------------------------------------

if __name__ == "__main__":
    from vedic_calc import calculate_chart

    # Oct 24, 1999 — 18:30 IST = 13:00 UTC — Nagpur (21.15N, 79.09E)
    birth_utc = datetime(1999, 10, 24, 13, 0, 0)
    chart = calculate_chart(birth_utc, lat=21.1458, lon=79.0882)

    print("Raw Moon longitude:", chart["raw_lons"]["Moon"])
    print("D1 ASC sign index:", chart["d1_asc"], "=", chart["core_trinity"]["ascendant"]["sign"])
    print()

    seq = calculate_vimshottari(chart["raw_lons"]["Moon"], birth_utc)
    block = format_dasha_block(seq, datetime(2025, 5, 16), birth_dt=birth_utc)
    print(block)

    print()
    print("--- detect_extra_charts tests ---")
    test_queries = [
        "list out my divisional chart details (all)",
        "what does D7 show?",
        "tell me about my saptamsa",
        "children",
        "past life karma",
        "career",
        "what is my navamsa",
    ]
    for q in test_queries:
        extras = detect_extra_charts(q)
        print(f"  '{q}' -> {extras or 'NONE (uses default D1+D9+D10)'}")

    print()
    prompt = build_system_prompt(
        chart, birth_utc,
        query_date=datetime(2025, 5, 16),
        birth_details={
            "name": "Test User",
            "dob":  "1999-10-24",
            "tob":  "18:30",
            "pob":  "Nagpur, Maharashtra, India",
        }
    )
    print(f"System prompt length: {len(prompt)} chars, ~{len(prompt)//4} tokens")
    print(prompt[:600], "...")
