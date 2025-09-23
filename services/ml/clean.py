import pandas as pd
import numpy as np
from pathlib import Path





OUT_DIR   = Path("data/cleaned_historical")
YEAR_LIST = ["2019", "2020", "2021", "2022", "2023", "2024", "2025"]


# ===== Normalization config =====
# Choose one of: None, "season", "expanding"
NORMALIZE_MODE = "season"
ZSCORE_PREFIX = "z_"       # for NORMALIZE_MODE == "season"
ZEXP_PREFIX   = "zexp_"    # for NORMALIZE_MODE == "expanding"

def _norm_feature_candidates(df: pd.DataFrame) -> list[str]:
    """Return numeric rolling feature columns to normalize (e.g., *_roll)."""
    num = df.select_dtypes(include=[np.number]).columns.tolist()
    cols = [c for c in num if c.endswith("_roll")]
    # Exclude binary/context flags even if named *_roll by mistake
    blacklist = {"prior_games"}
    return [c for c in cols if c not in blacklist]

def add_season_zscores(df: pd.DataFrame, cols: list[str], season_col: str = "season", prefix: str = ZSCORE_PREFIX) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            continue
        g = df.groupby(season_col)[c]
        mu = g.transform("mean")
        sd = g.transform("std").replace(0, np.nan)
        z = (df[c] - mu) / sd
        df[f"{prefix}{c}"] = z.clip(-4, 4)
    return df

def add_expanding_season_zscores(df: pd.DataFrame, cols: list[str], date_col: str = "Date", season_col: str = "season", prefix: str = ZEXP_PREFIX) -> pd.DataFrame:
    df = df.sort_values([season_col, date_col]).copy()
    for c in cols:
        if c not in df.columns:
            continue
        # cumulative mean/std up to previous row within the season
        cs = df.groupby(season_col)[c].cumsum().shift(1)
        csq = df.groupby(season_col)[c].apply(lambda s: (s**2).cumsum()).shift(1)
        n = df.groupby(season_col).cumcount()
        mu = cs / n.replace(0, np.nan)
        var = (csq / n.replace(0, np.nan)) - (mu ** 2)
        sd = np.sqrt(var.clip(lower=0))
        z = (df[c] - mu) / sd.replace(0, np.nan)
        df[f"{prefix}{c}"] = z.clip(-4, 4)
    return df





# Static alias dictionary for team name normalization
TEAM_ALIASES = {
    # Common abbreviations / sportsbook short names → canonical stats names
    "ablchristian": "abilenechristian",
    "alabam": "alabamaam",
    "alabamast": "alabamastate",
    "albany": "albanyny",
    "alcornst": "alcornstate",
    "appstate": "appalachianstate",
    "arizonast": "arizonastate",
    "arkansasst": "arkansasstate",
    "arkpinebl": "arkansaspinebluff",
    "arlitrock": "arkansaslittlerock",
    "ballst": "ballstate",
    "bethcook": "bethunecookman",
    "boisest": "boisestate",
    "bostoncol": "bostoncollege",
    "bostonu": "bostonuniversity",
    "bowlinggrn": "bowlinggreenstate",
    "byu": "brighamyoung",
    "calbaptist": "californiabaptist",
    "calstnrdge": "calstatenorthridge",
    "centralark": "centralarkansas",
    "centralconn": "centralconnecticutstate",
    "centralmich": "centralmichigan",
    "charlsouth": "charlestonsouthern",
    "chicagost": "chicagostate",
    "clevelandst": "clevelandstate",
    "coastalcar": "coastalcarolina",
    "colcharlestn": "collegeofcharleston",
    "charleston": "collegeofcharleston",
    "coloradost": "coloradostate",
    "coppinst": "coppinstate",
    "purduefw": "ipfw",
    "iuindy": "iupui",
    "csbakersfld": "calstatebakersfield",
    "csfullerton": "calstatefullerton",
    "delawarest": "delawarestate",
    "detroit": "detroitmercy",
    "ecarolina": "eastcarolina",
    "ekentucky": "easternkentucky",
    "emichigan": "easternmichigan",
    "etennst": "easttennesseestate",
    "ewashingtn": "easternwashington",
    "fdickinson": "fairleighdickinson",
    "flaatlantic": "floridaatlantic",
    "flagulfcst": "floridagulfcoast",
    "floridaintl": "floridainternational",
    "floridast": "floridastate",
    "fresnost": "fresnostate",
    "gardwebb": "gardnerwebb",
    "gasouthern": "georgiasouthern",
    "gatech": "georgiatech",
    "geomason": "georgemason",
    "georgiast": "georgiastate",
    "georgiaso": "georgiasouthern",
    "gwashington": "georgewashington",
    "geowshgtn": "georgewashington",
    "houchristian": "houstonbaptist", 
    "hsnchristian": "houstonbaptist",
    "idahost": "idahostate",
    "illinoisst": "illinoisstate",
    "indianast": "indianastate",
    "iowast": "iowastate",
    "jacksonst": "jacksonstate",
    "jacksonvillest": "jacksonvillestate",
    "kansast": "kansasstate",
    "kentst": "kentstate",
    "louisianast": "louisianastate",
    "longbeachst": "longbeachstate",
    "missst": "mississippistate",
    "missvalst": "mississippivalleystate",
    "montst": "montanastate",
    "moreheadst": "moreheadstate",
    "ncstate": "northcarolinastate",
    "ndst": "northdakotastate",
    "nillinois": "northernillinois",
    "northernariz": "northernarizona",
    "northtexas": "northtexas",
    "oklahomast": "oklahomastate",
    "oregonst": "oregonstate",
    "pennst": "pennstate",
    "sacstate": "sacramentostate",
    "samhoustonst": "samhoustonstate",
    "sandiegost": "sandiegostate",
    "santarosa": "santaclara", 
    "semo": "southeastmissouristate",
    "sillinois": "southernillinois",
    "siue": "southernillinoisedwardsville",
    "southal": "southalabama",
    "southcarst": "southcarolinastate",
    "stjohns": "stjohnsny",
    "stjosephs": "saintjosephs",
    "stlouis": "saintlouis",
    "syr": "syracuse",
    "tennessest": "tennesseestate",
    "tenntec": "tennesseetech",
    "tnmartin": "tennesseemartin",
    "towsonst": "towson",
    "txamcc": "texasamcorpuschristi",
    "txsout": "texassouthern",
    "utahst": "utahstate",
    "valdosta": "valparaiso", 
    "washst": "washingtonstate",
    "westvirg": "westvirginia",
    "wrightst": "wrightstate",
    "youngstownst": "youngstownstate",
    "ucriverside": "californiariverside",
    "tnstate": "tennesseestate",
    "kennesawst": "kennesawstate",
    "sdakotast": "southdakotastate",
    "wmmary": "williammary",
    "ewashingtn": "easternwashington",
    "scupstate": "southcarolinaupstate",
    "eillinois": "easternillinois",
    "upenn": "pennsylvania",
    "scarolinast": "southcarolinastate",
    "geomason": "georgemason",
    "gramblingst": "grambling",
    "kansascity": "missourikansascity",
    "ucdavis": "californiadavis",
    "latech": "louisianatech",
    "lsu": "louisianastate",
    "marylandbc": "marylandbaltimorecounty",
    "marylandes": "marylandeasternshore",
    "masslowell": "massachusettslowell",
    "liu": "longislanduniversity",
    "ncasheville": "northcarolinaasheville",
    "ncgrnsboro": "northcarolinagreensboro",
    "ncat": "northcarolinaat",
    "nccentral": "northcarolinacentral",
    "ncwilmgton": "northcarolinawilmington",
    "semissouri": "southeastmissouristate",
    "siuedward": "southernillinoisedwardsville",
    "stfranny": "saintfrancispa",
    "sutah": "southernutah",
    "tntech": "tennesseetech",
    "txpanam": "texaspanamerican",
    "uab": "alabamabirmingham",
    "ucf": "centralflorida",
    "ucirvine": "californiairvine",
    "ucsb": "californiasantabarbara",
    "ucsd": "californiasandiego",
    "ulmonroe": "louisianamonroe",
    "umass": "massachusetts",
    "unlv": "nevadalasvegas",
    "usc": "southerncalifornia",
    "utsa": "texassanantonio",
    "vatech": "virginiatech",
    "vcu": "virginiacommonwealth",
    "vmi": "virginiamilitaryinstitute",
    "youngsst": "youngstownstate",
    "alabamam": "alabamaam",
    "geowshgtn": "georgewashington",
    "gramblingst": "grambling",
    "grdcanyon": "grandcanyon",
    "houstonbap": "houstonbaptist",
    "ilchicago": "illinoischicago",
    "incarword": "incarnateword",
    "jamesmad": "jamesmadison",
    "jksnvillest": "jacksonvillestate",
    "kansascity": "missourikansascity",
    "kansasst": "kansasstate",
    "kennesawst": "kennesawstate",
    "lgbeachst": "longbeachstate",
    "louisiana": "louisianalafayette",
    "loyolachi": "loyolail",
    "loyolamymt": "loyolamarymount",
    "mcneesest": "mcneesestate",
    "miami": "miamifl",
    "michiganst": "michiganstate",
    "middletenn": "middletennessee",
    "missourist": "missouristate",
    "missstate": "mississippistate",
    "montanast": "montanastate",
    "morganst": "morganstate",
    "mtstmarys": "mountstmarys",
    "murrayst": "murraystate",
    "nalabama": "northalabama",
    "narizona": "northernarizona",
    "ncarolina": "westerncarolina",
    "ncolorado": "northerncolorado",
    "ndakotast": "northdakotastate",
    "nebomaha": "nebraskaomaha",
    "nflorida": "northflorida",
    "nhampshire": "newhampshire",
    "nicholls": "nichollsstate",
    "niowa": "northerniowa",
    "nkentucky": "northernkentucky",
    "nmexstate": "newmexicostate",
    "norfolkst": "norfolkstate",
    "northeastrn": "northeastern",
    "nwstate": "weberstate",
    "ohiost": "ohiostate",
    "portlandst": "portlandstate",
    "robmorris": "robertmorris",
    "sacredhrt": "sacredheart",
    "salabama": "southalabama",
    "samhousst": "samhoustonstate",
    "sanjosest": "sanjosestate",
    "scarolina": "southcarolina",
    "scarstate": "kansasstate",
    "sdakotast": "southdakotastate",
    "selouisiana": "southeasternlouisiana",
    "sflorida": "southflorida",
    "smethodist": "southernmethodist",
    "smississippi": "southernmississippi",
    "southernmiss": "southernmississippi",
    "stbonavent": "stbonaventure",
    "stefaustin": "stephenfaustin",
    "stfranpa": "saintfrancispa",
    "stmarys": "saintmarysca",
    "stpeters": "saintpeters",
    "stthomas": "stthomasmn",
    "tarletonst": "tarletonstate",
    "texasst": "texasstate",
    "txarlington": "texasarlington",
    "txchristian": "texaschristian",
    "txelpaso": "texaselpaso",
    "txsouthern": "texassouthern",
    "washstate": "washingtonstate",
    "wcarolina": "westerncarolina",
    "weberst": "weberstate",
    "wichitast": "wichitastate",
    "wigrnbay": "greenbay",
    "willinois": "westernillinois",
    "wimilwkee": "milwaukee",
    "wkentucky": "westernkentucky",
    "wmichigan": "michiganstate",
    "wvirginia": "westvirginia",
    "arpinebluff": "arkansaspinebluff",
    "bethune": "bethunecookman",
    "bowlinggreen": "bowlinggreenstate",
    "carkansas": "centralarkansas",
    "cconnecticut": "centralconnecticutstate",
    "charlestonso": "charlestonsouthern",
    "cmichigan": "centralmichigan",
    "csbakersfield": "calstatebakersfield",
    "csnorthridge": "calstatenorthridge",
    "etennesseest": "easttennesseestate",
    "etexasam": "texasamcorpuschristi",
    "txamcom": "texasamcommerce",
    "ewashington": "easternwashington",
    "fgcu": "floridagulfcoast",
    "jmadison": "jamesmadison",
    "littlerock": "arkansaslittlerock",
    "mcneesestate": "mcneesestate",
    "mcneese": "mcneesestate",
    "penn": "pennsylvania",
    "samhouston": "samhoustonstate",
    "mississippist": "mississippistate",
    "missvalleyst": "mississippivalleystate",
    "ncgreensboro": "northcarolinagreensboro",
    "ncwilmington": "northcarolinawilmington",
    "ncarolina": "northcarolina",
    "newmexicost": "newmexicostate",
    "ntexas": "northtexas",
    "omaha": "nebraskaomaha",
    "queensny": "queenscollege",
    "queens": "queensnc",
    "sacramentost": "sacramentostate",
    "saintmarys"    : "saintmarysca",
    "samhoustonst": "samhoustonstate",
    "scarstate": "southcarolinastate",
    "semissourist": "southeastmissouristate",
    "sfaustin": "stephenfaustin",
    "sindiana": "southernindiana",
    "smu": "southernmethodist",
    "stfrancispa": "saintfrancispa",
    "tcu": "texaschristian",
    "tennesseest": "tennesseestate",
    "tenntech": "tennesseetech",
    "texasamcc": "texasamcommerce",
    "texasso": "texassouthern",
    "thecitadel": "citadel",
    "uconn": "connecticut",
    "umasslowell": "massachusettslowell",
    "umbc": "marylandbaltimorecounty",
    "utahtech": "dixiestate",
    "utarlington": "texasarlington",
    "utep": "texaselpaso",
    "utmartin": "tennesseemartin",
    "utriogrande": "texaspanamerican",
    "washingtonst": "washingtonstate",
    "wgeorgia": "westgeorgia",
    "nwstate": "northwesternstate",


}

def _slug_str(x: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", x.lower())

def load_alias_map() -> dict[str, str]:
    """Return alias mappings using ONLY the static TEAM_ALIASES (no CSV loading)."""
    # ensure cache symbol exists
    global _ALIAS_MAP_CACHE
    try:
        _ = _ALIAS_MAP_CACHE
    except NameError:
        _ALIAS_MAP_CACHE = None

    if _ALIAS_MAP_CACHE is not None:
        return _ALIAS_MAP_CACHE

    def _slug(x: str) -> str:
        return "".join(ch for ch in str(x).lower() if ch.isalnum())

    alias: dict[str, str] = {}
    # Normalize TEAM_ALIASES into fully slugged map
    for bet_key, canon_key in TEAM_ALIASES.items():
        bk = _slug(bet_key)
        ck = _slug(canon_key)
        if bk and ck:
            alias[bk] = ck

    _ALIAS_MAP_CACHE = alias
    print(f"[aliases] Loaded {len(alias)} total aliases (static only)")
    return _ALIAS_MAP_CACHE

# --- Betting constants and columns ---
BET_DIR = Path("data/betting_historical")

BET_COLS_MAP = {
    "Date": "Date",
    "Team": "bet_Team",
    "Opponent": "bet_Opponent",
    "Location": "bet_Location",
    "Score": "bet_Score",
    "Spread": "bet_spread",
    "ATS Margin": "bet_ats_margin",
    "Total (O/U)": "bet_total",
    "Combined": "bet_combined",
    "O/U Margin": "bet_ou_margin",
    "Moneyline": "bet_moneyline",
    "MOV": "bet_mov",
}

DIRECTIONAL_BET_COLS = ["bet_spread", "bet_ats_margin", "bet_mov"]

GAME_LEVEL_BET_COLS = ["bet_total", "bet_combined", "bet_ou_margin"]

# Canonical betting columns we want across all seasons
CANONICAL_BET_COLS = [
    "bet_spread",
    "bet_ats_margin",
    "bet_mov",
    "bet_total",
    "bet_combined",
    "bet_ou_margin",
    "bet_moneyline",
    "bet_moneyline_for_team",
]

def ensure_bet_schema(df: pd.DataFrame, cols: list[str] = CANONICAL_BET_COLS) -> pd.DataFrame:
    """Ensure the provided betting columns exist in df. Adds missing columns as NaN.
    Returns a new DataFrame with the same index as input.
    """
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = np.nan
    return out

def normalize_key(s: pd.Series) -> pd.Series:
    alias = load_alias_map()
    sl = s.astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
    return sl.map(lambda x: alias.get(x, x))

def raw_path_for(year: str) -> str:
    return f"data/raw_historical/d1_mens_basketball_{year}_gamelogs.csv"



def parse_dates(series: pd.Series) -> pd.Series:
    """Try multiple formats and pick the one with the most valid parses; then
    drop any timezone info and normalize to midnight so joins are day-precise."""
    candidates = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%d-%b-%y",
        "%d-%b-%Y",
    ]
    best = None
    best_ok = -1
    for fmt in candidates:
        dt = pd.to_datetime(series, format=fmt, errors="coerce")
        ok = dt.notna().sum()
        if ok > best_ok:
            best_ok, best = ok, dt
    if best_ok <= 0:
        # fallback: let pandas infer (may be slower but robust)
        best = pd.to_datetime(series, errors="coerce")

    # Ensure tz-naive and strip time-of-day for consistent joins
    try:
        best = best.dt.tz_localize(None)
    except Exception:
        pass
    return best.dt.normalize()

def slug(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().str.replace(r"[^a-z0-9]", "", regex=True)

# --- Betting loader ---
def load_betting(year: str) -> pd.DataFrame:
    """Load betting lines CSV for a year and normalize columns/keys."""
    # Prefer a pre-normalized file if you've created one; fall back to original
    path_fixed = BET_DIR / f"{year}BettingLinesCBB_fixed.csv"
    path = path_fixed if path_fixed.exists() else (BET_DIR / f"{year}BettingLinesCBB.csv")
    if not path.exists():
        raise FileNotFoundError(str(path))
    b = pd.read_csv(path)

    # Drop any duplicate-named columns (some CSVs may repeat headers)
    if b.columns.duplicated().any():
        b = b.loc[:, ~b.columns.duplicated()].copy()

    # If there are multiple columns that are effectively 'Date' (case-insensitive), keep the first
    date_like = [c for c in b.columns if c.lower() == "date"]
    if len(date_like) > 1:
        keep = date_like[0]
        drop = date_like[1:]
        b = b.drop(columns=drop)
        if keep != "Date":
            b = b.rename(columns={keep: "Date"})

    # Rename to normalized bet_* columns where present
    rename = {k: v for k, v in BET_COLS_MAP.items() if k in b.columns}
    b = b.rename(columns=rename)

    # After renaming, ensure unique column names again
    if b.columns.duplicated().any():
        # Prefer the left-most occurrence when duplicates exist
        seen = set()
        new_cols = []
        for col in b.columns:
            if col not in seen:
                new_cols.append(col)
                seen.add(col)
            else:
                # drop duplicate by giving it a throwaway name then removing
                new_cols.append(f"__dup__{col}")
        b.columns = new_cols
        b = b.loc[:, [c for c in b.columns if not c.startswith("__dup__")]].copy()

    # Parse date
    b["Date"] = parse_dates(b["Date"]) if "Date" in b.columns else pd.NaT
    if "Date" in b.columns:
        try:
            b["Date"] = b["Date"].dt.tz_localize(None)
        except Exception:
            pass
        b["Date"] = b["Date"].dt.normalize()

    # Keys
    if "bet_Team" in b.columns:
        b["team_key"] = normalize_key(b["bet_Team"])
    else:
        b["team_key"] = ""
    if "bet_Opponent" in b.columns:
        b["opp_key"] = normalize_key(b["bet_Opponent"])
    else:
        b["opp_key"] = ""

    # Coerce numerics where applicable
    for c in ["bet_spread", "bet_ats_margin", "bet_total", "bet_combined", "bet_ou_margin", "bet_moneyline", "bet_mov"]:
        if c in b.columns:
            b[c] = pd.to_numeric(b[c], errors="coerce")

    # Build a deterministic, de-duplicated keep list (avoid double 'Date')
    mapped_vals = [v for v in BET_COLS_MAP.values() if v in b.columns]
    mapped_vals = [v for v in mapped_vals if v not in {"Date", "team_key", "opp_key"}]
    keep = ["Date", "team_key", "opp_key"] + mapped_vals
    keep = list(dict.fromkeys([c for c in keep if c in b.columns]))
    b = b.loc[:, keep].copy()
    return b


# --- Reduce betting lines to one row per (day, team_key, opp_key) ---
def reduce_betting(b: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one row per game (DateKey, team_key, opp_key), taking last non-null for bet_* columns.
    Drops rows with missing Date/team_key/opp_key so merges cannot explode with duplicates.
    """
    if b.empty:
        return b
    b = b.copy()

    # Parse date and build day-only key
    b["Date"] = pd.to_datetime(b["Date"], errors="coerce")
    b["_DateKey"] = b["Date"].dt.date

    # Normalize and trim keys, drop unusable rows
    for k in ("team_key", "opp_key"):
        if k not in b.columns:
            b[k] = ""
        b[k] = b[k].astype(str).str.strip()

    # Keep only rows with complete merge keys
    b = b.dropna(subset=["_DateKey"]).loc[(b["team_key"] != "") & (b["opp_key"] != "")].copy()
    if b.empty:
        return b.assign(Date=pd.to_datetime(pd.Series([], dtype="datetime64[ns]")))

    grp = ["_DateKey", "team_key", "opp_key"]

    def last_non_null(s: pd.Series):
        s = s.dropna()
        return s.iloc[-1] if not s.empty else pd.NA

    agg = {}
    for c in b.columns:
        if c in grp or c == "Date":
            continue
        if c.startswith("bet_"):
            agg[c] = last_non_null
        else:
            agg[c] = lambda s: s.dropna().iloc[0] if s.dropna().size else pd.NA

    out = b.groupby(grp, as_index=False).agg(agg)

    # Restore Date from key at midnight; ensure uniqueness and stable ordering
    out["Date"] = pd.to_datetime(out["_DateKey"], errors="coerce")
    out = out.drop(columns=["_DateKey"], errors="ignore")

    # Final guard: enforce strict uniqueness
    dup_mask = out.duplicated(subset=["Date", "team_key", "opp_key"], keep=False)
    if dup_mask.any():
        out = (
            out.sort_values(["Date", "team_key", "opp_key"])
               .drop_duplicates(subset=["Date", "team_key", "opp_key"], keep="last")
        )

    return out.reset_index(drop=True)

def prepare_rolling(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Date"] = parse_dates(df["Date"])
    try:
        df["Date"] = df["Date"].dt.tz_localize(None)
    except Exception:
        pass
    df["Date"] = df["Date"].dt.normalize()
    df = df.dropna(subset=["Date", "Team", "Opp"])

    # numeric conversion (remove % signs)
    for c in df.columns:
        if df[c].dtype == "object":
            try:
                df[c] = pd.to_numeric(df[c].str.replace("%", "", regex=False))
            except Exception:
                # if conversion fails, leave column as-is
                pass

    # normalize keys
    df["team_key"] = normalize_key(df["Team"])
    df["opp_key"] = normalize_key(df["Opp"])

    # sort games
    df["RowID"] = np.arange(len(df))
    df = df.sort_values(["team_key", "Date", "RowID"]).reset_index(drop=True)
    df["prior_games"] = df.groupby("team_key").cumcount()

    # --- Rolling win% and Strength of Schedule (SOS) ---
    # Compute per-row win flag for the team and store as a named column
    if "Tm" in df.columns and "Opp.1" in df.columns:
        df["Tm"] = pd.to_numeric(df["Tm"], errors="coerce")
        df["Opp.1"] = pd.to_numeric(df["Opp.1"], errors="coerce")
        win_flag = (df["Tm"] > df["Opp.1"]).astype(float)
    else:
        win_flag = pd.Series(np.nan, index=df.index)
    win_flag.name = "win_flag"
    df["win_flag"] = win_flag

    # Team rolling win% up to prior game (shifted by 1 to avoid leakage)
    team_winpct_roll = (
        df.groupby("team_key")["win_flag"]
          .expanding()
          .mean()
          .reset_index(level=0, drop=True)
          .shift(1)
    )
    team_winpct_roll.name = "team_winpct_roll"

    # Opponent rolling win% at the time of this matchup
    opp_wp_lookup = pd.concat([
        df[["team_key", "Date"]].rename(columns={"team_key": "opp_key"}),
        team_winpct_roll.rename("opp_winpct_roll")
    ], axis=1)

    # Merge to get opponent win% for each row (current opponent's rolling win%)
    base_keys = ["Team", "Opp", "team_key", "opp_key", "Date", "prior_games"]
    team_base = df[base_keys].copy()
    team_base = team_base.merge(opp_wp_lookup, on=["opp_key", "Date"], how="left")

    # Team SOS: rolling average of opponent win% across *past* opponents (shifted)
    team_SOS_roll = (
        team_base.groupby("team_key")["opp_winpct_roll"]
                 .apply(lambda s: s.expanding().mean())
                 .reset_index(level=0, drop=True)
                 .shift(1)
    )
    team_SOS_roll.name = "team_SOS_roll"

    # choose numeric stats for rolling
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # skip opponent copies and junk columns (RowID, prior_games, Gtm)
    stat_cols = [
        c for c in num_cols
        if not c.endswith(".1")
        and c not in ["RowID", "prior_games", "Gtm"]
    ]

    # compute rolling averages
    roll = (
        df.groupby("team_key")[stat_cols]
          .expanding()
          .mean()
          .reset_index(level=0, drop=True)
          .shift(1)
    )
    roll.columns = [f"team_{c}_roll" for c in roll.columns]
    # rename team_Tm_roll to team_points_roll
    roll = roll.rename(columns={"team_Tm_roll": "team_points_roll"})

    team_roll = pd.concat([
        df[["Team", "Opp", "team_key", "opp_key", "Date", "prior_games"]],
        team_winpct_roll,
        team_SOS_roll,
        roll
    ], axis=1)

    # opponent roll
    opp_lookup = pd.concat([df[["team_key", "Date"]].rename(columns={"team_key": "opp_key"}), roll], axis=1)
    opp_lookup = opp_lookup.rename(columns={c: c.replace("team_", "opp_") for c in roll.columns})
    # rename opp_Tm_roll to opp_points_roll
    if "opp_Tm_roll" in opp_lookup.columns:
        opp_lookup = opp_lookup.rename(columns={"opp_Tm_roll": "opp_points_roll"})

    # Also attach opponent win% and SOS to the lookup
    opp_sos_lookup = pd.concat([
        df[["team_key", "Date"]].rename(columns={"team_key": "opp_key"}),
        team_SOS_roll.rename("opp_SOS_roll")
    ], axis=1)
    opp_lookup = opp_lookup.merge(opp_wp_lookup[["opp_key","Date","opp_winpct_roll"]], on=["opp_key","Date"], how="left")
    opp_lookup = opp_lookup.merge(opp_sos_lookup[["opp_key","Date","opp_SOS_roll"]], on=["opp_key","Date"], how="left")

    out = pd.merge(team_roll, opp_lookup, on=["opp_key", "Date"], how="left")

    # --- Rolling Pace (possessions per game, Oliver formula) ---
    # pace ≈ FGA + 0.44*FTA - ORB + TOV (computed from rolling means, shifted already)
    team_req = ["team_FGA_roll", "team_FTA_roll", "team_ORB_roll", "team_TOV_roll"]
    opp_req  = ["opp_FGA_roll",  "opp_FTA_roll",  "opp_ORB_roll",  "opp_TOV_roll"]

    if all(c in out.columns for c in team_req):
        out["team_pace_roll"] = (
            out["team_FGA_roll"] + 0.44 * out["team_FTA_roll"] - out["team_ORB_roll"] + out["team_TOV_roll"]
        )
    else:
        out["team_pace_roll"] = np.nan

    if all(c in out.columns for c in opp_req):
        out["opp_pace_roll"] = (
            out["opp_FGA_roll"] + 0.44 * out["opp_FTA_roll"] - out["opp_ORB_roll"] + out["opp_TOV_roll"]
        )
    else:
        out["opp_pace_roll"] = np.nan

    if "team_pace_roll" in out.columns and "opp_pace_roll" in out.columns:
        out["delta_pace_roll"] = out["team_pace_roll"] - out["opp_pace_roll"]

    # --- Rolling Offensive/Defensive Efficiency (per 100 possessions) ---
    # Possessions (Oliver): FGA + 0.44*FTA - ORB + TOV, using *rolling means* (already shifted by 1)
    have_team_poss = all(c in out.columns for c in [
        "team_FGA_roll", "team_FTA_roll", "team_ORB_roll", "team_TOV_roll"
    ]) and ("team_points_roll" in out.columns)
    have_opp_poss = all(c in out.columns for c in [
        "opp_FGA_roll", "opp_FTA_roll", "opp_ORB_roll", "opp_TOV_roll"
    ]) and ("opp_points_roll" in out.columns)

    if have_team_poss:
        team_poss = (
            out["team_FGA_roll"] + 0.44 * out["team_FTA_roll"] - out["team_ORB_roll"] + out["team_TOV_roll"]
        )
        # Avoid divide-by-zero or negative edge cases
        team_poss = team_poss.where(team_poss > 0)
    else:
        team_poss = pd.Series(np.nan, index=out.index)

    if have_opp_poss:
        opp_poss = (
            out["opp_FGA_roll"] + 0.44 * out["opp_FTA_roll"] - out["opp_ORB_roll"] + out["opp_TOV_roll"]
        )
        opp_poss = opp_poss.where(opp_poss > 0)
    else:
        opp_poss = pd.Series(np.nan, index=out.index)

    # Offensive efficiency: points scored per 100 possessions
    # Defensive efficiency: points allowed per 100 possessions (use same possession base for that team)
    out["team_off_eff_roll"] = (out.get("team_points_roll") / team_poss) * 100
    out["team_def_eff_roll"] = (out.get("opp_points_roll")  / team_poss) * 100
    out["opp_off_eff_roll"]  = (out.get("opp_points_roll")  / opp_poss)  * 100
    out["opp_def_eff_roll"]  = (out.get("team_points_roll") / opp_poss)  * 100

    # --- Advanced Opponent Strength & SOS (rolling, no leakage) ---
    # Opponent net efficiency (per 100) and z-score
    if {"opp_off_eff_roll", "opp_def_eff_roll"}.issubset(out.columns):
        opp_net_eff = out["opp_off_eff_roll"] - out["opp_def_eff_roll"]
        mu = opp_net_eff.mean(skipna=True)
        sd = opp_net_eff.std(skipna=True)
        if pd.isna(sd) or sd == 0:
            sd = 1.0
        opp_net_eff_z = (opp_net_eff - mu) / sd
    else:
        opp_net_eff_z = pd.Series(np.nan, index=out.index)

    # Shrink opponent rolling win% toward 0.5 early in season (robust to NaNs)
    k = 6.0  # prior strength
    if "opp_winpct_roll" in out.columns and "prior_games" in out.columns:
        pg = pd.to_numeric(out["prior_games"], errors="coerce").clip(lower=0)
        ow = pd.to_numeric(out["opp_winpct_roll"], errors="coerce")
        # Treat missing opponent win% as neutral 0.5 when unobserved
        ow_safe = ow.fillna(0.5)
        opp_winpct_shrunk = (ow_safe * pg + 0.5 * k) / (pg + k)
    else:
        opp_winpct_shrunk = pd.Series(np.nan, index=out.index)

    # Opponent Strength Index (blend win% and net efficiency z-score)
    # Blend win% and net efficiency z; use 0 when net-eff z is missing early
    out["opp_strength_idx"] = 0.5 * opp_winpct_shrunk + 0.5 * opp_net_eff_z.fillna(0)

    # Rolling advanced SOS for team = expanding mean of prior opponent strengths
    g = out.groupby("team_key", sort=False)
    prior_osi = g["opp_strength_idx"].shift(1)
    out["team_SOS_adv_roll"] = prior_osi.groupby(out["team_key"]).expanding().mean().reset_index(level=0, drop=True)

    # Also attach opponent's advanced SOS via lookup to form a delta
    adv_lookup = pd.concat([
        out[["team_key", "Date"]].rename(columns={"team_key": "opp_key"}),
        out[["team_SOS_adv_roll"]].rename(columns={"team_SOS_adv_roll": "opp_SOS_adv_roll"})
    ], axis=1)
    out = out.merge(adv_lookup, on=["opp_key", "Date"], how="left")

    out["delta_SOS_roll"] = out["team_SOS_roll"] - out["opp_SOS_roll"]
    if "team_SOS_adv_roll" in out.columns and "opp_SOS_adv_roll" in out.columns:
        out["delta_SOS_adv_roll"] = out["team_SOS_adv_roll"] - out["opp_SOS_adv_roll"]

    # Drop any rows that have nulls (e.g. when teams play non-D1 opponents)
    out = out[out["prior_games"] > 0]

# 2) Now drop any other rows with nulls (e.g., non-D1 opp causing missing opp rolls)
    out = out.dropna().reset_index(drop=True)

    return out

def add_labels(cleaned: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    raw["Date"] = parse_dates(raw["Date"])
    try:
        raw["Date"] = raw["Date"].dt.tz_localize(None)
    except Exception:
        pass
    raw["Date"] = raw["Date"].dt.normalize()
    raw["team_key"] = normalize_key(raw["Team"])
    raw["opp_key"]  = normalize_key(raw["Opp"])

    # Build a map from team_key -> Conference (most frequent non-null value per team)
    if "Conference" in raw.columns:
        conf_df = raw[["Team", "Conference"]].copy()
        conf_df["team_key"] = normalize_key(conf_df["Team"])  # normalize
        conf_df = conf_df.dropna(subset=["Conference"])  # keep only known
        # most frequent conference per team_key
        conf_map = (
            conf_df.groupby("team_key")["Conference"]
                   .agg(lambda s: s.value_counts().idxmax())
        )
    else:
        conf_map = pd.Series(dtype=object)

    merged = pd.merge(
        cleaned,
        raw[["team_key", "opp_key", "Date", "Tm", "Opp.1", "Location"]],
        on=["team_key", "opp_key", "Date"],
        how="inner"
    )

    # rename raw score columns for clarity
    merged = merged.rename(columns={"Tm": "team_score", "Opp.1": "opp_score"})

    # ensure numeric
    merged["team_score"] = pd.to_numeric(merged["team_score"], errors="coerce")
    merged["opp_score"]  = pd.to_numeric(merged["opp_score"], errors="coerce")

    # labels
    merged["win"]    = (merged["team_score"] > merged["opp_score"]).astype(int)
    merged["margin"] = merged["team_score"] - merged["opp_score"]
    merged["total"]  = merged["team_score"] + merged["opp_score"]

    # home/away/neutral from Location column; then drop Location
    loc = merged["Location"].fillna("")
    merged["is_neutral"] = (loc == "N").astype(int)
    merged["is_home"]    = (~loc.isin(["@", "N"])) .astype(int)
    merged = merged.drop(columns=["Location"])  # remove Location from final outputs

    # conference-game flag: team_conf == opp_conf
    if not conf_map.empty:
        team_conf = merged["team_key"].map(conf_map)
        opp_conf  = merged["opp_key"].map(conf_map)
        merged["is_conf_game"] = (team_conf.notna() & opp_conf.notna() & (team_conf == opp_conf)).astype(int)
    else:
        merged["is_conf_game"] = 0

    # Rolling Strength of Record (SOR): prior wins weighted by prior opponent strength
    if "opp_strength_idx" in merged.columns:
        grp = merged.groupby("team_key", sort=False)
        # Use prior game only (shift), and treat missing as 0 in cumulative sums to avoid NaN propagation
        win_prev = grp["win"].shift(1).fillna(0)
        osi_prev = grp["opp_strength_idx"].shift(1).fillna(0)
        num = (win_prev * osi_prev).groupby(merged["team_key"]).cumsum()
        den = (osi_prev).groupby(merged["team_key"]).cumsum().replace(0, np.nan)
        merged["team_SOR_roll"] = num / den
    else:
        merged["team_SOR_roll"] = np.nan

    # game id: same id for both team rows
    # ensure Date is datetime
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")

    # order-independent pair key
    pair_key = np.where(
        merged["team_key"] <= merged["opp_key"],
        merged["team_key"] + "_" + merged["opp_key"],
        merged["opp_key"] + "_" + merged["team_key"],
    )
    merged["game_key"] = pair_key + "_" + merged["Date"].dt.strftime("%Y%m%d")

    # stable 1-based id (same for both team rows)
    merged["game_id"] = pd.factorize(merged["game_key"])[0] + 1

    return merged

# --- Merge helper for betting lines ---
def merge_betting(labeled: pd.DataFrame, betting: pd.DataFrame) -> pd.DataFrame:
    """Merge betting lines onto per-team rows by (Date-only, team_key, opp_key).
    If direct match fails, try swapped keys and flip directional fields to row team's POV.
    Moneyline isn't flipped (left NaN for swapped rows)."""
    df = labeled.copy()
    b = betting.copy()
    # Deduplicate columns (keep first occurrence) before any Date parsing
    if b.columns.duplicated().any():
        b = b.loc[:, ~b.columns.duplicated()].copy()
    # If multiple literal 'Date' columns slipped through, keep only the first
    if list(b.columns).count("Date") > 1:
        keep_cols = []
        seen_date = False
        for c in b.columns:
            if c == "Date":
                if not seen_date:
                    keep_cols.append(c)
                    seen_date = True
                # skip later 'Date' duplicates
            else:
                keep_cols.append(c)
        b = b.loc[:, keep_cols].copy()
    # Guard against rare case where selecting 'Date' yields a DataFrame (duplicate-named cols)
    _df_date = df["Date"] if "Date" in df.columns else pd.Series(pd.NaT, index=df.index)
    if isinstance(_df_date, pd.DataFrame):
        _df_date = _df_date.iloc[:, 0]
    df["Date"] = pd.to_datetime(_df_date, errors="coerce")

    _b_date = b["Date"] if "Date" in b.columns else pd.Series(pd.NaT, index=b.index)
    if isinstance(_b_date, pd.DataFrame):
        _b_date = _b_date.iloc[:, 0]
    b["Date"] = pd.to_datetime(_b_date, errors="coerce")

    df["_DateKey"] = df["Date"].dt.date
    b["_DateKey"]  = b["Date"].dt.date

    base = ["_DateKey", "team_key", "opp_key"]

    # Ensure we don't carry multiple 'Date' columns around
    bet_cols = [c for c in b.columns if c not in (base + ["Date"]) ]
    bet_cols = list(dict.fromkeys(bet_cols))  # preserve order, de-dupe

    # Tag which side the moneyline applies to; default for direct orientation is the row team
    if "bet_moneyline" in b.columns:
        b["bet_moneyline_for"] = "team"
    # Ensure the indicator column is preserved during merges
    if "bet_moneyline_for" in b.columns and "bet_moneyline_for" not in bet_cols:
        bet_cols.append("bet_moneyline_for")

    # --- Direct orientation ---
    m_dir = df.merge(b[base + bet_cols], on=base, how="left")

    # --- Swapped orientation (flip directional fields) ---
    b2 = b.rename(columns={"team_key": "opp_key", "opp_key": "team_key"}).copy()
    for c in DIRECTIONAL_BET_COLS:
        if c in b2.columns:
            b2[c] = -pd.to_numeric(b2[c], errors="coerce")
    if "bet_moneyline" in b2.columns:
        b2["bet_moneyline_for"] = "opp"

    m_sw = df.merge(b2[base + bet_cols], on=base, how="left")

    # --- Fill from swapped where direct is missing ---
    m_out = m_dir.copy()
    for c in bet_cols:
        if c in m_out.columns and c in m_sw.columns:
            m_out[c] = m_out[c].where(m_out[c].notna(), m_sw[c])

    # --- Moneyline: keep value + 0/1 indicator only ---
    if "bet_moneyline" in m_out.columns and "bet_moneyline_for" in m_out.columns:
        ind = m_out["bet_moneyline_for"].eq("team").astype(float)
        # Define indicator only where a moneyline exists; leave NaN otherwise
        ind = ind.where(m_out["bet_moneyline"].notna(), np.nan)
        m_out["bet_moneyline_for_team"] = ind
        # Drop the string tag column to keep schema minimal
        m_out = m_out.drop(columns=["bet_moneyline_for"], errors="ignore")

    # cleanup helper key
    return m_out.drop(columns=["_DateKey"], errors="ignore")

def make_per_game(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # ensure Date is datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # if game_key isn't present for any reason, build it vectorized
    if "game_key" not in df.columns:
        pair_key = np.where(
            df["team_key"] <= df["opp_key"],
            df["team_key"] + "_" + df["opp_key"],
            df["opp_key"] + "_" + df["team_key"],
        )
        df["game_key"] = pair_key + "_" + df["Date"].dt.strftime("%Y%m%d")

    # prefer the home row (is_home==1); otherwise keep first
    df = df.sort_values(["Date", "game_key", "is_home"], ascending=[True, True, False]).reset_index(drop=True)
    per_game = df.drop_duplicates(subset=["game_key"], keep="first")

    return per_game

def save_unmatched_aliases(year: str, betting: pd.DataFrame, labeled_before_merge: pd.DataFrame):
    """
    For a given season `year`, find all aliases in the betting dataframe that cannot be matched
    to any game in the labeled data (considering both team/opponent orientations).
    Save ONE CSV containing only the unique unmatched aliases (strings) for that year.

    Output columns: ["year", "unmatched_key"]
    File: BET_DIR / f"unmatched_{year}.csv"
    """
    # --- Build known (Date, team_key, opp_key) pairs from labeled data (both orientations) ---
    labeled = labeled_before_merge.copy()
    labeled_dates = pd.to_datetime(labeled["Date"], errors="coerce").dt.date

    games_fwd = set(zip(
        labeled_dates,
        labeled["team_key"].astype(str),
        labeled["opp_key"].astype(str),
    ))
    games_rev = set(zip(
        labeled_dates,
        labeled["opp_key"].astype(str),
        labeled["team_key"].astype(str),
    ))
    known_pairs = games_fwd | games_rev

    # Also track which team keys are known at all (for "unknown team" diagnostics)
    known_teams = set(labeled["team_key"].astype(str).unique())

    # --- Normalize betting side ---
    b = betting.copy()

    # Ensure unique column names (drop duplicate-named columns keeping the first)
    if b.columns.duplicated().any():
        b = b.loc[:, ~b.columns.duplicated()].copy()

    # If there are multiple literal 'Date' columns, keep the first
    if list(b.columns).count("Date") > 1:
        keep_cols = []
        seen_date = False
        for c in b.columns:
            if c == "Date":
                if not seen_date:
                    keep_cols.append(c)
                    seen_date = True
                # skip subsequent "Date" duplicates
            else:
                keep_cols.append(c)
        b = b.loc[:, keep_cols].copy()

    # Parse Date robustly even if pandas returned a DataFrame for duplicate column names
    if "Date" in b.columns:
        date_obj = b["Date"]
        # If duplicate column names slipped through and this is a DataFrame, take first col
        if isinstance(date_obj, pd.DataFrame):
            date_obj = date_obj.iloc[:, 0]
        b["Date"] = pd.to_datetime(date_obj, errors="coerce").dt.date
    else:
        b["Date"] = pd.NaT

    # Normalize key columns to strings (if present)
    if "team_key" in b.columns:
        b["team_key"] = b["team_key"].astype(str)
    else:
        b["team_key"] = ""
    if "opp_key" in b.columns:
        b["opp_key"]  = b["opp_key"].astype(str)
    else:
        b["opp_key"] = ""

    # --- Check match in either orientation ---
    tup    = list(zip(b["Date"], b["team_key"], b["opp_key"]))
    tup_sw = list(zip(b["Date"], b["opp_key"], b["team_key"]))
    has_match = pd.Series([t in known_pairs or t2 in known_pairs for t, t2 in zip(tup, tup_sw)], index=b.index)

    # --- Identify which side(s) are actually unknown (by team roster presence) ---
    team_ok = b["team_key"].isin(known_teams)
    opp_ok  = b["opp_key"].isin(known_teams)

    unmatched_mask = ~has_match

    # If a row is unmatched and the team_key isn't in known_teams, it's a bad team alias.
    bad_team_mask = unmatched_mask & (~team_ok)
    # If a row is unmatched and the opp_key isn't in known_teams, it's a bad opp alias.
    bad_opp_mask  = unmatched_mask & (~opp_ok)

    bad_keys = set()
    if bad_team_mask.any():
        bad_keys.update(b.loc[bad_team_mask, "team_key"].tolist())
    if bad_opp_mask.any():
        bad_keys.update(b.loc[bad_opp_mask, "opp_key"].tolist())

    # --- Clean out NA-like values and normalize whitespace ---
    def _clean_key(x: str) -> str:
        x = (x or "").strip()
        return x

    cleaned = {_clean_key(x) for x in bad_keys if pd.notna(x)}
    # Drop empties and common NA string tokens
    cleaned = {x for x in cleaned if x and x.lower() not in {"nan", "na", "none", "<na>"}}

    # --- Build output and save ---
    out_df = pd.DataFrame(sorted(cleaned), columns=["unmatched_key"])
    out_df.insert(0, "year", year)

    out_path = BET_DIR / f"unmatched_{year}.csv"
    out_df.to_csv(out_path, index=False)
    print(f"[unmatched] {len(out_df)} unique keys → {out_path}")

#
# --- Diagnostics helpers for no-bet reasons ---

def _bet_team_keys(b: pd.DataFrame) -> set:
    """Return set of all normalized betting team keys present in the betting table."""
    keys = set()
    if "team_key" in b.columns:
        keys.update(b["team_key"].astype(str).tolist())
    if "opp_key" in b.columns:
        keys.update(b["opp_key"].astype(str).tolist())
    # remove empties/NA-like
    keys = {k.strip() for k in keys if isinstance(k, str) and k and k.lower() not in {"nan","na","none","<na>"}}
    return keys

def _known_team_keys_from_labeled(labeled: pd.DataFrame) -> set:
    """Return set of team keys known from the labeled stats side (both team & opp)."""
    s = set()
    if "team_key" in labeled.columns:
        s.update(labeled["team_key"].astype(str).tolist())
    if "opp_key" in labeled.columns:
        s.update(labeled["opp_key"].astype(str).tolist())
    s = {k.strip() for k in s if isinstance(k, str) and k and k.lower() not in {"nan","na","none","<na>"}}
    return s

def _classify_no_bet_reason(row: pd.Series) -> str:
    """Classify why betting data was not attached for this row.
    Assumes the following columns exist in the row:
      - team_key, opp_key, exists_direct_in_bet, exists_swapped_in_bet,
        team_known_in_bet, opp_known_in_bet
    Returns a short machine-friendly reason string.
    """
    d = bool(row.get("exists_direct_in_bet", False))
    s = bool(row.get("exists_swapped_in_bet", False))
    team_known = bool(row.get("team_known_in_bet", False))
    opp_known  = bool(row.get("opp_known_in_bet", False))

    if not team_known:
        return "alias_mismatch_team"
    if not opp_known:
        return "alias_mismatch_opp"
    if d or s:
        # Betting table contains this game (direct or swapped) for the same day,
        # but merge still failed: indicates join-key mismatch (date dtype/time/tz) or duplicate Date columns
        return "join_key_mismatch"
    return "no_line_available"

def process_year(year: str):
    raw_path = raw_path_for(year)
    raw = pd.read_csv(raw_path)
    cleaned = prepare_rolling(raw)
    labeled = add_labels(cleaned, raw)

    # --- Season normalization of rolling features (adds z_* columns) ---
    try:
        labeled["season"] = int(year)
    except Exception:
        labeled["season"] = pd.to_numeric(year, errors="coerce")
    norm_cols = _norm_feature_candidates(labeled)
    if NORMALIZE_MODE == "season" and norm_cols:
        labeled = add_season_zscores(labeled, norm_cols, season_col="season", prefix=ZSCORE_PREFIX)
        print(f"[normalize] season z-scores added for {len(norm_cols)} roll features")
    elif NORMALIZE_MODE == "expanding" and norm_cols:
        labeled = add_expanding_season_zscores(labeled, norm_cols, date_col="Date", season_col="season", prefix=ZEXP_PREFIX)
        print(f"[normalize] expanding season z-scores added for {len(norm_cols)} roll features")
    else:
        if NORMALIZE_MODE not in {None, "season", "expanding"}:
            print(f"[normalize] UNKNOWN mode '{NORMALIZE_MODE}', skipping normalization")

    # Attach betting lines if available for this year
    try:
        bet = load_betting(year)
        bet = reduce_betting(bet)  # ensure one row per (day, team_key, opp_key)
        # Precompute the exact betting merge keys for diagnostics
        bet_keys_df = bet.copy()
        # Ensure unique columns (drop duplicate-named columns)
        if bet_keys_df.columns.duplicated().any():
            bet_keys_df = bet_keys_df.loc[:, ~bet_keys_df.columns.duplicated()].copy()
        # If there are multiple literal 'Date' columns, keep only the first
        if list(bet_keys_df.columns).count("Date") > 1:
            keep_cols = []
            seen_date = False
            for c in bet_keys_df.columns:
                if c == "Date":
                    if not seen_date:
                        keep_cols.append(c)
                        seen_date = True
                    # skip subsequent "Date" duplicates
                else:
                    keep_cols.append(c)
            bet_keys_df = bet_keys_df.loc[:, keep_cols].copy()
        # Parse Date robustly even if duplicate names slipped through
        if "Date" in bet_keys_df.columns:
            _date_obj = bet_keys_df["Date"]
            if isinstance(_date_obj, pd.DataFrame):
                _date_obj = _date_obj.iloc[:, 0]
            bet_keys_df["Date"] = parse_dates(_date_obj)
        else:
            bet_keys_df["Date"] = pd.NaT
        bet_keys_df["_lookup_direct"] = (
            bet_keys_df["Date"].dt.strftime("%Y%m%d") + "|" +
            bet_keys_df["team_key"].astype(str) + "|" +
            bet_keys_df["opp_key"].astype(str)
        )
        BET_KEY_SET = set(bet_keys_df["_lookup_direct"].dropna().astype(str))
        # Precompute sets for diagnostics
        bet_team_key_set = _bet_team_keys(bet)
        known_teams_set  = _known_team_keys_from_labeled(labeled)
        save_unmatched_aliases(year, bet, labeled)
        labeled = merge_betting(labeled, bet)
        # Enforce consistent betting schema across seasons
        labeled = ensure_bet_schema(labeled)

        # Save all rows that don't have any betting data to a separate CSV
        bet_indicator_cols = [
            "bet_total", "bet_spread", "bet_ou_margin",
            "bet_moneyline", "bet_ats_margin", "bet_mov"
        ]
        present_bet_cols = [c for c in bet_indicator_cols if c in labeled.columns]
        if present_bet_cols:
            has_any_bet = labeled[present_bet_cols].notna().any(axis=1)
            no_bet_mask = ~has_any_bet
            if no_bet_mask.any():
                # Ensure we have is_home available to prefer a single per-game row
                if "is_home" not in labeled.columns:
                    labeled["is_home"] = ((labeled.get("Location", "").fillna("")) != "@").astype(int)
                no_bet_df = labeled.loc[no_bet_mask, :].copy()
                no_bet_df["Date"] = pd.to_datetime(no_bet_df["Date"], errors="coerce")
                # Build the exact lookup keys we attempt against betting data
                date_str = no_bet_df["Date"].dt.strftime("%Y%m%d")
                no_bet_df["lookup_team_key"] = no_bet_df["team_key"].astype(str)
                no_bet_df["lookup_opp_key"]  = no_bet_df["opp_key"].astype(str)
                no_bet_df["lookup_direct"] = date_str + "|" + no_bet_df["lookup_team_key"] + "|" + no_bet_df["lookup_opp_key"]
                no_bet_df["lookup_swapped"] = date_str + "|" + no_bet_df["lookup_opp_key"] + "|" + no_bet_df["lookup_team_key"]
                # Whether those exact lookup keys exist in betting data
                no_bet_df["exists_direct_in_bet"] = no_bet_df["lookup_direct"].isin(BET_KEY_SET)
                no_bet_df["exists_swapped_in_bet"] = no_bet_df["lookup_swapped"].isin(BET_KEY_SET)
                # Team presence checks against betting table (helps pinpoint alias issues)
                no_bet_df["team_known_in_bet"] = no_bet_df["lookup_team_key"].isin(bet_team_key_set)
                no_bet_df["opp_known_in_bet"]  = no_bet_df["lookup_opp_key"].isin(bet_team_key_set)

                # Human-friendly reason why we could not attach betting data
                no_bet_df["no_bet_reason"] = no_bet_df.apply(_classify_no_bet_reason, axis=1)

                # Quick console breakdown to guide fixes
                reason_counts = no_bet_df["no_bet_reason"].value_counts(dropna=False)
                print("[no-betting reasons]", {k: int(v) for k, v in reason_counts.to_dict().items()})
                # Raw slugs (pre-alias) for visibility
                if "Team" in no_bet_df.columns:
                    no_bet_df["team_slug_raw"] = slug(no_bet_df["Team"])
                if "Opp" in no_bet_df.columns:
                    no_bet_df["opp_slug_raw"] = slug(no_bet_df["Opp"])
                # Now build export columns using the actual df columns (so lookup_* are kept)
                export_cols = [
                    "Date", "team_key", "opp_key", "Team", "Opp", "is_home",
                    "team_slug_raw", "opp_slug_raw",
                    "lookup_team_key", "lookup_opp_key", "lookup_direct", "lookup_swapped",
                    "exists_direct_in_bet", "exists_swapped_in_bet",
                ]
                export_cols = [c for c in export_cols if c in no_bet_df.columns]
                # Add new diagnostic columns if present
                for extra_col in ["team_known_in_bet","opp_known_in_bet","no_bet_reason"]:
                    if extra_col in no_bet_df.columns and extra_col not in export_cols:
                        export_cols.append(extra_col)
                export_cols += present_bet_cols
                no_bet_df = no_bet_df[export_cols].copy()
                pair_key = np.where(
                    no_bet_df["team_key"] <= no_bet_df["opp_key"],
                    no_bet_df["team_key"] + "_" + no_bet_df["opp_key"],
                    no_bet_df["opp_key"] + "_" + no_bet_df["team_key"],
                )
                no_bet_df["game_key"] = pair_key + "_" + no_bet_df["Date"].dt.strftime("%Y%m%d")
                # Prefer home row when present; otherwise keep first occurrence
                sort_cols = ["Date", "game_key"]
                if "is_home" in no_bet_df.columns:
                    no_bet_df = no_bet_df.sort_values(sort_cols + ["is_home"], ascending=[True, True, False])
                else:
                    no_bet_df = no_bet_df.sort_values(sort_cols, ascending=[True, True])
                no_bet_per_game = no_bet_df.drop_duplicates(subset=["game_key"], keep="first").copy()
                # Sort by reason severity then by team/date for readability
                reason_order = {"alias_mismatch_team": 0, "alias_mismatch_opp": 1, "join_key_mismatch": 2, "no_line_available": 3}
                if "no_bet_reason" in no_bet_per_game.columns:
                    no_bet_per_game.loc[:, "_reason_rank"] = no_bet_per_game["no_bet_reason"].map(reason_order).fillna(99)
                    sort_cols2 = ["_reason_rank", "team_key", "Date"] if {"team_key","Date"}.issubset(no_bet_per_game.columns) else ["_reason_rank"]
                    no_bet_per_game = no_bet_per_game.sort_values(sort_cols2, ascending=[True, True, True]).drop(columns=["_reason_rank"], errors="ignore")
                no_bet_path = BET_DIR / f"no_betting_{year}.csv"
                no_bet_per_game.to_csv(no_bet_path, index=False)
                print(f"[no-betting] {len(no_bet_per_game)} games without betting data → {no_bet_path}")
                print("[hint] Open the CSV and filter by no_bet_reason to fix aliases first; if many 'join_key_mismatch', switch to a day-only DateKey merge.")
        else:
            print("[no-betting] No betting columns present; skipping export.")
    except FileNotFoundError:
        print(f"[INFO] No betting file for {year} in {BET_DIR}")

    # (per-team file writing removed)

    # per-game file (1 row per game)
    per_game = make_per_game(labeled)
    # Also ensure per-game has canonical betting columns
    per_game = ensure_bet_schema(per_game)
    # Sort alphabetically by team_key (then Date for stability)
    if "team_key" in per_game.columns:
        per_game = per_game.sort_values(["team_key", "Date"], ascending=[True, True])
    per_game_path = OUT_DIR / f"per_game_{year}.csv"
    per_game.to_csv(per_game_path, index=False)
    print(f"Saved per-game dataset -> {per_game_path}")

    print(f"Rows({year}) -> cleaned: {len(cleaned)} | labeled: {len(labeled)} | per_game: {len(per_game)}")

    # Betting coverage diagnostic (per-game)
    bet_cols_present = [c for c in ["bet_total", "bet_spread"] if c in per_game.columns]
    if bet_cols_present:
        has_bet = per_game[bet_cols_present].notna().any(axis=1).mean()
        print(f"Betting coverage ({year}): {has_bet:.1%} of per-game rows have betting lines")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for yr in YEAR_LIST:
        try:
            process_year(yr)
        except FileNotFoundError:
            print(f"[WARN] Raw file missing for {yr}: {raw_path_for(yr)} — skipping.")



if __name__ == "__main__":
    
    main()
