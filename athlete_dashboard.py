import io
import json
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Athlete Analytics Dashboard", layout="wide")

# NVIDIA AI API configuration
AI_API_KEY = os.getenv("NVIDIA_API_KEY", "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")
AI_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
AI_MODEL = "meta/llama-4-maverick-17b-128e-instruct"

# Custom color theme - vibrant and eye-catching
COLORS = {
    "primary": "#1E3A5F",      # Deep navy blue
    "secondary": "#FD7341",    # Vibrant orange
    "accent": "#00D4AA",       # Teal/mint
    "success": "#28A745",      # Green
    "warning": "#FFC107",      # Amber
    "danger": "#DC3545",       # Red
    "info": "#17A2B8",         # Cyan
    "light": "#F8F9FA",        # Light gray
    "dark": "#4DA3FA",         # Dark gray
    "valid": "#00D4AA",        # Teal for valid
    "flagged": "#FF6B35",      # Orange for flagged
    "chart_palette": ["#1E3A5F", "#FF6B35", "#00D4AA", "#FFC107", "#17A2B8", "#9B59B6", "#E91E63", "#00BCD4"]
}

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        background: linear-gradient(135deg, #1E3A5F 0%, #2E5A8F 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    .stMetric label {
        color: #00D4AA !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: white !important;
    }
    h1, h2, h3 {
        color: #1E3A5F;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 10px 20px;
        color: #1E3A5F;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B35 0%, #FF8C5A 100%) !important;
        color: white !important;
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

TIME_TESTS = {
    "thirtyMFlingStarts": {"label": "30m Sprint", "min": 1.5, "max": 15, "unit": "sec", "higher_better": False, "tooltip": "Elite youth sprinters achieve 3.5-5s; values <1.5s are unrealistic, >15s indicates measurement error or non-sprint activity."},
    "shuttleRun10MX6": {"label": "Shuttle Run 10M×6", "min": 8, "max": 50, "unit": "sec", "higher_better": False, "tooltip": "60m total distance with direction changes; <8s is physically impossible, >50s indicates recording issues or incomplete test."},
    "eightHundredMetersRun": {"label": "800m Run", "min": 90, "max": 600, "unit": "sec", "higher_better": False, "tooltip": "90s (1:30) is near world-class youth level; 600s (10 min) upper bound accounts for beginners and younger participants."},
}

DIST_TESTS = {
    "standingBroadJump": {"label": "Standing Broad Jump", "min": 100, "max": 350, "unit": "cm", "higher_better": True, "tooltip": "100cm is minimum for basic athletic ability; 350cm exceeds adult world records, so higher values indicate data entry errors."},
    "verticalJump": {"label": "Vertical Jump", "min": 10, "max": 300, "unit": "cm", "higher_better": True, "tooltip": "10cm minimum for any jump; 300cm is well above any recorded human jump (~90cm max), flagging measurement or unit errors."},
    "footballBallThrow5No": {"label": "Football Throw", "min": 1.5, "max": 15, "unit": "m", "higher_better": True, "tooltip": "1.5m minimum throw for basic arm strength; 15m is exceptional for youth athletes, higher values suggest unit confusion."},
}

BASIC_METRICS = {
    "height": {"label": "Height", "min": 130, "max": 185, "unit": "cm", "tooltip": "130cm covers younger participants (~8-10 yrs); 185cm upper limit as most youth athletes are below this height."},
    "weight": {"label": "Weight", "min": 28, "max": 85, "unit": "kg", "tooltip": "28kg minimum for ~8-10 year olds; 85kg upper bound for healthy athletic youth without extreme outliers."},
}

# Sports allowed for AI recommendation
ALLOWED_SPORTS = [
    "Archery", "Shooting", "Badminton", "Boxing", "Cycling", "Gymnastics",
    "Volleyball", "Fencing", "Judo", "Table Tennis", "Rowing", "Swimming",
    "Tennis", "Wrestling", "Weight Lifting", "Football", "Hockey", "Kabaddi",
    "Athletics", "Basketball"
]

# Performance band definitions
PERFORMANCE_BANDS = [
    {"label": "Top 5%",         "lo": 95, "hi": 100, "color": "#28A745"},  # Green
    {"label": "Good (5-20%)",   "lo": 80, "hi": 95,  "color": "#17A2B8"},  # Cyan
    {"label": "Above Avg (20-35%)", "lo": 65, "hi": 80, "color": "#FFC107"},  # Amber
    {"label": "Average (35-50%)", "lo": 50, "hi": 65,  "color": "#FF8C00"},  # Dark Orange
    {"label": "Below Avg (bottom 50%)", "lo": 0, "hi": 50, "color": "#DC3545"},  # Red
]

# Bihar district contextual insights for the Demographic tab
BIHAR_DISTRICT_INSIGHTS = {
    "Patna": {
        "gdp_per_capita": "₹1,12,000",
        "sports_infra": "High – Patliputra Sports Complex, indoor stadiums, SAI centre",
        "notable_athletes": "Sushil Modi (cricket), Mithali Raj grew up nearby",
        "insight": "State capital with best-funded sports infrastructure and coaching academies; higher GDP attracts private sports investment.",
    },
    "Gaya": {
        "gdp_per_capita": "₹52,000",
        "sports_infra": "Moderate – District stadium, school-level programmes",
        "notable_athletes": "Growing athletics talent pipeline",
        "insight": "Religious tourism economy; recent govt push for sports infra in Magadh division is yielding early results.",
    },
    "Muzaffarpur": {
        "gdp_per_capita": "₹48,000",
        "sports_infra": "Moderate – Litchi Bowl stadium, district sports authority active",
        "notable_athletes": "Strong wrestling and kabaddi tradition",
        "insight": "Agricultural prosperity funds grassroots sports; traditional wrestling akhadas produce robust athletes.",
    },
    "Bhagalpur": {
        "gdp_per_capita": "₹55,000",
        "sports_infra": "Moderate – Tilka Manjhi Stadium, rowing on the Ganges",
        "notable_athletes": "Silk-city rowing talent",
        "insight": "River access fosters rowing/swimming culture; emerging as Bihar's aquatic sports hub.",
    },
    "Purnia": {
        "gdp_per_capita": "₹40,000",
        "sports_infra": "Low-Moderate – District stadium, limited coaching",
        "notable_athletes": "Rural athletics talent",
        "insight": "Large rural population with natural endurance; players excel in long-distance running due to daily physical routines.",
    },
    "Darbhanga": {
        "gdp_per_capita": "₹42,000",
        "sports_infra": "Moderate – Mithila University sports grounds",
        "notable_athletes": "Cricket and athletics at university level",
        "insight": "University ecosystem provides structured coaching; cultural emphasis on education spills into disciplined training.",
    },
    "Begusarai": {
        "gdp_per_capita": "₹58,000",
        "sports_infra": "Low-Moderate – Industrial township sports clubs",
        "notable_athletes": "Industrial town produces disciplined athletes",
        "insight": "Industrial economy (refinery) funds CSR sports programmes; company-sponsored tournaments boost participation.",
    },
    "Munger": {
        "gdp_per_capita": "₹45,000",
        "sports_infra": "Low – Basic district facilities",
        "notable_athletes": "Yoga and martial arts traditions",
        "insight": "Bihar School of Yoga HQ; strong flexibility and body-control tradition translates to gymnastics aptitude.",
    },
    "Vaishali": {
        "gdp_per_capita": "₹38,000",
        "sports_infra": "Low – School-level only",
        "notable_athletes": "Grassroots kabaddi players",
        "insight": "Proximity to Patna allows talented athletes to access better coaching; agricultural background builds endurance.",
    },
    "Samastipur": {
        "gdp_per_capita": "₹36,000",
        "sports_infra": "Low – Railway sports club active",
        "notable_athletes": "Railway athletes contribute to district performance",
        "insight": "Railway-sector sports clubs provide structured competition; junction town attracts diverse talent.",
    },
    "Saran": {
        "gdp_per_capita": "₹39,000",
        "sports_infra": "Low-Moderate – District stadium, riverfront activities",
        "notable_athletes": "Strong sprint and throw talent",
        "insight": "Gandak-Ganga flood plain life builds physical resilience; athletes show above-average strength metrics.",
    },
    "East Champaran": {
        "gdp_per_capita": "₹32,000",
        "sports_infra": "Low – Very limited infrastructure",
        "notable_athletes": "Hockey tradition from sugarcane-belt",
        "insight": "Gandhian legacy district; sugarcane-field labour builds upper-body strength useful in throws and wrestling.",
    },
    "West Champaran": {
        "gdp_per_capita": "₹30,000",
        "sports_infra": "Low – Minimal formal facilities",
        "notable_athletes": "Border-area athletes with Nepal exposure",
        "insight": "Indo-Nepal border cultural exchange; exposure to Nepali martial arts traditions; raw athletic talent pool.",
    },
    "Nalanda": {
        "gdp_per_capita": "₹44,000",
        "sports_infra": "Moderate – University sports facilities, Rajgir hills",
        "notable_athletes": "Cycling and hill-running talent",
        "insight": "Rajgir hills provide natural altitude training; Nalanda University sports dept. produces coached athletes.",
    },
    "Aurangabad": {
        "gdp_per_capita": "₹35,000",
        "sports_infra": "Low – Basic school grounds",
        "notable_athletes": "Emerging talent in athletics",
        "insight": "Mining-region physical labour culture translates to raw power; untapped potential with proper coaching.",
    },
    "Rohtas": {
        "gdp_per_capita": "₹41,000",
        "sports_infra": "Low-Moderate – Sasaram stadium, hilly terrain",
        "notable_athletes": "Kaimur hills produce endurance athletes",
        "insight": "Hilly terrain of Kaimur range provides natural endurance training; army recruitment tradition drives fitness culture.",
    },
    "Katihar": {
        "gdp_per_capita": "₹34,000",
        "sports_infra": "Low – Railway grounds",
        "notable_athletes": "Railway-sponsored athletes",
        "insight": "Railway junction town; railway sports quota motivates youth; fertile agricultural base builds stamina.",
    },
    "Saharsa": {
        "gdp_per_capita": "₹31,000",
        "sports_infra": "Low – Very basic facilities",
        "notable_athletes": "Flood-zone resilient athletes",
        "insight": "Kosi river flood-zone life builds exceptional physical resilience and mental toughness.",
    },
    "Sitamarhi": {
        "gdp_per_capita": "₹29,000",
        "sports_infra": "Low – Minimal infrastructure",
        "notable_athletes": "Border-region talent",
        "insight": "Indo-Nepal border district; cross-border sports exchange; agricultural economy builds baseline fitness.",
    },
    "Madhubani": {
        "gdp_per_capita": "₹33,000",
        "sports_infra": "Low – Cultural focus over sports",
        "notable_athletes": "Art district with emerging sports interest",
        "insight": "Famous for Madhubani painting; recent govt sports schemes driving new participation; creative mindset aids strategic sports.",
    },
    "Siwan": {
        "gdp_per_capita": "₹35,000",
        "sports_infra": "Low – District stadium, school grounds",
        "notable_athletes": "Wrestling tradition in rural areas",
        "insight": "Strong diaspora-funded community programmes; remittance economy supports grassroots sports initiatives.",
    },
    "Gopalganj": {
        "gdp_per_capita": "₹33,000",
        "sports_infra": "Low – Basic district facilities",
        "notable_athletes": "Kabaddi and wrestling practitioners",
        "insight": "Agricultural district with traditional strength-sport culture; proximity to UP border enables inter-state competition.",
    },
    "Bhojpur": {
        "gdp_per_capita": "₹40,000",
        "sports_infra": "Low-Moderate – Arrah stadium, school sports",
        "notable_athletes": "Historical martial traditions",
        "insight": "Rich martial heritage of Bhojpur region; Ara district produces naturally strong athletes with wrestling aptitude.",
    },
    "Buxar": {
        "gdp_per_capita": "₹36,000",
        "sports_infra": "Low – Basic grounds, Ganga riverfront",
        "notable_athletes": "Rowing and swimming along the Ganga",
        "insight": "Historic battle site; military tradition drives fitness culture; river access promotes aquatic sports.",
    },
    "Madhepura": {
        "gdp_per_capita": "₹28,000",
        "sports_infra": "Low – Very limited infrastructure",
        "notable_athletes": "Resilient flood-zone athletes",
        "insight": "Kosi flood-prone area builds physical and mental toughness; untapped athletic talent in harsh conditions.",
    },
    "Araria": {
        "gdp_per_capita": "₹30,000",
        "sports_infra": "Low – School-level only",
        "notable_athletes": "Long-distance running talent",
        "insight": "Rural agrarian district; daily physical labour and long walking distances build natural endurance for athletics.",
    },
    "Kishanganj": {
        "gdp_per_capita": "₹27,000",
        "sports_infra": "Low – Minimal facilities",
        "notable_athletes": "Emerging football culture",
        "insight": "Northernmost Bihar district near Darjeeling foothills; tea-garden and hill exposure fosters stamina.",
    },
    "Supaul": {
        "gdp_per_capita": "₹29,000",
        "sports_infra": "Low – Very basic facilities",
        "notable_athletes": "Flood-resilient athletes",
        "insight": "Kosi river basin district; annual floods build exceptional survival fitness and mental toughness in youth.",
    },
    "Nawada": {
        "gdp_per_capita": "₹32,000",
        "sports_infra": "Low – District stadium only",
        "notable_athletes": "Emerging athletics talent",
        "insight": "Hilly terrain near Rajgir provides natural training ground; stone-quarry labour builds upper-body strength.",
    },
    "Jamui": {
        "gdp_per_capita": "₹30,000",
        "sports_infra": "Low – Forest-area limited access",
        "notable_athletes": "Tribal athletics traditions",
        "insight": "Significant tribal population with traditional physical games and hunting-gathering fitness; archery potential.",
    },
    "Jehanabad": {
        "gdp_per_capita": "₹34,000",
        "sports_infra": "Low – Small district, limited grounds",
        "notable_athletes": "Proximity to Patna aids coaching access",
        "insight": "Smallest districts by area; close proximity to Patna enables athletes to train at state-level facilities.",
    },
    "Arwal": {
        "gdp_per_capita": "₹31,000",
        "sports_infra": "Low – Newly formed district, minimal infra",
        "notable_athletes": "Developing sports ecosystem",
        "insight": "Bihar's newest and smallest district; developing infrastructure from scratch; agricultural background builds baseline fitness.",
    },
    "Banka": {
        "gdp_per_capita": "₹29,000",
        "sports_infra": "Low – School-level sports",
        "notable_athletes": "Rocky terrain produces endurance athletes",
        "insight": "Hilly and rocky terrain near Bhagalpur; natural obstacle-course-like environment builds agility and endurance.",
    },
    "Khagaria": {
        "gdp_per_capita": "₹30,000",
        "sports_infra": "Low – Flood-prone area limits infra",
        "notable_athletes": "River-belt swimming talent",
        "insight": "Ganga-Kosi confluence area; annual flooding cycle builds resilience; river culture promotes swimming and rowing.",
    },
    "Sheikhpura": {
        "gdp_per_capita": "₹33,000",
        "sports_infra": "Low – Very small district",
        "notable_athletes": "Close to Nalanda facilities",
        "insight": "One of Bihar's smallest districts; benefits from proximity to Nalanda's university sports infrastructure.",
    },
    "Sheohar": {
        "gdp_per_capita": "₹26,000",
        "sports_infra": "Low – Minimal, India's smallest district by area",
        "notable_athletes": "Emerging grassroots talent",
        "insight": "India's smallest district by area; extremely high population density drives competitive spirit; untapped potential.",
    },
    "Lakhisarai": {
        "gdp_per_capita": "₹32,000",
        "sports_infra": "Low – Basic district grounds",
        "notable_athletes": "Stone-quarry region strength athletes",
        "insight": "Industrial quarrying area; physical labour tradition produces strong athletes suited for throws and wrestling.",
    },
    "Kaimur": {
        "gdp_per_capita": "₹30,000",
        "sports_infra": "Low – Hilly terrain, limited access",
        "notable_athletes": "Hill-running and endurance traditions",
        "insight": "Kaimur plateau provides natural altitude training; forest-dwelling communities have exceptional endurance and agility.",
    },
}


def compute_performance_bands(series: pd.Series, higher_better: bool) -> pd.DataFrame:
    """Assign each value in *series* to a performance band based on percentiles.

    Returns a DataFrame with columns ['Band', 'Count'] ordered from top to bottom.
    """
    clean = series.dropna()
    if clean.empty:
        return pd.DataFrame(columns=["Band", "Count", "Color"])

    rows = []
    for band in PERFORMANCE_BANDS:
        lo_val = np.percentile(clean, band["lo"] if higher_better else 100 - band["hi"])
        hi_val = np.percentile(clean, band["hi"] if higher_better else 100 - band["lo"])

        if higher_better:
            count = int(((clean >= lo_val) & (clean <= hi_val)).sum())
        else:
            count = int(((clean >= lo_val) & (clean <= hi_val)).sum())

        rows.append({"Band": band["label"], "Count": count, "Color": band["color"]})

    return pd.DataFrame(rows)

# Data cleaning documentation
DATA_CLEANING_DOCS = [
    {"Field": "Height", "Original Unit": "cm", "Cleaning Applied": "Convert to numeric; flag missing values", "Valid Range": "130-185 cm", "Rationale": "Covers typical youth athlete heights; values outside indicate entry errors or non-target population."},
    {"Field": "Weight", "Original Unit": "kg", "Cleaning Applied": "Convert to numeric; flag missing values", "Valid Range": "28-85 kg", "Rationale": "Healthy weight range for youth athletes aged 8-18 years."},
    {"Field": "BMI", "Original Unit": "kg/m²", "Cleaning Applied": "Calculated from height & weight; flagged if <14 or >35", "Valid Range": "14-35", "Rationale": "BMI <14 indicates underweight/error; >35 indicates obesity or measurement issues."},
    {"Field": "Standing Broad Jump", "Original Unit": "cm or m", "Cleaning Applied": "If value <10, treat as meters and convert to cm (×100)", "Valid Range": "100-350 cm", "Rationale": "Values <10 likely recorded in meters; 350cm exceeds world records."},
    {"Field": "Vertical Jump", "Original Unit": "cm or m", "Cleaning Applied": "If value <4, treat as meters and convert to cm (×100)", "Valid Range": "10-300 cm", "Rationale": "Values <4 likely recorded in meters; 300cm is well above max human capability."},
    {"Field": "Football Throw", "Original Unit": "m or cm", "Cleaning Applied": "If value >15, treat as cm and convert to meters (÷100)", "Valid Range": "1.5-15 m", "Rationale": "Values >15 likely recorded in cm; 15m is exceptional for youth."},
    {"Field": "30m Sprint", "Original Unit": "sec", "Cleaning Applied": "Convert to numeric; flag out-of-range", "Valid Range": "1.5-15 sec", "Rationale": "<1.5s is physically impossible; >15s indicates measurement error."},
    {"Field": "Shuttle Run 10M×6", "Original Unit": "sec", "Cleaning Applied": "Convert to numeric; flag out-of-range", "Valid Range": "8-50 sec", "Rationale": "<8s impossible for 60m with turns; >50s indicates incomplete test."},
    {"Field": "800m Run", "Original Unit": "sec or mm:ss", "Cleaning Applied": "Parse time formats: '0x:0y:00', '00:0x:0y', '0x:0y' all treated as x min y sec; convert to total seconds", "Valid Range": "90-600 sec", "Rationale": "90s near elite youth; 600s (10 min) allows for beginners."},
]

ALL_TESTS = {**TIME_TESTS, **DIST_TESTS}


def build_configs_from_ui() -> Tuple[Dict[str, Dict], Dict[str, Dict], Dict[str, Dict], Dict[str, Dict]]:
    st.sidebar.header("Range Configuration")
    st.sidebar.caption("Adjust valid ranges and analytics will refresh.")

    basic_cfg = {k: v.copy() for k, v in BASIC_METRICS.items()}
    time_cfg = {k: v.copy() for k, v in TIME_TESTS.items()}
    dist_cfg = {k: v.copy() for k, v in DIST_TESTS.items()}

    with st.sidebar.expander("Basic metrics", expanded=False):
        for metric, cfg in basic_cfg.items():
            c1, c2 = st.columns(2)
            cfg["min"] = c1.number_input(f"{cfg['label']} min", value=float(cfg["min"]), key=f"min_{metric}", help=cfg.get("tooltip", ""))
            cfg["max"] = c2.number_input(f"{cfg['label']} max", value=float(cfg["max"]), key=f"max_{metric}", help=cfg.get("tooltip", ""))

    with st.sidebar.expander("Battery tests", expanded=False):
        for metric, cfg in {**time_cfg, **dist_cfg}.items():
            c1, c2 = st.columns(2)
            cfg["min"] = c1.number_input(f"{cfg['label']} min", value=float(cfg["min"]), key=f"min_{metric}", help=cfg.get("tooltip", ""))
            cfg["max"] = c2.number_input(f"{cfg['label']} max", value=float(cfg["max"]), key=f"max_{metric}", help=cfg.get("tooltip", ""))

    all_tests_cfg = {**time_cfg, **dist_cfg}
    return basic_cfg, time_cfg, dist_cfg, all_tests_cfg


def parse_800m_time(value) -> Tuple[Optional[float], bool, Optional[str]]:
    if pd.isna(value):
        return None, False, "Missing"

    text = str(value).strip()
    if not text:
        return None, False, "Missing"

    try:
        if ":" not in text:
            numeric = float(text)
            if 90 <= numeric <= 600:
                return numeric, True, None
            return numeric, False, f"Out of range ({numeric}s)"
    except Exception:
        pass

    try:
        parts = text.split(":")
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
        elif len(parts) == 3:
            p1, p2, p3 = int(parts[0]), int(parts[1]), int(parts[2])
            if p1 == 0:
                minutes, seconds = p2, p3
            else:
                minutes, seconds = p1, p2
        else:
            return None, False, f"Invalid format ({text})"

        total_seconds = minutes * 60 + seconds
        if 90 <= total_seconds <= 600:
            return float(total_seconds), True, None
        return float(total_seconds), False, f"Out of range ({total_seconds}s)"
    except Exception:
        return None, False, f"Parse error ({text})"


def convert_standing_broad_jump(value):
    if pd.isna(value):
        return value
    return value * 100 if value < 10 else value


def convert_vertical_jump(value):
    if pd.isna(value):
        return value
    return value * 100 if value < 4 else value


def convert_football_throw(value):
    if pd.isna(value):
        return value
    return value / 100 if value > 15 else value


def classify_bmi(height_cm, weight_kg):
    if pd.isna(height_cm) or pd.isna(weight_kg) or height_cm <= 0:
        return np.nan, "Missing"
    bmi = weight_kg / ((height_cm / 100) ** 2)
    if bmi < 14:
        return bmi, "Too Low"
    if bmi > 35:
        return bmi, "Too High"
    return bmi, "Valid"


def process_data(uploaded_bytes: bytes, filename: str, basic_cfg: Dict[str, Dict], all_tests_cfg: Dict[str, Dict]):
    source = io.BytesIO(uploaded_bytes)
    if filename.lower().endswith(".xlsx"):
        df = pd.read_excel(source)
    else:
        df = pd.read_csv(source)

    working = df.copy()
    
    # Track cleaning counts
    cleaning_counts = {
        "standingBroadJump_converted": 0,
        "verticalJump_converted": 0,
        "footballBallThrow_converted": 0,
        "eightHundredMetersRun_parsed": 0,
        "height_flagged": 0,
        "weight_flagged": 0,
        "bmi_flagged": 0,
    }

    for col in ["standingBroadJump", "verticalJump", "footballBallThrow5No", "eightHundredMetersRun"]:
        if col in working.columns:
            working[f"{col}_original"] = working[col]

    if "standingBroadJump" in working.columns:
        original_vals = pd.to_numeric(working["standingBroadJump"], errors="coerce")
        cleaning_counts["standingBroadJump_converted"] = int((original_vals < 10).sum())
        working["standingBroadJump"] = original_vals.apply(convert_standing_broad_jump)
    if "verticalJump" in working.columns:
        original_vals = pd.to_numeric(working["verticalJump"], errors="coerce")
        cleaning_counts["verticalJump_converted"] = int((original_vals < 4).sum())
        working["verticalJump"] = original_vals.apply(convert_vertical_jump)
    if "footballBallThrow5No" in working.columns:
        original_vals = pd.to_numeric(working["footballBallThrow5No"], errors="coerce")
        cleaning_counts["footballBallThrow_converted"] = int((original_vals > 15).sum())
        working["footballBallThrow5No"] = original_vals.apply(convert_football_throw)

    if "eightHundredMetersRun" in working.columns:
        parsed = working["eightHundredMetersRun"].apply(parse_800m_time)
        working["eightHundredMetersRun_seconds"] = parsed.apply(lambda x: x[0])
        working["eightHundredMetersRun_valid"] = parsed.apply(lambda x: x[1])
        working["eightHundredMetersRun_error"] = parsed.apply(lambda x: x[2])
        # Count time format conversions (those with ":" in original)
        cleaning_counts["eightHundredMetersRun_parsed"] = int(working["eightHundredMetersRun"].astype(str).str.contains(":", na=False).sum())
        working["eightHundredMetersRun"] = working["eightHundredMetersRun_seconds"]

    for col in ["height", "weight", "thirtyMFlingStarts", "shuttleRun10MX6", "standingBroadJump", "verticalJump", "footballBallThrow5No"]:
        if col in working.columns:
            working[col] = pd.to_numeric(working[col], errors="coerce")

    bmi_calc = working.apply(lambda r: classify_bmi(r.get("height"), r.get("weight")), axis=1)
    working["bmi"] = bmi_calc.apply(lambda x: x[0])
    working["bmi_status"] = bmi_calc.apply(lambda x: x[1])

    issue_rows = []
    issue_counts: Dict[str, int] = {}

    def add_issue(idx, issue_type, value, reason):
        issue_rows.append({
            "RowIndex": idx,
            "Sl_no": working.iloc[idx].get("Sl no"),
            "Student_Name": working.iloc[idx].get("studentName"),
            "IssueType": issue_type,
            "Value": value,
            "Reason": reason,
        })
        issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

    for idx, row in working.iterrows():
        for metric, cfg in basic_cfg.items():
            if metric not in working.columns:
                continue
            value = row.get(metric)
            if pd.isna(value):
                add_issue(idx, f"{cfg['label']} Missing", value, "Missing")
            elif value < cfg["min"] or value > cfg["max"]:
                add_issue(idx, f"{cfg['label']} Out of Range", value, f"Valid range: {cfg['min']}-{cfg['max']} {cfg['unit']}")

        if row.get("bmi_status") == "Too Low":
            add_issue(idx, "BMI Too Low", row.get("bmi"), "BMI < 14")
        elif row.get("bmi_status") == "Too High":
            add_issue(idx, "BMI Too High", row.get("bmi"), "BMI > 35")

        for metric, cfg in all_tests_cfg.items():
            if metric not in working.columns:
                continue
            value = row.get(metric)
            if pd.isna(value):
                add_issue(idx, f"{cfg['label']} Missing", value, "Missing")
            elif value < cfg["min"] or value > cfg["max"]:
                add_issue(idx, f"{cfg['label']} Out of Range", value, f"Valid range: {cfg['min']}-{cfg['max']} {cfg['unit']}")

    issue_df = pd.DataFrame(issue_rows)

    valid_masks = {}
    for metric, cfg in all_tests_cfg.items():
        if metric in working.columns:
            valid_masks[metric] = working[metric].between(cfg["min"], cfg["max"], inclusive="both")

    valid_masks["height"] = working["height"].between(basic_cfg["height"]["min"], basic_cfg["height"]["max"], inclusive="both") if "height" in working.columns else pd.Series(False, index=working.index)
    valid_masks["weight"] = working["weight"].between(basic_cfg["weight"]["min"], basic_cfg["weight"]["max"], inclusive="both") if "weight" in working.columns else pd.Series(False, index=working.index)
    
    # Count flagged height/weight
    if "height" in working.columns:
        cleaning_counts["height_flagged"] = int((~valid_masks["height"]).sum())
    if "weight" in working.columns:
        cleaning_counts["weight_flagged"] = int((~valid_masks["weight"]).sum())
    cleaning_counts["bmi_flagged"] = int((working["bmi_status"] != "Valid").sum())

    score_components = []
    for metric, cfg in all_tests_cfg.items():
        if metric not in working.columns:
            continue
        s = working[metric]
        rank = s.rank(pct=True, ascending=not cfg["higher_better"])
        score_components.append(rank)

    if "height" in working.columns:
        h_med = working.loc[valid_masks["height"], "height"].median()
        h_dev = (working["height"] - h_med).abs()
        score_components.append(1 - (h_dev / h_dev.max()).fillna(0))
    if "weight" in working.columns:
        w_med = working.loc[valid_masks["weight"], "weight"].median()
        w_dev = (working["weight"] - w_med).abs()
        score_components.append(1 - (w_dev / w_dev.max()).fillna(0))

    if score_components:
        scores = pd.concat(score_components, axis=1).mean(axis=1, skipna=True)
    else:
        scores = pd.Series(0, index=working.index)

    working["overall_score"] = scores

    top10 = working.sort_values("overall_score", ascending=False).head(10).copy()

    duplicates = pd.DataFrame()
    if "studentName" in working.columns:
        name_counts = working["studentName"].value_counts()
        duplicates = name_counts[name_counts > 1].reset_index()
        duplicates.columns = ["Student_Name", "Count"]

    return {
        "raw": df,
        "working": working,
        "issues": issue_df,
        "issue_counts": issue_counts,
        "valid_masks": valid_masks,
        "duplicates": duplicates,
        "top10": top10,
        "cleaning_counts": cleaning_counts,
    }


def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()


def call_ai_recommendation(row: pd.Series, api_key: str, model_name: str = AI_MODEL) -> str:
    """Call NVIDIA AI API for sports recommendation (OpenAI-compatible format)."""
    fields = [
        "height", "weight", "bmi", "thirtyMFlingStarts", "shuttleRun10MX6",
        "standingBroadJump", "verticalJump", "footballBallThrow5No", "eightHundredMetersRun"
    ]
    profile = {k: row.get(k) for k in fields}

    sports_list = ", ".join(ALLOWED_SPORTS)

    prompt = (
        "You are a youth sports performance analyst. Based on the athlete metrics below, "
        "recommend top 3 sports from ONLY the following list and explain why in practical terms.\n\n"
        f"ALLOWED SPORTS (choose only from these): {sports_list}\n\n"
        f"Athlete data: {profile}\n\n"
        "Output format:\n"
        "1) Sport - reason (2-3 sentences explaining why this athlete's metrics suit this sport)\n"
        "2) Sport - reason (2-3 sentences)\n"
        "3) Sport - reason (2-3 sentences)\n\n"
        "Then one short section: 'Improvement focus' with 2-3 actionable suggestions."
    )

    response = requests.post(
        AI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": f"You provide sports talent recommendations using physical test metrics. You must ONLY recommend sports from this list: {sports_list}. Do not recommend any sport outside this list."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
            "temperature": 1.0,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "stream": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


logo_col, title_col = st.columns([0.10, 0.90])
with logo_col:
    logo_path = Path(__file__).parent / "BSSA_logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=200)
with title_col:
    st.title("🏃 Mashal Athlete Interactive Analytics Dashboard")
    st.write("Upload your Excel/CSV file to start analytics.")

# ── Session-based auto-load (Data Collection app integration) ─────────────
# When the Flutter Data Collection app opens this dashboard with ?session=<id>,
# the CSV is fetched from the companion API server instead of requiring a file
# upload.  The file uploader is shown as a fallback for standalone use.
_session_id: str = st.query_params.get("session", "")
_session_bytes: Optional[bytes] = None
_default_name: Optional[str] = None

if _session_id:
    try:
        _resp = requests.get(
            f"http://localhost:8502/sessions/{_session_id}",
            timeout=5,
        )
        if _resp.ok:
            _session_bytes = _resp.json()["csv"].encode("utf-8")
        else:
            st.warning(
                f"⚠️ Could not retrieve session data (HTTP {_resp.status_code}). "
                "Please upload a file manually."
            )
    except Exception as _exc:
        st.warning(
            f"⚠️ Analytics session service unreachable: {_exc}. "
            "Please upload a file manually."
        )

# Bundled dataset that is loaded by default when no session or upload is given.
DEFAULT_DATA_PATH = Path(__file__).parent / "Athlete_10000_augmented.xlsx"

if _session_bytes:
    # Running in integrated mode — no file upload needed
    st.info("📊 Live data loaded from the Data Collection app.")
    uploaded = None
else:
    uploaded = st.file_uploader(
        "Select athlete file (optional — replaces the default dataset)",
        type=["xlsx", "csv"],
    )
    if not uploaded and DEFAULT_DATA_PATH.exists():
        _session_bytes = DEFAULT_DATA_PATH.read_bytes()
        _default_name = DEFAULT_DATA_PATH.name
        st.info(f"📁 Showing the default dataset: `{_default_name}`. Upload a file to use different data.")

if not _session_bytes and not uploaded:
    st.info("Please upload an `.xlsx` or `.csv` file to begin.")
    st.stop()

basic_cfg, time_cfg, dist_cfg, all_tests_cfg = build_configs_from_ui()

with st.spinner("Processing data and preparing analytics..."):
    if _session_bytes:
        processed = process_data(
            _session_bytes,
            _default_name if _default_name else "live_data.csv",
            basic_cfg,
            all_tests_cfg,
        )
    else:
        processed = process_data(uploaded.getvalue(), uploaded.name, basic_cfg, all_tests_cfg)

st.success("Analytics is now ready ✅")

working = processed["working"]
issues = processed["issues"]
valid_masks = processed["valid_masks"]

# ── Insights toggle (sidebar) ─────────────────────────────────────────
has_insights_cols = all(c in working.columns for c in ["gender", "age", "district"])
if has_insights_cols:
    st.sidebar.markdown("---")
    enable_insights = st.sidebar.checkbox("🔍 Enable Insights Tab", value=False,
                                          help="Toggle the Gender / Age / Demographic insights panel on or off.")
else:
    enable_insights = False

tab_names = ["Participants", "Data Cleaning", "Battery Tests", "Data Quality", "Athlete Profiling"]
if enable_insights:
    tab_names.append("🔍 Insights")

main_tabs = st.tabs(tab_names)

with main_tabs[0]:
    st.subheader("Participants Overview")
    col1, col2 = st.columns(2)
    col1.metric("Total Participants", f"{len(working):,}", help="Total number of athlete records found in the uploaded file.")
    col2.metric("Total Battery Tests", len(all_tests_cfg), help="Number of distinct physical tests being analysed (sprint, jump, throw, run, etc.).")

    test_table = pd.DataFrame([
        {
            "Test": cfg["label"],
            "Column": metric,
            "Valid Range": f"{cfg['min']} - {cfg['max']} {cfg['unit']}",
            "Type": "Distance" if cfg["higher_better"] else "Time",
        }
        for metric, cfg in all_tests_cfg.items()
    ])
    st.markdown("### Battery Tests Included")
    st.dataframe(test_table, use_container_width=True)

    bmi_valid = working[working["bmi_status"] == "Valid"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Valid Avg BMI", f"{round(bmi_valid['bmi'].mean(), 2)} kg/m²" if not bmi_valid.empty else "NA", help="Average BMI computed only from participants whose BMI falls within the valid range (14–35). Excludes missing, too-low, and too-high BMI entries.")
    c2.metric("Valid Avg Height", f"{round(working.loc[valid_masks.get('height', pd.Series(False, index=working.index)), 'height'].mean(), 2)} cm", help=f"Average height (cm) computed only from participants within the valid height range ({basic_cfg['height']['min']}–{basic_cfg['height']['max']} cm). Outliers excluded.")
    c3.metric("Valid Avg Weight", f"{round(working.loc[valid_masks.get('weight', pd.Series(False, index=working.index)), 'weight'].mean(), 2)} kg", help=f"Average weight (kg) computed only from participants within the valid weight range ({basic_cfg['weight']['min']}–{basic_cfg['weight']['max']} kg). Outliers excluded.")

    st.markdown("### Quick Visuals")
    # BMI Status Distribution - Pie chart with custom colors
    bmi_count = working["bmi_status"].value_counts().rename_axis("BMI_Status").reset_index(name="Count")
    fig_bmi_pie = px.pie(bmi_count, names="BMI_Status", values="Count", title="BMI Status Distribution", 
                          hole=0.4, color_discrete_sequence=COLORS["chart_palette"])
    fig_bmi_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_bmi_pie.update_layout(font=dict(size=14), title_font_size=18)
    st.plotly_chart(fig_bmi_pie, use_container_width=True, key="participants-bmi-status")

    # Grouped bar chart for Valid vs Flagged entries per test (including height & weight)
    coverage_rows = []
    for metric, cfg in basic_cfg.items():
        if metric in working.columns:
            valid_count = int(valid_masks.get(metric, pd.Series(False, index=working.index)).sum())
            coverage_rows.append({"Test": cfg["label"], "Valid": valid_count, "Flagged": len(working) - valid_count})
    for metric, cfg in all_tests_cfg.items():
        if metric in working.columns:
            valid_count = int(valid_masks.get(metric, pd.Series(False, index=working.index)).sum())
            coverage_rows.append({"Test": cfg["label"], "Valid": valid_count, "Flagged": len(working) - valid_count})
    if coverage_rows:
        coverage_df = pd.DataFrame(coverage_rows)
        _total_athletes = len(working)
        _valid_labels = [f"{v} ({v/_total_athletes*100:.1f}%)" for v in coverage_df['Valid']]
        _flagged_labels = [f"{f} ({f/_total_athletes*100:.1f}%)" for f in coverage_df['Flagged']]
        fig_coverage = go.Figure()
        fig_coverage.add_trace(go.Bar(name='Valid', x=coverage_df['Test'], y=coverage_df['Valid'], 
                                       marker_color=COLORS['valid'], text=_valid_labels, textposition='auto'))
        fig_coverage.add_trace(go.Bar(name='Flagged', x=coverage_df['Test'], y=coverage_df['Flagged'], 
                                       marker_color=COLORS['flagged'], text=_flagged_labels, textposition='auto'))
        fig_coverage.update_layout(barmode='group', title='Valid vs Flagged Entries by Test',
                                    xaxis_title='Test', yaxis_title='Count',
                                    font=dict(size=12), title_font_size=18,
                                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
        st.plotly_chart(
            fig_coverage,
            use_container_width=True,
            key="participants-valid-flagged-coverage",
        )

with main_tabs[2]:
    st.subheader("Battery Tests")
    test_tabs = st.tabs([cfg["label"] for cfg in all_tests_cfg.values()])

    for (metric, cfg), tab in zip(all_tests_cfg.items(), test_tabs):
        with tab:
            if metric not in working.columns:
                st.warning(f"Column `{metric}` not found in uploaded data.")
                continue

            mask = valid_masks.get(metric, pd.Series(False, index=working.index))
            valid_df = working[mask].copy()

            total_participants = len(working)
            total_valid = len(valid_df)
            valid_avg = valid_df[metric].mean() if total_valid else np.nan

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Participants", total_participants, help="Total number of athlete records in the uploaded dataset.")
            m2.metric("Total Valid Entries", total_valid, help=f"Participants whose {cfg['label']} value falls within the valid range ({cfg['min']}–{cfg['max']} {cfg['unit']}). Missing and out-of-range entries are excluded.")
            m3.metric("Valid Range", f"{cfg['min']} - {cfg['max']} {cfg['unit']}", help=cfg.get("tooltip", ""))
            st.metric("Average (valid entries)", f"{round(valid_avg, 2)} {cfg['unit']}" if pd.notna(valid_avg) else "NA", help=f"Arithmetic mean of {cfg['label']} computed only from the {total_valid} valid entries ({cfg['unit']}). Out-of-range and missing values are excluded from this calculation.")

            # Performance band distribution – shown FIRST
            if total_valid:
                band_df = compute_performance_bands(valid_df[metric], cfg["higher_better"])
                if not band_df.empty:
                    # Compute cutoff values for x-axis labels
                    clean_vals = valid_df[metric].dropna()
                    band_labels_with_cutoff = []
                    for band in PERFORMANCE_BANDS:
                        lo_val = np.percentile(clean_vals, band["lo"] if cfg["higher_better"] else 100 - band["hi"])
                        hi_val = np.percentile(clean_vals, band["hi"] if cfg["higher_better"] else 100 - band["lo"])
                        if cfg["higher_better"]:
                            band_labels_with_cutoff.append(f"{band['label']}<br>(≥{lo_val:.2f} {cfg['unit']})")
                        else:
                            band_labels_with_cutoff.append(f"{band['label']}<br>(≤{hi_val:.2f} {cfg['unit']})")

                    fig_band = go.Figure()
                    fig_band.add_trace(go.Bar(
                        x=band_labels_with_cutoff,
                        y=band_df["Count"],
                        marker_color=band_df["Color"].tolist(),
                        text=band_df["Count"],
                        textposition="auto",
                        textfont=dict(size=18, color="white"),
                    ))
                    fig_band.update_layout(
                        title=f"{cfg['label']} – Performance Band Distribution ({cfg['unit']})",
                        xaxis_title="Performance Band",
                        yaxis_title="Number of Athletes",
                        font=dict(size=12),
                        title_font_size=16,
                    )
                    st.plotly_chart(
                        fig_band,
                        use_container_width=True,
                        key=f"battery-{metric}-performance-bands",
                    )

            # Valid vs Flagged pie chart – shown AFTER bands
            vis_df = pd.DataFrame({"Category": ["Valid", "Flagged"], "Count": [total_valid, total_participants - total_valid]})
            fig_valid_pie = px.pie(vis_df, names="Category", values="Count", title="Valid vs Flagged Entries", 
                                   hole=0.4, color="Category", color_discrete_map={"Valid": COLORS["valid"], "Flagged": COLORS["flagged"]})
            fig_valid_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_valid_pie.update_layout(font=dict(size=14), title_font_size=18)
            st.plotly_chart(
                fig_valid_pie,
                use_container_width=True,
                key=f"battery-{metric}-valid-flagged-pie",
            )

            if total_valid:
                if cfg["higher_better"]:
                    cutoff = valid_df[metric].quantile(0.95)
                    top_5 = valid_df[valid_df[metric] >= cutoff].copy()
                else:
                    cutoff = valid_df[metric].quantile(0.05)
                    top_5 = valid_df[valid_df[metric] <= cutoff].copy()

                st.metric("Top 5% Cutoff", f"{round(cutoff, 2)} {cfg['unit']}")
                _top5_show_cols = [c for c in ["Sl no", "studentName", metric] if c in top_5.columns]
                st.dataframe(top_5[_top5_show_cols].head(10), use_container_width=True)
                st.caption(f"Showing up to 10 of {len(top_5)} top 5% athletes. Download full list below.")
                st.download_button(
                    f"Download top 5% ({cfg['label']})",
                    data=df_to_xlsx_bytes(top_5, f"Top5_{metric}"),
                    file_name=f"top5_{metric}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{metric}",
                )

with main_tabs[1]:
    st.subheader("Data Cleaning Documentation")
    st.write("This section documents all data cleaning and transformation rules applied to the raw data before analysis.")
    
    cleaning_counts = processed["cleaning_counts"]

    st.markdown("### Cleaning & Transformation Rules")
    st.info("ℹ️ Values outside the valid range are flagged as data quality issues but retained for review. Adjust ranges in the sidebar.")
    
    # Add counts to cleaning docs
    cleaning_docs_with_counts = []
    for doc in DATA_CLEANING_DOCS:
        doc_copy = doc.copy()
        field = doc["Field"]
        if field == "Standing Broad Jump":
            doc_copy["Records Cleaned"] = cleaning_counts.get("standingBroadJump_converted", 0)
        elif field == "Vertical Jump":
            doc_copy["Records Cleaned"] = cleaning_counts.get("verticalJump_converted", 0)
        elif field == "Football Throw":
            doc_copy["Records Cleaned"] = cleaning_counts.get("footballBallThrow_converted", 0)
        elif field == "800m Run":
            doc_copy["Records Cleaned"] = cleaning_counts.get("eightHundredMetersRun_parsed", 0)
        elif field == "Height":
            doc_copy["Records Cleaned"] = cleaning_counts.get("height_flagged", 0)
        elif field == "Weight":
            doc_copy["Records Cleaned"] = cleaning_counts.get("weight_flagged", 0)
        elif field == "BMI":
            doc_copy["Records Cleaned"] = cleaning_counts.get("bmi_flagged", 0)
        else:
            doc_copy["Records Cleaned"] = 0
        cleaning_docs_with_counts.append(doc_copy)
    
    cleaning_df = pd.DataFrame(cleaning_docs_with_counts)
    cleaning_df.index = range(1, len(cleaning_df) + 1)
    cleaning_df.index.name = "#"
    st.dataframe(cleaning_df, use_container_width=True)
    
    # Cleaning summary visualization
    st.markdown("### Cleaning Actions Summary")
    summary_data = [
        {"Action": "Standing Broad Jump (m→cm)", "Records": cleaning_counts.get("standingBroadJump_converted", 0)},
        {"Action": "Vertical Jump (m→cm)", "Records": cleaning_counts.get("verticalJump_converted", 0)},
        {"Action": "Football Throw (cm→m)", "Records": cleaning_counts.get("footballBallThrow_converted", 0)},
        {"Action": "800m Time Parsing", "Records": cleaning_counts.get("eightHundredMetersRun_parsed", 0)},
        {"Action": "Height Flagged", "Records": cleaning_counts.get("height_flagged", 0)},
        {"Action": "Weight Flagged", "Records": cleaning_counts.get("weight_flagged", 0)},
        {"Action": "BMI Flagged", "Records": cleaning_counts.get("bmi_flagged", 0)},
    ]
    summary_df = pd.DataFrame(summary_data)
    fig_cleaning = px.bar(summary_df, x="Records", y="Action", orientation='h', 
                          title="Records Cleaned/Flagged by Action",
                          color_discrete_sequence=[COLORS["secondary"]])
    fig_cleaning.update_layout(font=dict(size=12), title_font_size=18, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_cleaning, use_container_width=True, key="cleaning-actions-summary")

    st.markdown("### Detailed Transformation Logic")

    with st.expander("Standing Broad Jump Conversion", expanded=False):
        st.markdown("""
        **Problem:** Data collected in mixed units (some in meters, some in cm).
        
        **Rule:** If value < 10, assume it's in meters and convert to cm (×100)
        
        **Example:**
        - Input: `2.35` → Output: `235 cm` (converted from meters)
        - Input: `180` → Output: `180 cm` (already in cm)
        """)

    with st.expander("Vertical Jump Conversion", expanded=False):
        st.markdown("""
        **Problem:** Data collected in mixed units (some in meters, some in cm).
        
        **Rule:** If value < 4, assume it's in meters and convert to cm (×100)
        
        **Example:**
        - Input: `0.65` → Output: `65 cm` (converted from meters)
        - Input: `55` → Output: `55 cm` (already in cm)
        """)

    with st.expander("Football Throw Conversion", expanded=False):
        st.markdown("""
        **Problem:** Data collected in mixed units (some in meters, some in cm).
        
        **Rule:** If value > 15, assume it's in cm and convert to meters (÷100)
        
        **Example:**
        - Input: `850` → Output: `8.5 m` (converted from cm)
        - Input: `12.5` → Output: `12.5 m` (already in meters)
        """)

    with st.expander("800m Run Time Parsing", expanded=False):
        st.markdown("""
        **Problem:** Time recorded in multiple formats (mm:ss, 0m:0s:00, 00:mm:ss, or raw seconds).
        
        **Parsing Rules:**
        - Format `0x:0y:00` → x minutes, y seconds
        - Format `00:0x:0y` → x minutes, y seconds  
        - Format `0x:0y` → x minutes, y seconds
        - Raw numeric (90-600) → already in seconds
        
        **Example:**
        - Input: `03:45:00` → Output: `225 sec` (3 min 45 sec)
        - Input: `00:03:45` → Output: `225 sec` (3 min 45 sec)
        - Input: `3:45` → Output: `225 sec` (3 min 45 sec)
        - Input: `225` → Output: `225 sec` (already in seconds)
        """)

    with st.expander("BMI Calculation & Validation", expanded=False):
        st.markdown("""
        **Calculation:** BMI = Weight (kg) / (Height (m))²
        
        **Validation Rules:**
        - BMI < 14 → Flagged as "Too Low" (likely data error or severe underweight)
        - BMI > 35 → Flagged as "Too High" (likely data error or obesity)
        - 14 ≤ BMI ≤ 35 → Valid range for youth athletes
        
        **Missing Data:** If height or weight is missing, BMI cannot be calculated.
        """)

with main_tabs[3]:
    st.subheader("Data Quality")

    # ── Quality Breakdown by Category ─────────────────────────────────
    st.markdown("### Quality Breakdown by Category")
    counts = processed["issue_counts"]
    if counts:
        cat_df = pd.DataFrame(
            [{"Category": k, "Count": v} for k, v in counts.items()]
        ).sort_values("Count", ascending=True)
        cat_df["Percentage"] = (cat_df["Count"] / len(working) * 100).round(2)
        st.dataframe(cat_df.sort_values("Count", ascending=False), use_container_width=True)

        # Horizontal bar chart – consistent indicator colors
        max_scale = max(5000, cat_df["Count"].max() + 500)
        # Map each category to a consistent color from the chart palette
        _indicator_color_map = {}
        for i, cat_name in enumerate(cat_df["Category"].unique()):
            _indicator_color_map[cat_name] = COLORS["chart_palette"][i % len(COLORS["chart_palette"])]
        bar_colors = [_indicator_color_map[c] for c in cat_df["Category"]]

        fig_quality = go.Figure()
        fig_quality.add_trace(go.Bar(
            x=cat_df["Count"],
            y=cat_df["Category"],
            orientation='h',
            marker_color=bar_colors,
            text=[f"← {count:,} ({pct:.1f}%)" for count, pct in zip(cat_df["Count"], cat_df["Percentage"])],
            textposition='outside',
            textfont=dict(size=11, color=COLORS["dark"])
        ))
        fig_quality.update_layout(
            title="Quality Breakdown by Category",
            xaxis_title="Number of Issues",
            yaxis_title="",
            xaxis=dict(range=[0, max_scale], dtick=1000),
            font=dict(size=12),
            title_font_size=18,
            height=max(400, len(cat_df) * 40 + 100),
            margin=dict(l=200, r=100),
            showlegend=False
        )
        fig_quality.add_vline(x=5000, line_dash="dash", line_color=COLORS["danger"],
                               annotation_text="Reference: 5000", annotation_position="top")
        st.plotly_chart(fig_quality, use_container_width=True, key="data-quality-category-breakdown")

        st.download_button(
            "Download quality breakdown (XLSX)",
            data=df_to_xlsx_bytes(cat_df.sort_values("Count", ascending=False), "Quality_Breakdown"),
            file_name="quality_breakdown.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.success("No data quality issues found based on configured rules.")

    # ── Flagged Height / Weight / BMI ─────────────────────────────────
    with st.expander("⚠️ Flag Entries", expanded=False):
        flagged_height = working[~valid_masks.get("height", pd.Series(True, index=working.index))].copy()
        if not flagged_height.empty:
            st.markdown("#### ⚠️ Flagged Height Entries")
            show_cols = [c for c in ["Sl no", "studentName", "height"] if c in flagged_height.columns]
            st.dataframe(flagged_height[show_cols].head(10), use_container_width=True)
            st.caption(f"Showing 10 of {len(flagged_height)} flagged height entries. Download full list below.")
            st.download_button(
                "Download flagged height entries (XLSX)",
                data=df_to_xlsx_bytes(flagged_height[show_cols], "Flagged_Height"),
                file_name="flagged_height_entries.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_flagged_height",
            )
        else:
            st.success("No flagged height entries.")

        flagged_weight = working[~valid_masks.get("weight", pd.Series(True, index=working.index))].copy()
        if not flagged_weight.empty:
            st.markdown("#### ⚠️ Flagged Weight Entries")
            show_cols = [c for c in ["Sl no", "studentName", "weight"] if c in flagged_weight.columns]
            st.dataframe(flagged_weight[show_cols].head(10), use_container_width=True)
            st.caption(f"Showing 10 of {len(flagged_weight)} flagged weight entries. Download full list below.")
            st.download_button(
                "Download flagged weight entries (XLSX)",
                data=df_to_xlsx_bytes(flagged_weight[show_cols], "Flagged_Weight"),
                file_name="flagged_weight_entries.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_flagged_weight",
            )
        else:
            st.success("No flagged weight entries.")

        flagged_bmi = working[working["bmi_status"].isin(["Too Low", "Too High", "Missing"])].copy()
        if not flagged_bmi.empty:
            st.markdown("#### ⚠️ Flagged BMI Entries")
            flagged_bmi["BMI_Reason"] = flagged_bmi["bmi_status"]
            show_cols = [c for c in ["Sl no", "studentName", "height", "weight", "bmi", "BMI_Reason"] if c in flagged_bmi.columns]
            st.dataframe(flagged_bmi[show_cols].head(10), use_container_width=True)
            st.caption(f"Showing 10 of {len(flagged_bmi)} flagged BMI entries. Download full list below.")
            st.download_button(
                "Download flagged BMI entries (XLSX)",
                data=df_to_xlsx_bytes(flagged_bmi[show_cols], "Flagged_BMI"),
                file_name="flagged_bmi_entries.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_flagged_bmi",
            )
        else:
            st.success("No flagged BMI entries.")

OVERALL_SCORE_TOOLTIP = (
    "Overall Score is the mean of percentile ranks across all battery tests plus height/weight proximity.\n\n"
    "**Formula:** overall_score = mean(R₁, R₂, …, Rₙ, H_prox, W_prox)\n\n"
    "Where:\n"
    "• Rᵢ = percentile rank of test i (higher-is-better tests ranked ascending; "
    "lower-is-better tests like sprint/run ranked descending)\n"
    "• H_prox = 1 − |height − median_height| / max_deviation  (closeness to median height)\n"
    "• W_prox = 1 − |weight − median_weight| / max_deviation  (closeness to median weight)\n\n"
    "Score ranges 0–1; higher = better overall athletic profile."
)

with main_tabs[4]:
    st.subheader("Athlete Profiling")
    top10 = processed["top10"].copy()

    if top10.empty:
        st.warning("No athletes available for profiling.")
    else:
        display_cols = [c for c in ["Sl no", "studentName", "overall_score"] if c in top10.columns]
        st.write("Top 10 athletes selected using battery tests + height + weight profile.")
        with st.expander("ℹ️ How is Overall Score calculated?", expanded=False):
            st.markdown(OVERALL_SCORE_TOOLTIP)
        top10_display = top10[display_cols].copy()
        top10_display.index = range(1, len(top10_display) + 1)
        top10_display.index.name = "Rank"
        st.dataframe(top10_display, use_container_width=True)

        options = top10.index.tolist()
        selected_idx = st.selectbox(
            "Select an athlete from top 10",
            options,
            format_func=lambda i: f"{top10.loc[i].get('studentName', 'Unknown')} (Sl no: {top10.loc[i].get('Sl no', 'NA')})",
        )

        athlete_row = top10.loc[selected_idx]
        athlete_view_cols = [
            "Sl no", "studentName", "height", "weight", "bmi",
            "thirtyMFlingStarts", "shuttleRun10MX6", "standingBroadJump",
            "verticalJump", "footballBallThrow5No", "eightHundredMetersRun", "overall_score"
        ]
        st.write("### Selected Athlete Metrics")
        st.dataframe(pd.DataFrame([athlete_row[[c for c in athlete_view_cols if c in athlete_row.index]]]), use_container_width=True)

        st.write("### AI Recommendation")
        st.info("🏅 Recommending sports from the Khelo India Games programme based on the athlete's physical test profile.")

        if st.button("Get top-3 sports recommendation"):
            if not AI_API_KEY:
                st.error("Please set `NVIDIA_API_KEY` in your environment before running the app.")
            else:
                with st.spinner("Generating AI recommendation..."):
                    try:
                        result = call_ai_recommendation(athlete_row, api_key=AI_API_KEY, model_name=AI_MODEL)
                        st.markdown(result)
                    except Exception as exc:
                        st.error(f"AI call failed: {exc}")

# ════════════════════════════════════════════════════════════════════════
# 🔍 INSIGHTS TAB  (Gender · Age · Demographic)
# ════════════════════════════════════════════════════════════════════════
if enable_insights:
    with main_tabs[5]:
        st.subheader("🔍 Insights — Gender · Age · Demographic")
        st.caption("This section requires **gender**, **age**, and **district** columns in the uploaded data. "
                   "Toggle the tab on/off from the sidebar.")

        insight_tabs = st.tabs(["👫 Gender", "📊 Age", "🗺️ Demographic"])

        # Helper: list of test metrics present in data
        available_tests = {k: v for k, v in all_tests_cfg.items() if k in working.columns}

        # ────────────────────────── GENDER ──────────────────────────
        with insight_tabs[0]:
            st.markdown("### Gender Distribution")
            gender_counts = working["gender"].value_counts().reset_index()
            gender_counts.columns = ["Gender", "Count"]

            fig_gpie = px.pie(gender_counts, names="Gender", values="Count",
                              title="Participation by Gender", hole=0.4,
                              color="Gender",
                              color_discrete_map={"Male": "#1E3A5F", "Female": "#E91E63"})
            fig_gpie.update_traces(textposition="inside", textinfo="percent+label")
            fig_gpie.update_layout(font=dict(size=14), title_font_size=18)
            st.plotly_chart(fig_gpie, use_container_width=True, key="insights-gender-participation-pie")

            # Gender performance comparison – grouped bars per test
            st.markdown("### Performance Comparison by Gender")
            gender_perf_rows = []
            for metric, cfg in available_tests.items():
                mask = valid_masks.get(metric, pd.Series(False, index=working.index))
                vdf = working[mask]
                for g in ["Male", "Female"]:
                    subset = vdf[vdf["gender"] == g][metric]
                    if not subset.empty:
                        gender_perf_rows.append({
                            "Test": f"{cfg['label']} ({cfg['unit']})",
                            "Gender": g,
                            "Average": round(subset.mean(), 2),
                        })

            if gender_perf_rows:
                gperf_df = pd.DataFrame(gender_perf_rows)
                fig_gperf = px.bar(gperf_df, x="Test", y="Average", color="Gender", barmode="group",
                                    color_discrete_map={"Male": "#1E3A5F", "Female": "#E91E63"},
                                    title="Average Performance by Gender (Valid Entries Only)",
                                    text="Average")
                fig_gperf.update_layout(font=dict(size=12), title_font_size=18, xaxis_tickangle=-30,
                                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_gperf, use_container_width=True, key="insights-gender-performance-bars")

            # Top 5% gender split — per test breakdown
            st.markdown("### Top 5% Athletes — Gender Split (Per Test)")
            st.caption("For each test, we compute the top 5% cutoff among valid entries, then show how many athletes qualify and their gender breakdown.")

            top5_test_rows = []
            for metric, cfg in available_tests.items():
                mask = valid_masks.get(metric, pd.Series(False, index=working.index))
                vdf = working[mask].copy()
                if vdf.empty:
                    continue
                if cfg["higher_better"]:
                    cutoff = vdf[metric].quantile(0.95)
                    top_athletes = vdf[vdf[metric] >= cutoff]
                else:
                    cutoff = vdf[metric].quantile(0.05)
                    top_athletes = vdf[vdf[metric] <= cutoff]
                total_top = len(top_athletes)
                if total_top == 0:
                    continue
                male_count = int((top_athletes["gender"] == "Male").sum())
                female_count = int((top_athletes["gender"] == "Female").sum())
                male_pct = round(male_count / total_top * 100, 1)
                female_pct = round(female_count / total_top * 100, 1)
                top5_test_rows.append({
                    "Test": cfg["label"],
                    "Cutoff": f"{cutoff:.2f} {cfg['unit']}",
                    "Top 5% Count": total_top,
                    "Male": f"{male_count} ({male_pct}%)",
                    "Female": f"{female_count} ({female_pct}%)",
                })

            if top5_test_rows:
                top5_test_df = pd.DataFrame(top5_test_rows)
                st.dataframe(top5_test_df, use_container_width=True)

                # Separate bar chart per test, 2 per row
                vis_rows = []
                for row in top5_test_rows:
                    test_name = row["Test"]
                    m_count = int(row["Male"].split("(")[0].strip())
                    f_count = int(row["Female"].split("(")[0].strip())
                    vis_rows.append({"Test": test_name, "Gender": "Male", "Count": m_count})
                    vis_rows.append({"Test": test_name, "Gender": "Female", "Count": f_count})
                vis_df = pd.DataFrame(vis_rows)
                test_names_top5 = vis_df["Test"].unique().tolist()
                for row_start in range(0, len(test_names_top5), 2):
                    row_tests = test_names_top5[row_start:row_start + 2]
                    cols = st.columns(len(row_tests))
                    for col, test_name in zip(cols, row_tests):
                        with col:
                            tdf = vis_df[vis_df["Test"] == test_name]
                            total_for_test = tdf["Count"].sum()
                            tdf = tdf.copy()
                            tdf["Label"] = tdf.apply(lambda r: f"{r['Count']} ({r['Count']/total_for_test*100:.0f}%)" if total_for_test else str(r['Count']), axis=1)
                            fig_t5 = px.bar(tdf, x="Gender", y="Count", color="Gender",
                                            color_discrete_map={"Male": "#1E3A5F", "Female": "#E91E63"},
                                            title=test_name, text="Label")
                            fig_t5.update_layout(font=dict(size=11), title_font_size=14, showlegend=False,
                                                  margin=dict(t=50, b=40))
                            st.plotly_chart(
                                fig_t5,
                                use_container_width=True,
                                key=f"insights-gender-top5-{test_name}",
                            )

        # ────────────────────────── AGE ─────────────────────────────
        with insight_tabs[1]:
            st.markdown("### Age Distribution")

            age_counts = working["age"].value_counts().sort_index().reset_index()
            age_counts.columns = ["Age", "Count"]
            _age_total = age_counts["Count"].sum()
            age_counts["Label"] = age_counts["Count"].apply(lambda c: f"{c} ({c/_age_total*100:.1f}%)")
            fig_age_bar = px.bar(age_counts, x="Age", y="Count", title="Participant Count by Age",
                                  color_discrete_sequence=[COLORS["primary"]], text="Label")
            fig_age_bar.update_layout(font=dict(size=14), title_font_size=18)
            st.plotly_chart(fig_age_bar, use_container_width=True, key="insights-age-distribution")

            # Define age groups
            def age_group(a):
                if a <= 12:
                    return "10-12 (Junior)"
                elif a <= 15:
                    return "13-15 (Sub-Junior)"
                else:
                    return "16-18 (Youth)"

            working["age_group"] = working["age"].apply(age_group)

            st.markdown("### Performance by Age Group")
            age_perf_rows = []
            for metric, cfg in available_tests.items():
                mask = valid_masks.get(metric, pd.Series(False, index=working.index))
                vdf = working[mask]
                for ag in ["10-12 (Junior)", "13-15 (Sub-Junior)", "16-18 (Youth)"]:
                    subset = vdf[vdf["age_group"] == ag][metric]
                    if not subset.empty:
                        age_perf_rows.append({
                            "Test": f"{cfg['label']} ({cfg['unit']})",
                            "Age Group": ag,
                            "Average": round(subset.mean(), 2),
                        })

            if age_perf_rows:
                aperf_df = pd.DataFrame(age_perf_rows)
                # Create separate bar chart per test, 2 per row
                test_names = aperf_df["Test"].unique().tolist()
                for row_start in range(0, len(test_names), 2):
                    row_tests = test_names[row_start:row_start + 2]
                    cols = st.columns(len(row_tests))
                    for col, test_name in zip(cols, row_tests):
                        with col:
                            tdf = aperf_df[aperf_df["Test"] == test_name]
                            fig_at = px.bar(tdf, x="Age Group", y="Average", color="Age Group", barmode="group",
                                            color_discrete_map={
                                                "10-12 (Junior)": "#FFC107",
                                                "13-15 (Sub-Junior)": "#17A2B8",
                                                "16-18 (Youth)": "#1E3A5F",
                                            },
                                            title=test_name,
                                            text="Average")
                            fig_at.update_layout(font=dict(size=11), title_font_size=14, showlegend=False,
                                                  xaxis_tickangle=-20, margin=dict(t=50, b=40))
                            st.plotly_chart(
                                fig_at,
                                use_container_width=True,
                                key=f"insights-age-performance-{test_name}",
                            )

        # ────────────────────────── DEMOGRAPHIC ─────────────────────
        with insight_tabs[2]:
            demo_tabs = st.tabs(["🗺️ District Overview", "📊 Data Collection Efficiency"])

            # ── District centroid coordinates for map visualisation ────
            # Name mapping: our district names → GADM NAME_2 property values
            DISTRICT_NAME_TO_GADM = {
                "Patna": "Patna", "Gaya": "Gaya", "Muzaffarpur": "Muzaffarpur",
                "Bhagalpur": "Bhagalpur", "Purnia": "Purnia", "Darbhanga": "Darbhanga",
                "Begusarai": "Begusarai", "Munger": "Munger", "Vaishali": "Vaishali",
                "Samastipur": "Samastipur", "Saran": "Saran",
                "East Champaran": "PurbaChamparan", "West Champaran": "PashchimChamparan",
                "Nalanda": "Nalanda", "Aurangabad": "Aurangabad", "Rohtas": "Rohtas",
                "Katihar": "Katihar", "Saharsa": "Saharsa", "Sitamarhi": "Sitamarhi",
                "Madhubani": "Madhubani", "Araria": "Araria", "Arwal": "Arwal",
                "Banka": "Banka", "Bhojpur": "Bhojpur", "Buxar": "Buxar",
                "Gopalganj": "Gopalganj", "Jamui": "Jamui", "Jehanabad": "Jehanabad",
                "Kaimur": "Kaimur", "Khagaria": "Khagaria", "Kishanganj": "Kishanganj",
                "Lakhisarai": "Lakhisarai", "Madhepura": "Madhepura", "Nawada": "Nawada",
                "Sheikhpura": "Sheikhpura", "Sheohar": "Sheohar", "Siwan": "Siwan",
                "Supaul": "Supaul",
            }
            GADM_TO_DISTRICT_NAME = {v: k for k, v in DISTRICT_NAME_TO_GADM.items()}

            @st.cache_data
            def load_bihar_geojson():
                geojson_path = Path(__file__).parent / "bihar_districts.geojson"
                with open(geojson_path, "r") as f:
                    return json.load(f)

            bihar_geojson = load_bihar_geojson()

            with demo_tabs[0]:
                st.markdown("### District-wise Participation")

                dist_counts = working["district"].value_counts().reset_index()
                dist_counts.columns = ["District", "Count"]

                # ── Bihar choropleth map — athlete count per district ──────
                dist_gender = working.groupby(["district", "gender"]).size().unstack(fill_value=0).reset_index()
                dist_gender.columns.name = None
                if "Male" not in dist_gender.columns:
                    dist_gender["Male"] = 0
                if "Female" not in dist_gender.columns:
                    dist_gender["Female"] = 0
                dist_gender["Total"] = dist_gender["Male"] + dist_gender["Female"]

                # Add overall score per district
                dist_perf = working.groupby("district")["overall_score"].mean()
                dist_gender["Avg Score"] = dist_gender["district"].map(dist_perf).round(4)

                # Map our district names to GADM names for choropleth matching
                dist_gender["gadm_name"] = dist_gender["district"].map(DISTRICT_NAME_TO_GADM)

                def _pct(part: float, total: float) -> float:
                    return (part / total * 100.0) if total else 0.0

                dist_gender["hover_text"] = dist_gender.apply(
                    lambda r: (
                        f"<b>{r['district']}</b><br>"
                        f"Total Athletes: {r['Total']}<br>"
                        f"Male: {r['Male']} ({_pct(r['Male'], r['Total']):.1f}%)<br>"
                        f"Female: {r['Female']} ({_pct(r['Female'], r['Total']):.1f}%)<br>"
                        f"Avg Overall Score: {r['Avg Score']:.4f}"
                    ), axis=1
                )

                fig_map = px.choropleth(
                    dist_gender,
                    geojson=bihar_geojson,
                    locations="gadm_name",
                    featureidkey="properties.NAME_2",
                    color="Total",
                    color_continuous_scale="Blues",
                    hover_name="district",
                    hover_data={
                        "gadm_name": False,
                        "Total": True,
                        "Male": True,
                        "Female": True,
                        "Avg Score": ":.4f",
                    },
                    labels={"Total": "Athletes", "Avg Score": "Avg Overall Score"},
                )
                fig_map.update_geos(fitbounds="locations", visible=False)
                fig_map.update_layout(
                    title="Bihar District Map — Athlete Participation",
                    font=dict(size=12), title_font_size=18,
                    height=650,
                    margin=dict(l=0, r=0, t=50, b=0),
                    geo=dict(bgcolor="#E8F4FD"),
                    coloraxis_colorbar=dict(title="Athletes"),
                )
                st.plotly_chart(fig_map, use_container_width=True, key="insights-demo-district-map")
                st.caption("Districts are colour-filled by athlete count (darker = more athletes). "
                           "Hover over a district for total participants, gender split, and performance indicator.")

                # Horizontal bar for participation
                _dist_sorted = dist_counts.sort_values("Count", ascending=True).copy()
                _dist_total = _dist_sorted["Count"].sum()
                _dist_sorted["Label"] = _dist_sorted["Count"].apply(
                    lambda c: f"{c} ({_pct(c, _dist_total):.1f}%)"
                )
                fig_distbar = px.bar(_dist_sorted,
                                      x="Count", y="District", orientation="h",
                                      title="Athlete Participation by District",
                                      color_discrete_sequence=[COLORS["primary"]],
                                      text="Label")
                fig_distbar.update_layout(font=dict(size=12), title_font_size=18,
                                           height=max(500, len(dist_counts) * 30 + 100),
                                           margin=dict(l=180))
                st.plotly_chart(
                    fig_distbar,
                    use_container_width=True,
                    key="insights-demo-district-participation-bar",
                )

                # ── District Performance Ranking ──────────────────────
                st.markdown("### District Performance Ranking (Overall Score)")
                with st.expander("ℹ️ How is the District Performance Ranking calculated?", expanded=False):
                    st.markdown(
                        "**Methodology:**\n\n"
                        "1. For each athlete, an **Overall Score** (0–1) is computed as the mean of "
                        "percentile ranks across all battery tests, plus height and weight proximity to the median.\n"
                        "2. Each district's **Average Overall Score** is the arithmetic mean of the Overall Scores "
                        "of all athletes belonging to that district.\n"
                        "3. Districts are then **ranked from highest to lowest** average score.\n\n"
                        "A higher score indicates that the district's athletes, on average, perform better "
                        "across the full battery of physical tests relative to the rest of the dataset."
                    )

                dist_score = working.groupby("district")["overall_score"].agg(["mean", "count"]).reset_index()
                dist_score.columns = ["District", "Avg Overall Score", "Athletes"]
                dist_score = dist_score.sort_values("Avg Overall Score", ascending=False)
                dist_score["Rank"] = range(1, len(dist_score) + 1)
                dist_score["Avg Overall Score"] = dist_score["Avg Overall Score"].round(4)
                st.dataframe(dist_score[["Rank", "District", "Avg Overall Score", "Athletes"]], use_container_width=True)

                # Best district per test
                st.markdown("### Best District per Test")
                best_dist_rows = []
                for metric, cfg in available_tests.items():
                    mask = valid_masks.get(metric, pd.Series(False, index=working.index))
                    vdf = working[mask]
                    if vdf.empty:
                        continue
                    dist_avg = vdf.groupby("district")[metric].mean()
                    if cfg["higher_better"]:
                        best = dist_avg.idxmax()
                        val = dist_avg.max()
                    else:
                        best = dist_avg.idxmin()
                        val = dist_avg.min()
                    best_dist_rows.append({
                        "Test": cfg["label"],
                        "Best District": best,
                        f"Avg Value ({cfg['unit']})": round(val, 2),
                    })
                if best_dist_rows:
                    st.dataframe(pd.DataFrame(best_dist_rows), use_container_width=True)

                # District contextual insights
                st.markdown("### 🏛️ Why Some Districts Perform Better")
                st.info("Contextual insights based on district GDP per capita, sports infrastructure, "
                        "notable athletes, and socio-economic factors.")

                top5_districts = dist_score.head(5)["District"].tolist()
                bottom5_districts = dist_score.tail(5)["District"].tolist()

                st.markdown("#### 🏆 Top 5 Performing Districts")
                for rank_i, dist_name in enumerate(top5_districts, 1):
                    info = BIHAR_DISTRICT_INSIGHTS.get(dist_name, {})
                    with st.expander(f"#{rank_i} — {dist_name}", expanded=(rank_i == 1)):
                        c1, c2 = st.columns(2)
                        c1.metric("GDP per Capita", info.get("gdp_per_capita", "N/A"))
                        c2.metric("Sports Infrastructure", info.get("sports_infra", "N/A").split("–")[0].strip())
                        st.markdown(f"**🏅 Notable Athletes / Traditions:** {info.get('notable_athletes', 'N/A')}")
                        st.markdown(f"**💡 Insight:** {info.get('insight', 'No data available.')}")

                st.markdown("#### ⚠️ Bottom 5 Performing Districts (Opportunity Zones)")
                for rank_i, dist_name in enumerate(bottom5_districts, len(dist_score) - 4):
                    info = BIHAR_DISTRICT_INSIGHTS.get(dist_name, {})
                    with st.expander(f"#{rank_i} — {dist_name}", expanded=False):
                        c1, c2 = st.columns(2)
                        c1.metric("GDP per Capita", info.get("gdp_per_capita", "N/A"))
                        c2.metric("Sports Infrastructure", info.get("sports_infra", "N/A").split("–")[0].strip())
                        st.markdown(f"**🏅 Notable Athletes / Traditions:** {info.get('notable_athletes', 'N/A')}")
                        st.markdown(f"**💡 Insight:** {info.get('insight', 'No data available.')}")
                        st.markdown("**🎯 Recommendation:** Targeted investment in coaching and infrastructure "
                                    "could unlock significant talent from this region.")

                # District × Gender — Bihar choropleth maps
                st.markdown("### District × Gender — Average Overall Score")
                dg_data = working.groupby(["district", "gender"])["overall_score"].mean().reset_index()
                dg_data["gadm_name"] = dg_data["district"].map(DISTRICT_NAME_TO_GADM)

                gender_col1, gender_col2 = st.columns(2)
                for gender, col, color_scale, accent in [
                    ("Male", gender_col1, "Blues", "#1E3A5F"),
                    ("Female", gender_col2, "RdPu", "#E91E63"),
                ]:
                    gdf = dg_data[dg_data["gender"] == gender].copy()
                    if gdf.empty:
                        continue
                    with col:
                        fig_dg = px.choropleth(
                            gdf,
                            geojson=bihar_geojson,
                            locations="gadm_name",
                            featureidkey="properties.NAME_2",
                            color="overall_score",
                            color_continuous_scale=color_scale,
                            hover_name="district",
                            hover_data={
                                "gadm_name": False,
                                "overall_score": ":.4f",
                            },
                            labels={"overall_score": "Avg Score"},
                        )
                        fig_dg.update_geos(fitbounds="locations", visible=False)
                        fig_dg.update_layout(
                            title=f"{gender} — Avg Overall Score",
                            font=dict(size=11), title_font_size=15,
                            height=500, margin=dict(l=0, r=0, t=50, b=0),
                            geo=dict(bgcolor="#F7F9FC"),
                            coloraxis_colorbar=dict(title="Avg Score"),
                        )
                        st.plotly_chart(
                            fig_dg,
                            use_container_width=True,
                            key=f"insights-demo-dg-{gender.lower()}-map",
                        )

                st.caption("Side-by-side choropleth maps showing average overall score for Male (blue) and Female (pink) "
                           "athletes per district. Darker colour = higher average score.")

                st.download_button(
                    "Download district performance summary (XLSX)",
                    data=df_to_xlsx_bytes(dist_score, "District_Performance"),
                    file_name="district_performance_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_district_perf",
                )

            # ── DATA COLLECTION EFFICIENCY sub-tab ────────────────────
            with demo_tabs[1]:
                st.markdown("### 📋 Data Collection Efficiency by District")
                st.caption("Analyse data quality across districts: identify which districts have the most "
                           "missing values, data entry errors, and overall best/worst data quality.")

                issues_df = processed["issues"]
                if not issues_df.empty and "district" in working.columns:
                    # Map each issue row back to its district
                    issues_with_district = issues_df.copy()
                    issues_with_district["District"] = issues_with_district["RowIndex"].map(
                        lambda idx: working.iloc[idx].get("district", "Unknown") if idx < len(working) else "Unknown"
                    )
                    issues_with_district["ErrorType"] = issues_with_district["Reason"].apply(
                        lambda r: "Missing Values" if str(r).strip() == "Missing" else "Data Entry Errors"
                    )

                    # Aggregate errors per district
                    err_by_district = issues_with_district.groupby(["District", "ErrorType"]).size().unstack(fill_value=0).reset_index()
                    err_by_district.columns.name = None
                    for col_name in ["Missing Values", "Data Entry Errors"]:
                        if col_name not in err_by_district.columns:
                            err_by_district[col_name] = 0
                    err_by_district["Total Errors"] = err_by_district["Missing Values"] + err_by_district["Data Entry Errors"]

                    # Athletes per district for error rate calc
                    athletes_per_dist = working["district"].value_counts().to_dict()
                    err_by_district["Athletes"] = err_by_district["District"].map(athletes_per_dist).fillna(0)
                    err_by_district["Error Rate"] = err_by_district.apply(
                        lambda r: round(r["Total Errors"] / r["Athletes"], 2) if r["Athletes"] else 0.0,
                        axis=1,
                    )

                    # Map: choropleth colored by error rate
                    err_by_district["gadm_name"] = err_by_district["District"].map(DISTRICT_NAME_TO_GADM)

                    fig_err_map = px.choropleth(
                        err_by_district,
                        geojson=bihar_geojson,
                        locations="gadm_name",
                        featureidkey="properties.NAME_2",
                        color="Error Rate",
                        color_continuous_scale="RdYlGn_r",
                        hover_name="District",
                        hover_data={
                            "gadm_name": False,
                            "Total Errors": True,
                            "Missing Values": True,
                            "Data Entry Errors": True,
                            "Athletes": True,
                            "Error Rate": ":.2f",
                        },
                        labels={"Error Rate": "Errors/Athlete"},
                    )
                    fig_err_map.update_geos(fitbounds="locations", visible=False)
                    fig_err_map.update_layout(
                        title="Bihar District Map — Data Quality (Error Rate per District)",
                        font=dict(size=12), title_font_size=18,
                        height=650, margin=dict(l=0, r=0, t=50, b=0),
                        geo=dict(bgcolor="#FFF5F5"),
                        coloraxis_colorbar=dict(title="Errors/Athlete"),
                    )
                    st.plotly_chart(
                        fig_err_map,
                        use_container_width=True,
                        key="insights-demo-efficiency-error-map",
                    )
                    st.caption("Districts are colour-filled by error rate (red = worst/most errors, green = best/fewest errors). "
                               "Hover for missing value vs data entry error breakdown.")

                    # Stacked bar: missing vs data entry per district
                    err_sorted = err_by_district.sort_values("Total Errors", ascending=True).copy()
                    _err_grand_total = err_sorted["Total Errors"].sum() if err_sorted["Total Errors"].sum() > 0 else 1
                    _miss_labels = [f"{v} ({v/_err_grand_total*100:.1f}%)" for v in err_sorted["Missing Values"]]
                    _entry_labels = [f"{v} ({v/_err_grand_total*100:.1f}%)" for v in err_sorted["Data Entry Errors"]]
                    fig_err_bar = go.Figure()
                    fig_err_bar.add_trace(go.Bar(
                        y=err_sorted["District"], x=err_sorted["Missing Values"],
                        name="Missing Values", orientation="h",
                        marker_color="#FFC107", text=_miss_labels, textposition="auto",
                    ))
                    fig_err_bar.add_trace(go.Bar(
                        y=err_sorted["District"], x=err_sorted["Data Entry Errors"],
                        name="Data Entry Errors", orientation="h",
                        marker_color="#DC3545", text=_entry_labels, textposition="auto",
                    ))
                    fig_err_bar.update_layout(
                        barmode="stack", title="Missing Values vs Data Entry Errors by District",
                        xaxis_title="Error Count", yaxis_title="",
                        font=dict(size=12), title_font_size=18,
                        height=max(500, len(err_sorted) * 30 + 100),
                        margin=dict(l=180),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    )
                    st.plotly_chart(
                        fig_err_bar,
                        use_container_width=True,
                        key="insights-demo-efficiency-error-bar",
                    )

                    # Best data quality districts
                    best_quality = err_by_district.sort_values("Error Rate", ascending=True).head(5)
                    st.markdown("#### ✅ Best Data Quality Districts (lowest error rate)")
                    st.dataframe(
                        best_quality[["District", "Athletes", "Total Errors", "Missing Values",
                                      "Data Entry Errors", "Error Rate"]].reset_index(drop=True),
                        use_container_width=True,
                    )

                    # Worst data quality districts
                    worst_quality = err_by_district.sort_values("Error Rate", ascending=False).head(5)
                    st.markdown("#### ⚠️ Worst Data Quality Districts (highest error rate)")
                    st.dataframe(
                        worst_quality[["District", "Athletes", "Total Errors", "Missing Values",
                                       "Data Entry Errors", "Error Rate"]].reset_index(drop=True),
                        use_container_width=True,
                    )

                    st.download_button(
                        "Download data quality by district (XLSX)",
                        data=df_to_xlsx_bytes(err_by_district[["District", "Athletes", "Total Errors",
                                              "Missing Values", "Data Entry Errors", "Error Rate"]],
                                              "Data_Quality_Districts"),
                        file_name="data_quality_by_district.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_data_quality_district",
                    )
                else:
                    st.info("No data quality issues found, or district column is missing.")
