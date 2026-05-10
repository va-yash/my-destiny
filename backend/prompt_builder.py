"""
prompt_builder.py — Yoga Detection + Vimshottari Dasha + Claude System Prompt Assembly

Depends on: vedic_calc.py
Install:    pip install pyswisseph python-dateutil

Entry point:
    from prompt_builder import build_system_prompt
    system_prompt = build_system_prompt(chart, birth_dt, query_date=datetime.utcnow())
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from vedic_calc import SIGNS, SIGN_ABBR

# ─── Vimshottari Dasha ────────────────────────────────────────────────────────

DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

# Nakshatra index (0-26) → Dasha lord
NAK_DASHA_LORD = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury"
]

NAK_SIZE = 360.0 / 27          # 13.3333°
TOTAL_YEARS = 120.0


def _add_years_fractional(dt: datetime, years_float: float) -> datetime:
    """Add fractional years to a datetime using day-based precision."""
    return dt + timedelta(days=years_float * 365.25)


def calculate_vimshottari(moon_lon: float, birth_dt: datetime) -> list[dict]:
    """
    Compute the full Vimshottari Dasha sequence (9 periods + their sub-periods)
    anchored on the Moon's sidereal longitude and birth datetime.

    Returns list of dicts:
        lord, start, end, years, antardashas: [{lord, start, end}]
    """
    nak_idx      = int(moon_lon / NAK_SIZE) % 27
    birth_lord   = NAK_DASHA_LORD[nak_idx]
    pos_in_nak   = moon_lon % NAK_SIZE
    elapsed_frac = pos_in_nak / NAK_SIZE          # how far into nakshatra

    md_years_total  = DASHA_YEARS[birth_lord]
    elapsed_in_md   = elapsed_frac * md_years_total
    md_start        = _add_years_fractional(birth_dt, -elapsed_in_md)

    start_idx = DASHA_ORDER.index(birth_lord)
    sequence  = []
    cur_start = md_start

    for i in range(9):
        md_lord  = DASHA_ORDER[(start_idx + i) % 9]
        md_years = DASHA_YEARS[md_lord]
        md_end   = _add_years_fractional(cur_start, md_years)

        # Antardashas: sequence starts from the MD lord itself
        ad_start   = cur_start
        antardashas = []
        ad_offset   = i  # AD sequence starts at same position as MD lord
        for j in range(9):
            ad_lord  = DASHA_ORDER[(start_idx + ad_offset + j) % 9]
            ad_years = (md_years * DASHA_YEARS[ad_lord]) / TOTAL_YEARS
            ad_end   = _add_years_fractional(ad_start, ad_years)
            antardashas.append({"lord": ad_lord, "start": ad_start, "end": ad_end})
            ad_start = ad_end

        sequence.append({
            "lord":        md_lord,
            "start":       cur_start,
            "end":         md_end,
            "years":       md_years,
            "antardashas": antardashas
        })
        cur_start = md_end

    return sequence


def get_current_dasha(sequence: list[dict], query_date: datetime) -> dict:
    """
    Given the dasha sequence and a query date, return:
        mahadasha lord + dates, antardasha lord + dates, next MD + AD transitions.
    """
    result = {
        "mahadasha":  None, "md_start": None, "md_end": None,
        "antardasha": None, "ad_start": None, "ad_end": None,
        "upcoming":   []
    }

    for period in sequence:
        if period["start"] <= query_date < period["end"]:
            result["mahadasha"] = period["lord"]
            result["md_start"]  = period["start"]
            result["md_end"]    = period["end"]

            for ad in period["antardashas"]:
                if ad["start"] <= query_date < ad["end"]:
                    result["antardasha"] = ad["lord"]
                    result["ad_start"]   = ad["start"]
                    result["ad_end"]     = ad["end"]
                    break
            break

    # Next two MD transitions
    for p in sequence:
        if p["start"] > query_date:
            result["upcoming"].append({"lord": p["lord"], "start": p["start"]})
            if len(result["upcoming"]) >= 2:
                break

    return result


def format_dasha_block(sequence: list[dict], query_date: datetime) -> str:
    """Return a formatted multi-line dasha block for the system prompt."""
    cur   = get_current_dasha(sequence, query_date)
    lines = ["CURRENT DASHA TIMELINE"]

    if cur["mahadasha"]:
        lines.append(
            f"Mahadasha  : {cur['mahadasha']:<10} "
            f"({cur['md_start'].strftime('%b %d, %Y')} → {cur['md_end'].strftime('%b %d, %Y')})"
        )
    if cur["antardasha"]:
        lines.append(
            f"Antardasha : {cur['antardasha']:<10} "
            f"({cur['ad_start'].strftime('%b %d, %Y')} → {cur['ad_end'].strftime('%b %d, %Y')})"
        )

    lines.append("")
    lines.append("UPCOMING MAHADASHA TRANSITIONS")
    for u in cur["upcoming"]:
        lines.append(f"  → {u['lord']:<10} begins {u['start'].strftime('%b %d, %Y')}")

    lines.append("")
    lines.append("FULL MAHADASHA SEQUENCE (birth onward)")
    for p in sequence:
        marker = " ◀ ACTIVE" if p["lord"] == cur.get("mahadasha") else ""
        lines.append(
            f"  {p['lord']:<10} {p['start'].strftime('%Y')}–{p['end'].strftime('%Y')}{marker}"
        )

    return "\n".join(lines)


# ─── House-lord map ───────────────────────────────────────────────────────────

# Traditional (Parashari) sign lords — used for yoga detection
SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"
]


def house_lords(asc_sign_idx: int) -> dict[int, str]:
    """Return {house_number: lord_planet} for any ascendant sign index."""
    return {
        h: SIGN_LORDS[(asc_sign_idx + h - 1) % 12]
        for h in range(1, 13)
    }


def planet_house(d1: dict, name: str) -> int:
    return d1[name]["house"]


def planet_sign(d1: dict, name: str) -> int:
    return d1[name]["sign_idx"]


def houses_of_planet(d1: dict, planet_name: str, asc_idx: int) -> int:
    """Which house is this planet in?"""
    return (d1[planet_name]["sign_idx"] - asc_idx) % 12 + 1


# ─── Yoga detection ───────────────────────────────────────────────────────────

PLANETS_ALL = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
BENEFICS    = {"Jupiter", "Venus", "Moon", "Mercury"}
MALEFICS    = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
KENDRA      = {1, 4, 7, 10}
TRIKONA     = {1, 5, 9}
TRIK        = {6, 8, 12}


def detect_yogas(chart: dict) -> list[dict]:
    """
    Detect major classical yogas from the chart dict.
    Returns list of {name, description, planets, quality}
    where quality is 'benefic' | 'challenging' | 'mixed'.
    """
    d1      = chart["d1"]
    asc_idx = d1["Sun"]["sign_idx"] - d1["Sun"]["house"] + 1  # back-calculate

    # Recalculate asc_idx reliably from any planet
    # asc_idx = (planet_sign - planet_house + 1) % 12 for any planet
    asc_idx = (d1["Moon"]["sign_idx"] - d1["Moon"]["house"] + 1) % 12
    lords   = house_lords(asc_idx)
    yogas   = []

    def h(name):
        return d1[name]["house"]

    def s(name):
        return d1[name]["sign_idx"]

    def same_house(p1, p2):
        return h(p1) == h(p2)

    def is_debil(name):
        return d1[name].get("debilitated", False)

    def is_retro(name):
        return d1[name].get("retrograde", False)

    def is_exalted(name):
        return d1[name].get("exalted", False)

    # planet whose sign is occupied by another planet
    def dispositor(planet_name):
        """Lord of the sign that planet_name is currently in."""
        return SIGN_LORDS[s(planet_name)]

    # ── 1. Gaja Kesari Yoga ──────────────────────────────────────────────
    moon_h = h("Moon")
    jup_h  = h("Jupiter")
    diff   = abs(moon_h - jup_h)
    mutual_kendra = diff in (0, 3, 6, 9)  # houses 1,4,7,10 from each other
    if mutual_kendra and jup_h in KENDRA:
        yogas.append({
            "name": "Gaja Kesari Yoga",
            "description": "Jupiter in a kendra from Moon — grants wisdom, renown, and moral authority.",
            "planets": ["Moon", "Jupiter"],
            "quality": "benefic"
        })

    # ── 2. Neecha Bhanga Raja Yoga ───────────────────────────────────────
    DEBIL_SIGN = {"Sun":6,"Moon":7,"Mars":3,"Mercury":11,"Jupiter":9,"Venus":5,"Saturn":0,"Rahu":7,"Ketu":1}
    EXALT_SIGN = {"Sun":0,"Moon":1,"Mars":9,"Mercury":5,"Jupiter":3,"Venus":11,"Saturn":6}
    EXALT_LORD = {v: k for k, v in EXALT_SIGN.items()}  # sign_idx → exalting planet

    for planet in PLANETS_ALL[:7]:  # Skip Rahu/Ketu for NBR
        if not is_debil(planet):
            continue

        debil_sign_idx = DEBIL_SIGN[planet]
        disp = SIGN_LORDS[debil_sign_idx]   # lord of debilitation sign
        disp_house = h(disp)

        # Exaltation lord of same sign
        exalt_planet = EXALT_LORD.get(debil_sign_idx)

        cancellation = False
        reason = ""

        # Rule 1: Lord of debilitation sign in kendra from lagna
        if disp_house in KENDRA:
            cancellation = True
            reason = f"{disp} (lord of debilitation sign) is in kendra (H{disp_house})"

        # Rule 2: Exaltation lord of the sign in kendra
        if exalt_planet and h(exalt_planet) in KENDRA:
            cancellation = True
            reason += ("; " if reason else "") + \
                      f"{exalt_planet} (exaltation lord of {SIGNS[debil_sign_idx]}) in kendra (H{h(exalt_planet)})"

        # Rule 3: Dispositor of debilitated planet in kendra from Moon
        moon_sign = s("Moon")
        disp_from_moon = (s(disp) - moon_sign) % 12 + 1
        if disp_from_moon in KENDRA:
            cancellation = True
            reason += ("; " if reason else "") + \
                      f"{disp} in kendra from Moon"

        if cancellation:
            yogas.append({
                "name": f"Neecha Bhanga Raja Yoga — {planet}",
                "description": (
                    f"{planet} is debilitated in {SIGNS[debil_sign_idx]} but its fall is cancelled: {reason}. "
                    "This converts weakness into latent royal power, activated through adversity."
                ),
                "planets": [planet, disp],
                "quality": "mixed"
            })

    # ── 3. Viparita Raja Yoga ────────────────────────────────────────────
    for trik_house in [6, 8, 12]:
        lord_of_trik = lords[trik_house]
        lord_house   = h(lord_of_trik)
        if lord_house in TRIK and lord_house != trik_house:
            yogas.append({
                "name": f"Viparita Raja Yoga ({trik_house}th lord in {lord_house}th)",
                "description": (
                    f"Lord of H{trik_house} ({lord_of_trik}) placed in H{lord_house} "
                    "— adversity and obstacles become the source of unexpected power and reversals of fortune."
                ),
                "planets": [lord_of_trik],
                "quality": "benefic"
            })

    # ── 4. Kemadruma Yoga ────────────────────────────────────────────────
    moon_sign = s("Moon")
    second_from_moon  = (moon_sign + 1) % 12
    twelfth_from_moon = (moon_sign - 1) % 12

    flanking_planets = [
        p for p in PLANETS_ALL
        if p not in ("Moon", "Rahu", "Ketu") and
        s(p) in (second_from_moon, twelfth_from_moon)
    ]
    if not flanking_planets:
        yogas.append({
            "name": "Kemadruma Yoga",
            "description": (
                "No planets flank the Moon in 2nd or 12th signs from it — "
                "creates emotional isolation, inconsistency, and the need to build inner stability independently."
            ),
            "planets": ["Moon"],
            "quality": "challenging"
        })

    # ── 5. Veshi Yoga (planets in 2nd from Sun) ──────────────────────────
    sun_sign = s("Sun")
    second_from_sun = (sun_sign + 1) % 12
    veshi_planets = [
        p for p in PLANETS_ALL
        if p not in ("Sun", "Moon", "Rahu", "Ketu") and s(p) == second_from_sun
    ]
    if veshi_planets:
        is_benefic = all(p in BENEFICS for p in veshi_planets)
        yogas.append({
            "name": "Veshi Yoga",
            "description": (
                f"{', '.join(veshi_planets)} in 2nd from Sun — "
                "adds vitality and eloquence to the solar identity. "
                + ("Benefic planets make this auspicious." if is_benefic else "Mixed/malefic influence — brings complexity.")
            ),
            "planets": ["Sun"] + veshi_planets,
            "quality": "benefic" if is_benefic else "mixed"
        })

    # ── 6. Dharma-Karmadhipati Yoga ──────────────────────────────────────
    lord_9  = lords[9]
    lord_10 = lords[10]
    if same_house(lord_9, lord_10):
        yogas.append({
            "name": "Dharma-Karmadhipati Yoga",
            "description": (
                f"9th lord ({lord_9}) and 10th lord ({lord_10}) conjunct in H{h(lord_9)} — "
                "purpose (dharma) and career (karma) are aligned; profession becomes a spiritual calling."
            ),
            "planets": [lord_9, lord_10],
            "quality": "benefic"
        })
    # Also check exchange
    elif s(lord_9) == (asc_idx + 9) % 12 and s(lord_10) == (asc_idx + 8) % 12:
        # lord_9 is in 10th sign, lord_10 is in 9th sign = exchange
        yogas.append({
            "name": "Dharma-Karmadhipati Yoga (Exchange)",
            "description": (
                f"9th lord ({lord_9}) and 10th lord ({lord_10}) exchange signs — "
                "powerful alignment of purpose and profession."
            ),
            "planets": [lord_9, lord_10],
            "quality": "benefic"
        })

    # ── 7. Raja Yoga (Kendra-Trikona lord conjunction / mutual aspect) ───
    kendra_lords  = {lords[h_] for h_ in KENDRA  if h_ != 1}   # 4,7,10
    trikona_lords = {lords[h_] for h_ in TRIKONA if h_ != 1}   # 5,9
    # Exclude if same planet is both (e.g., for some lagnas)
    seen_raja = set()
    for p1 in PLANETS_ALL:
        for p2 in PLANETS_ALL:
            if p1 >= p2:
                continue
            is_kendra_lord  = (p1 in kendra_lords or p2 in kendra_lords)
            is_trikona_lord = (p1 in trikona_lords or p2 in trikona_lords)
            if is_kendra_lord and is_trikona_lord and same_house(p1, p2):
                pair_key = tuple(sorted([p1, p2]))
                if pair_key not in seen_raja:
                    seen_raja.add(pair_key)
                    yogas.append({
                        "name": f"Raja Yoga — {p1} + {p2}",
                        "description": (
                            f"{p1} (lord of {[k for k,v in lords.items() if v==p1]}) "
                            f"and {p2} (lord of {[k for k,v in lords.items() if v==p2]}) "
                            f"conjunct in H{h(p1)} — kendra and trikona lords meeting = royal combinations."
                        ),
                        "planets": [p1, p2],
                        "quality": "benefic"
                    })

    # ── 8. Maha Parivartana Yoga (sign exchange between two planets) ─────
    for i, p1 in enumerate(PLANETS_ALL):
        for p2 in PLANETS_ALL[i+1:]:
            if p1 in ("Rahu", "Ketu") or p2 in ("Rahu", "Ketu"):
                continue
            # p1 is in p2's own sign AND p2 is in p1's own sign
            p1_sign = s(p1)
            p2_sign = s(p2)
            p1_owns = [idx for idx, lord in enumerate(SIGN_LORDS) if lord == p1]
            p2_owns = [idx for idx, lord in enumerate(SIGN_LORDS) if lord == p2]
            if p1_sign in p2_owns and p2_sign in p1_owns:
                h1, h2 = h(p1), h(p2)
                # Classify: if both houses are 1,5,9 or 1-10 → Maha; otherwise regular
                is_maha = (h1 in KENDRA | TRIKONA) and (h2 in KENDRA | TRIKONA)
                yoga_name = "Maha Parivartana Yoga" if is_maha else "Parivartana Yoga"
                yogas.append({
                    "name": f"{yoga_name} — {p1} ↔ {p2} (H{h1} ↔ H{h2})",
                    "description": (
                        f"{p1} in {SIGNS[p1_sign]} (H{h1}) exchanges signs with "
                        f"{p2} in {SIGNS[p2_sign]} (H{h2}) — "
                        "the two houses effectively merge energies; each planet gains the strength of both houses."
                    ),
                    "planets": [p1, p2],
                    "quality": "benefic"
                })

    # Deduplicate by name
    seen_names = set()
    unique_yogas = []
    for y in yogas:
        if y["name"] not in seen_names:
            seen_names.add(y["name"])
            unique_yogas.append(y)

    return unique_yogas


def format_yoga_block(yogas: list[dict]) -> str:
    """Format yoga list into a structured text block for the prompt."""
    if not yogas:
        return "ACTIVE YOGAS\nNone detected."

    benefic    = [y for y in yogas if y["quality"] == "benefic"]
    mixed      = [y for y in yogas if y["quality"] == "mixed"]
    challenging = [y for y in yogas if y["quality"] == "challenging"]

    lines = ["ACTIVE YOGAS & SPECIAL COMBINATIONS"]
    lines.append("")

    if benefic:
        lines.append("Gifts & Blessings:")
        for y in benefic:
            lines.append(f"  ✦ {y['name']}")
            lines.append(f"    {y['description']}")
        lines.append("")

    if mixed:
        lines.append("Latent Power (activated through challenge):")
        for y in mixed:
            lines.append(f"  ✦ {y['name']}")
            lines.append(f"    {y['description']}")
        lines.append("")

    if challenging:
        lines.append("Challenges to work with:")
        for y in challenging:
            lines.append(f"  ⚠ {y['name']}")
            lines.append(f"    {y['description']}")

    return "\n".join(lines)


# ─── System Prompt Template ───────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
You are a masterful Vedic astrology advisor (Jyotishi) with decades of experience \
in classical Parashari and Jaimini Jyotish. You have been given this person's complete \
birth chart, divisional charts, dasha timeline, and yoga profile. Every answer you \
give must be rooted in THEIR specific placements — never generic.

════════════════════════════════════════════════════════
BIRTH CHART DATA
════════════════════════════════════════════════════════
{chart_block}

════════════════════════════════════════════════════════
{dasha_block}
════════════════════════════════════════════════════════

{yoga_block}

════════════════════════════════════════════════════════
HOW TO RESPOND — READ THIS CAREFULLY
════════════════════════════════════════════════════════
1. ALWAYS anchor your answer in specific placements from this chart.
   Reference house numbers, signs, degrees, nakshatras, and dashas.

2. NEVER give a generic reading. If you cannot find the answer in
   the chart data above, say so honestly.

3. TIMING: When the user asks about timing or "when will X happen",
   reference the active Mahadasha and Antardasha periods above.
   Name the specific dasha period and explain WHY that planet's
   energy manifests as the user's described event.

4. CHALLENGES: When discussing difficult placements (debilitated
   planets, challenging yogas), always pair the difficulty with:
   a) What this placement is TEACHING the person
   b) A concrete remedy or reframe (ritual, behaviour, awareness)

5. STRENGTHS: When discussing gifts, show HOW to activate them
   practically — not just "you are creative" but "your Venus in H5
   activates through X, Y, Z specific actions."

6. NEECHA BHANGA & VIPARITA RAJA YOGAS are latent royal power
   that activates through adversity and reversal. When these planets
   are relevant to a question, frame challenges as the activation
   mechanism — the user's greatest difficulties are their launchpad.

7. PARIVARTANA YOGAS: Treat exchanged houses as merged — the person
   lives out BOTH house significations through each planet involved.

8. TONE: Speak like a wise elder who also understands modern life.
   Be direct and specific. Avoid vague spiritual filler.
   When asked "what should I do", give ACTUAL steps.

9. FOLLOW-UP: After answering, if the chart reveals something
   important the user hasn't asked about yet, gently flag it:
   "Your chart also shows something worth discussing about [X]..."

10. ASK BACK when the question is ambiguous:
    "Are you asking about [A] or [B]? Your chart speaks differently
    to each."
════════════════════════════════════════════════════════
"""


# ─── Master builder ───────────────────────────────────────────────────────────

def build_system_prompt(chart: dict, birth_dt: datetime, query_date: datetime = None) -> str:
    """
    Build the complete Claude system prompt from a calculated chart.

    Parameters
    ----------
    chart       : Output of vedic_calc.calculate_chart()
    birth_dt    : Actual birth datetime in UTC (for dasha timing)
    query_date  : The date for dasha calculation (default: today)

    Returns
    -------
    str — complete system prompt ready to pass to Claude API
    """
    if query_date is None:
        query_date = datetime.utcnow()

    from vedic_calc import format_for_prompt

    # Chart text block
    chart_block = format_for_prompt(chart)

    # Dasha block
    moon_lon  = chart["d1"]["Moon"]["sign_idx"] * 30 + chart["d1"]["Moon"]["degrees"]
    # Reconstruct full Moon longitude from sign + degrees
    moon_full_lon = chart["d1"]["Moon"]["sign_idx"] * 30 + chart["d1"]["Moon"]["degrees"]
    sequence     = calculate_vimshottari(moon_full_lon, birth_dt)
    dasha_block  = format_dasha_block(sequence, query_date)

    # Yoga block
    yogas      = detect_yogas(chart)
    yoga_block = format_yoga_block(yogas)

    return SYSTEM_PROMPT_TEMPLATE.format(
        chart_block=chart_block,
        dasha_block=dasha_block,
        yoga_block=yoga_block
    )


# ─── Quick test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from vedic_calc import calculate_chart

    # Oct 24, 1999 — 18:30 IST = 13:00 UTC — Nagpur (21.15N, 79.09E)
    birth_utc = datetime(1999, 10, 24, 13, 0, 0)
    chart = calculate_chart(birth_utc, lat=21.1458, lon=79.0882)

    prompt = build_system_prompt(
        chart,
        birth_dt=birth_utc,
        query_date=datetime(2026, 4, 1)
    )

    print(prompt[:6000])  # first 6000 chars
    print("\n... [truncated for display] ...\n")
    print(f"\nTotal system prompt length: {len(prompt)} characters / ~{len(prompt)//4} tokens")
