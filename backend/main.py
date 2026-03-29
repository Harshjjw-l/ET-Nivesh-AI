import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import ta
import pandas as pd

import requests
import yfinance as yf
from fastapi import FastAPI, Query

from services.stock_resolver import (
    load_stock_data,
    resolve_stock,
    resolve_portfolio_stocks,
    search_stocks
)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
load_dotenv()
try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore

app = FastAPI(title="ET Nivesh AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── INPUT NORMALIZATION / ALIAS HELPERS ──────────────────────────
def _normalize_ticker(raw: str) -> Optional[str]:
    t = (raw or "").strip().upper()
    if not t:
        return None
    t = re.sub(r"[^A-Z0-9\.]", "", t)
    if not t:
        return None
    if t.endswith(".NS"):
        base = t[:-3]
        if base and re.fullmatch(r"[A-Z0-9]{1,15}", base):
            return t
        return None
    if re.fullmatch(r"[A-Z0-9]{1,15}", t):
        return f"{t}.NS"
    return None


_NAME_TO_NSE_TICKER: Dict[str, str] = {
    "RELIANCE": "RELIANCE.NS",
    "RELIANCE INDUSTRIES": "RELIANCE.NS",
    "TATA CONSULTANCY SERVICES": "TCS.NS",
    "TCS": "TCS.NS",
    "INFOSYS": "INFY.NS",
    "INFY": "INFY.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "SBI": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "MARUTI": "MARUTI.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "NTPC": "NTPC.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "TECH MAHINDRA": "TECHM.NS",
    "TECHM": "TECHM.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
    "ADANIENT": "ADANIENT.NS",
    "WIPRO": "WIPRO.NS",
    "POWER GRID": "POWERGRID.NS",
    "POWERGRID": "POWERGRID.NS",
    "ONGC": "ONGC.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "TITAN": "TITAN.NS",
    "ULTRATECH CEMENT": "ULTRACEMCO.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
}


def _clean_mapping_key(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _name_to_nse_ticker(raw: str) -> Optional[str]:
    direct = _normalize_ticker(raw)
    if direct:
        return direct

    cleaned = _clean_mapping_key(raw)
    if not cleaned:
        return None

    for name, ticker in _NAME_TO_NSE_TICKER.items():
        if _clean_mapping_key(name) == cleaned:
            return ticker

    for name, ticker in _NAME_TO_NSE_TICKER.items():
        if _clean_mapping_key(name) in cleaned:
            return ticker

    return None
@app.on_event("startup")
def startup_event():
    load_stock_data("data/EQUITY_L.csv")


@app.get("/")
def home():
    return {"message": "Backend running"}


@app.get("/resolve-stock")
def resolve_stock_api(q: str = Query(...)):
    return resolve_stock(q)

@app.get("/search-stock")
def search_stock_api(q: str = Query(...)):
    return {"results": search_stocks(q, limit=5)}
@app.post("/analyze")
def analyze_stock(data: dict):
    question_stock_input = data.get("question_stock")
    portfolio = data.get("portfolio", [])

    # Resolve asked stock
    question_stock = resolve_stock(question_stock_input)

    if question_stock["status"] != "success":
        return {
            "status": "error",
            "message": question_stock["message"]
        }

    # Resolve portfolio stocks
    portfolio_result = resolve_portfolio_stocks(portfolio)

    # Combine all tickers
    all_tickers = [question_stock["ticker"]] + portfolio_result["resolved_tickers"]
    all_tickers = list(set(all_tickers))

    print("Final tickers for analysis:", all_tickers)

    return {
        "status": "success",
        "question_stock": question_stock,
        "portfolio_result": portfolio_result,
        "all_tickers": all_tickers
    }


SYSTEM_PROMPT = (
    "You are ET Nivesh AI, a friendly investment assistant for first-time Indian investors. "
    "Never use financial jargon without explaining it simply. "
    "Always give a clear entry price range, profit target and stop loss level. "
    "If any stock exceeds 30% of the user's portfolio value, warn them about concentration risk. "
    "End every response with: This is for informational purposes only — not financial advice. "
    "The final decision is always yours."
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    portfolio: List[str] = Field(default_factory=list)
    investment_amount: float = Field(default=0)
    total_invested: float = Field(default=0, ge=0)
    timeframe: str = Field(..., min_length=1)
    selected_stock: Optional[str] = None


from typing import Optional, List, Any

class ChatResponse(BaseModel):
    status: Optional[str] = None
    answer: Optional[str] = None

    entry_price: Optional[Any] = None
    target_price: Optional[Any] = None
    stop_loss: Optional[Any] = None

    rsi_value: Optional[Any] = None
    rsi_explanation: Optional[str] = None

    sources_used: Optional[List[str]] = None
    timestamp: Optional[str] = None

    concentration_warning: Optional[str] = None
    bulk_deals: Optional[Any] = None
    budget_note: Optional[str] = None

    options: Optional[List[dict]] = None

_IST_TZ = timezone(timedelta(hours=5, minutes=30))


def _ist_now() -> datetime:
    return datetime.now(_IST_TZ)


def _ist_time_str() -> str:
    # Example: "14:32 IST"
    return _ist_now().strftime("%H:%M IST")


def _ist_timestamp_str() -> str:
    # Full datetime, not just date: "2026-03-27 14:32:10 IST"
    return _ist_now().strftime("%Y-%m-%d %H:%M:%S IST")


def _normalize_ticker(raw: str) -> Optional[str]:
    t = (raw or "").strip().upper()
    if not t:
        return None
    t = re.sub(r"[^A-Z0-9\.]", "", t)
    if not t:
        return None
    if t.endswith(".NS"):
        base = t[:-3]
        if base and re.fullmatch(r"[A-Z0-9]{1,15}", base):
            return t
        return None
    if re.fullmatch(r"[A-Z0-9]{1,15}", t):
        return f"{t}.NS"
    return None


_NAME_TO_NSE_TICKER: Dict[str, str] = {
    # Common Indian tickers / names (extend as needed)
    "RELIANCE": "RELIANCE.NS",
    "RELIANCE INDUSTRIES": "RELIANCE.NS",
    "TATA CONSULTANCY SERVICES": "TCS.NS",
    "TATA CONSULTANCY SERVICE": "TCS.NS",
    "TCS": "TCS.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "INFOSYS": "INFY.NS",
    "WIPRO": "WIPRO.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "SBIN": "SBIN.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "GARDEN REACH SHIPBUILDERS": "GRSE.NS",
    "GRSE": "GRSE.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
    "ADANIENT": "ADANIENT.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "MARUTI": "MARUTI.NS",
    "NTPC": "NTPC.NS",
    "OIL AND NATURAL GAS CORPORATION": "ONGC.NS",
    "ONGC": "ONGC.NS",
    "POWER GRID": "POWERGRID.NS",
    "POWERGRID": "POWERGRID.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "SUN PHARMACEUTICAL INDUSTRIES": "SUNPHARMA.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "TECH MAHINDRA": "TECHM.NS",
    "TECHM": "TECHM.NS",
    "TITAN": "TITAN.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "ULTRACEMCO LIMITED": "ULTRACEMCO.NS",
    "ULTRATECH CEMENT": "ULTRACEMCO.NS",
    # Extra common name aliases (lowercase inputs are cleaned before matching)
    "HDFC": "HDFCBANK.NS",
    "AXIS BANK": "AXISBANK.NS",
    "AXIS": "AXISBANK.NS",
    "KOTAK": "KOTAKBANK.NS",
    "KOTAK MAHINDRA": "KOTAKBANK.NS",
    "ITC": "ITC.NS",
    "L&T": "LT.NS",
    "LARSEN": "LT.NS",
    "BHARTI": "BHARTIARTL.NS",
    "AIRTEL": "BHARTIARTL.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "SUN PHARMACEUTICAL": "SUNPHARMA.NS",
    "ADANI PORTS": "ADANIPORTS.NS",
    "ADANI": "ADANIPORTS.NS",
    "POWER GRID": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "ASIAN PAINTS": "ASIANPAINT.NS",
    "ULTRATECH": "ULTRACEMCO.NS",
    "BAJAJ AUTO": "BAJAJ-AUTO.NS",
    "DR REDDY": "DRREDDY.NS",
    "CIPLA": "CIPLA.NS",
    "DIVIS": "DIVISLAB.NS",
    "HCL": "HCLTECH.NS",
    "COAL INDIA": "COALINDIA.NS",
    "HINDALCO": "HINDALCO.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "JSW": "JSWSTEEL.NS",
    "TATA STEEL": "TATASTEEL.NS",
    "TATA POWER": "TATAPOWER.NS",
    "INDUSIND": "INDUSINDBK.NS",
    "SBI LIFE": "SBILIFE.NS",
    "HDFC LIFE": "HDFCLIFE.NS",
    "BAJAJ FINSERV": "BAJAJFINSV.NS",
}


def _clean_mapping_key(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _name_to_nse_ticker(raw: str) -> Optional[str]:
    """
    Convert a portfolio "share name" to an NSE ticker symbol.
    If the input already looks like a ticker (e.g., TCS or TCS.NS), we normalize it directly.
    """
    direct = _normalize_ticker(raw)
    if direct:
        return direct

    cleaned = _clean_mapping_key(raw)
    if not cleaned:
        return None

    # Exact match on cleaned name
    for name, ticker in _NAME_TO_NSE_TICKER.items():
        if _clean_mapping_key(name) == cleaned:
            return ticker

    # Substring match (handles extra words like "Ltd", "Limited", etc.)
    for name, ticker in _NAME_TO_NSE_TICKER.items():
        if _clean_mapping_key(name) in cleaned:
            return ticker

    return None


def _extract_nse_tickers_from_question(question: str) -> List[str]:
    q = (question or "").upper()
    candidates = set()

    # Explicit forms: RELIANCE.NS, TCS.NS
    for m in re.finditer(r"\b([A-Z0-9]{1,15}\.NS)\b", q):
        candidates.add(m.group(1))

    # Loose uppercase tokens; we normalize to .NS
    for m in re.finditer(r"\b([A-Z]{2,15})\b", q):
        tok = m.group(1)
        if tok in {"NSE", "BSE", "RSI", "ETF", "SIP", "IPO", "PE", "P/E"}:
            continue
        norm = _normalize_ticker(tok)
        if norm:
            candidates.add(norm)

    return sorted(candidates)


def _unique_nse_tickers(question: str, portfolio: List[str]) -> List[str]:
    # IMPORTANT: Tickers must come only from the explicit `portfolio` list.
    # The `question` is used for intent only, not for extracting tickers.
    tickers = set()
    for p in portfolio or []:
        norm = _name_to_nse_ticker(p)
        if not norm:
            # If mapping fails, still try basic ticker normalization.
            norm = _normalize_ticker(p)
        if norm:
            tickers.add(norm)
    return sorted(tickers)


def _fetch_last_20_days(ticker: str) -> pd.DataFrame:
    print("Fetching data for:", ticker)

    df = yf.Ticker(ticker).history(period="2mo", interval="1d")

    if df is None or df.empty:
        raise ValueError(f"No price data returned for {ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    cols = {c.lower(): c for c in df.columns}
    if "close" not in cols:
        raise ValueError(f"Missing Close column for {ticker}")

    df = df.dropna(subset=[cols["close"]]).copy()
    df = df.tail(20)

    if df.empty:
        raise ValueError(f"Not enough price data for {ticker}")

    print("SUCCESS:", ticker, "rows:", len(df))
    return df

def _compute_support_resistance(df: pd.DataFrame, current_price: float, timeframe: str = "long term") -> Dict[str, Any]:
    """
    Compute entry, target and stop-loss based on timeframe.
    """
    timeframe = (timeframe or "").lower()

    if "intraday" in timeframe:
        target_multiplier = 1.02   # +2%
        stop_multiplier = 0.99     # -1%
        entry_buffer = 0.005       # 0.5%
    elif "short" in timeframe or "1 month" in timeframe or "3 month" in timeframe:
        target_multiplier = 1.06   # +6%
        stop_multiplier = 0.96     # -4%
        entry_buffer = 0.01        # 1%
    else:
        # long term / 12 month
        target_multiplier = 1.15   # +15%
        stop_multiplier = 0.92     # -8%
        entry_buffer = 0.02        # 2%

    entry_low = round(current_price * (1 - entry_buffer), 2)
    entry_high = round(current_price * (1 + entry_buffer / 2), 2)
    target = round(current_price * target_multiplier, 2)
    stop_loss = round(current_price * stop_multiplier, 2)

    return {
        "entry_price": f"₹{entry_low}–₹{entry_high}",
        "target_price": target,
        "stop_loss": stop_loss,
    }

def _compute_rsi(close_series: pd.Series, length: int = 14) -> Tuple[Optional[float], str]:
    try:
        delta = close_series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=length).mean()
        loss = -delta.where(delta < 0, 0.0).rolling(window=length).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        val = float(rsi.dropna().iloc[-1])
        if val >= 70:
            expl = f"RSI is {val:.2f} — overbought (price rose too fast, may pull back)."
        elif val <= 30:
            expl = f"RSI is {val:.2f} — oversold (price fell too fast, may bounce)."
        else:
            expl = f"RSI is {val:.2f} — neutral zone."
        return val, expl
    except Exception:
        return None, "RSI could not be computed."

def _portfolio_concentration_flags(portfolio: List[str]) -> List[str]:
    # We don't have holdings/weights, so we assume equal allocation of the given portfolio list.
    p = [t for t in (portfolio or []) if (t or "").strip()]
    n = len(p)
    if n <= 0:
        return []
    weight = 1.0 / n
    if weight > 0.30:
        return [f"Equal-weight concentration risk: with {n} holdings, each is ~{weight*100:.0f}% of the portfolio."]
    return []


def _concentration_warning(tickers: List[str], investment_amount: float) -> Optional[str]:
    """
    Equal-weight assumption: distribute `investment_amount` equally across tickers.
    If any single stock is >30% of total, return a warning string.
    """
    n = len(tickers or [])
    if n <= 0 or investment_amount <= 0:
        return None
    pct = 100.0 / n
    if pct <= 30.0:
        return None
    # If equal-weight exceeds 30%, then every holding is concentrated; pick the first ticker for message.
    t0 = (tickers[0] or "").split(".")[0] if tickers else "This stock"
    pct_int = int(round(pct))
    return (
        f"{t0} makes up {pct_int}% of your portfolio. Buying more increases your risk if this stock falls. "
        "Consider diversifying."
    )


def _fetch_nse_bulk_deals_for_portfolio(portfolio_tickers: List[str]) -> Any:
    """
    Fetch today's bulk deals from NSE and filter for portfolio tickers.
    Returns a list of matching deals, or a string message if none found.
    """
    bases = {(t or "").upper().replace(".NS", "") for t in (portfolio_tickers or []) if (t or "").strip()}
    if not bases:
        return "No bulk deal activity today for your stocks"

    # NSE requires a session cookie established from homepage.
    homepage = "https://www.nseindia.com"
    # NSE changed bulk deals endpoints; "largedeal snapshot" supports bulk deals via mode parameter.
    urls_to_try = [
        "https://www.nseindia.com/api/snapshot-capital-market-largedeal?mode=bulk_deals",
        # Fallbacks (may be retired / blocked depending on region/network)
        "https://www.nseindia.com/api/bulkdeals",
        "https://www.nseindia.com/api/bulk-deals",
        "https://www.nseindia.com/api/bulkdeals/",
        "https://www.nseindia.com/api/bulk-deals/",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com",
    }

    raw: Optional[str] = None
    last_err: Optional[str] = None
    try:
        with requests.Session() as s:
            s.get(homepage, headers=headers, timeout=10)
            for url in urls_to_try:
                try:
                    resp = s.get(url, headers=headers, timeout=10)
                    if resp.status_code == 404:
                        last_err = f"404 Not Found for url: {url}"
                        continue
                    resp.raise_for_status()
                    raw = resp.text
                    break
                except Exception as e:
                    last_err = str(e)
                    continue
    except Exception as e:
        return f"NSE bulk deals fetch failed: {e}"

    if raw is None:
        return "NSE bulk deals fetch failed: " + (last_err or f"all endpoints failed. Tried: {', '.join(urls_to_try)}")

    try:
        payload = json.loads(raw)
    except Exception:
        return "NSE bulk deals fetch failed: invalid JSON response"

    # Snapshot endpoint sometimes returns {"data":[...]} or other shapes; support both.
    rows = None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            rows = payload.get("data")
        elif isinstance(payload.get("bulk_deals"), list):
            rows = payload.get("bulk_deals")
    if not isinstance(rows, list) or not rows:
        return "No bulk deal activity today for your stocks"

    matches: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        sym = str(r.get("symbol") or "").upper().strip()
        if sym and sym in bases:
            # Keep the raw row (it's already structured), but ensure symbol is present
            matches.append(r)

    if not matches:
        return "No bulk deal activity today for your stocks"

    return matches


def _fetch_nse_bulk_deals(limit: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch latest bulk deals from NSE and return up to `limit` rows.
    """
    homepage = "https://www.nseindia.com"
    urls_to_try = [
        "https://www.nseindia.com/api/snapshot-capital-market-largedeal?mode=bulk_deals",
        "https://www.nseindia.com/api/bulkdeals",
        "https://www.nseindia.com/api/bulk-deals",
        "https://www.nseindia.com/api/bulkdeals/",
        "https://www.nseindia.com/api/bulk-deals/",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com",
    }

    raw: Optional[str] = None
    with requests.Session() as s:
        s.get(homepage, headers=headers, timeout=10)
        for url in urls_to_try:
            resp = s.get(url, headers=headers, timeout=10)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            raw = resp.text
            break

    if raw is None:
        return []

    payload = json.loads(raw)
    rows: Any = None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            rows = payload.get("data")
        elif isinstance(payload.get("bulk_deals"), list):
            rows = payload.get("bulk_deals")
    if not isinstance(rows, list):
        return []

    clean_rows = [r for r in rows if isinstance(r, dict)]
    return clean_rows[: max(0, limit)]


def _groq_client() -> Any:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")
    if Groq is None:
        raise RuntimeError("Groq client not installed. Install with: pip install groq")
    return Groq(api_key=api_key)


def _safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # Try to extract first JSON object in the text
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


@app.get("/test-ticker/{ticker}")
def test_ticker(ticker: str) -> Dict[str, Any]:
    norm = _normalize_ticker(ticker)
    if not norm:
        raise HTTPException(status_code=400, detail="Invalid ticker format. Example: TCS or TCS.NS")

    fetch_time_ist = _ist_time_str()
    try:
        df = _fetch_last_20_days(norm)
        close_col = "Close" if "Close" in df.columns else [c for c in df.columns if c.lower() == "close"][0]
        current_price = float(df[close_col].iloc[-1])
        return {
            "ticker": norm,
            "current_price": current_price,
            "fetched_at": fetch_time_ist,
        }
    except Exception as e:
        return {
            "ticker": norm,
            "error": str(e),
            "fetched_at": fetch_time_ist,
        }


@app.get("/test-all-tickers")
def test_all_tickers() -> Dict[str, Any]:
    base = [
        "RELIANCE",
        "TCS",
        "HDFCBANK",
        "INFY",
        "WIPRO",
        "SBIN",
        "ICICIBANK",
        "BAJFINANCE",
        "GRSE",
        "TATAMOTORS",
        "ADANIENT",
        "HINDUNILVR",
        "MARUTI",
        "NTPC",
        "ONGC",
        "POWERGRID",
        "SUNPHARMA",
        "TECHM",
        "TITAN",
        "ULTRACEMCO",
    ]
    tickers = [f"{t}.NS" for t in base]
    fetched_at = _ist_time_str()

    working: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    for t in tickers:
        try:
            df = _fetch_last_20_days(t)
            close_col = "Close" if "Close" in df.columns else [c for c in df.columns if c.lower() == "close"][0]
            current_price = float(df[close_col].iloc[-1])
            working.append(
                {
                    "ticker": t,
                    "current_price": current_price,
                    "fetched_at": fetched_at,
                }
            )
        except Exception as e:
            failed.append(
                {
                    "ticker": t,
                    "error": str(e),
                    "fetched_at": fetched_at,
                }
            )

    return {"working": working, "failed": failed}

def extract_stock_from_question(question: str) -> Optional[str]:
    """
    Try to detect a stock name from natural-language question
    using CSV search suggestions.
    """
    if not question or not question.strip():
        return None

    cleaned = question.lower()

    filler_phrases = [
     "should i buy",
     "should i invest in",
     "can i buy",
     "is it good to buy",
     "for 1 year",
     "for one year",
     "for 6 months",
     "for six months",
     "for long term",
     "for short term",
     "if market crashes",
     "if the market crashes",
     "now",
     "today",
     "right now",
     "stock",
     "share",
     "what about",
     "bro",
     "what do you think about",
     "at current level",
     "consider buying",
     "wealth creation",
     "analyze",
     "analyse",
     "should i buy?",
     "what with",
     "what's with",
]

    for phrase in filler_phrases:
        cleaned = cleaned.replace(phrase, " ")

    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()
    if words:
      cleaned = words[-1]
    if not cleaned:
        return None

    # First try alias / direct ticker mapping
    alias_ticker = _name_to_nse_ticker(cleaned)
    if alias_ticker:
        return alias_ticker.replace(".NS", "")
    if alias_ticker:
        return alias_ticker.replace(".NS", "")
    matches = search_stocks(cleaned, limit=5)

    best_match = None

    for m in matches:
        name = m["company_name"].lower()

        if all(word in name for word in cleaned.split()):
            best_match = m
            break

    if best_match:
        return best_match["company_name"]

    return None


@app.get("/signals/today")
def today_signals() -> Dict[str, Any]:
    try:
        deals = _fetch_nse_bulk_deals(limit=3)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch bulk deals: {e}")
    return {"timestamp": _ist_timestamp_str(), "deals": deals}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # -----------------------------------
    # Step 7: Resolve stock from question
    # -----------------------------------
    question_ticker = None

    if req.selected_stock:
       print("Using frontend selected stock:", req.selected_stock)
       question_stock = resolve_stock(req.selected_stock)
    else:
       clean_question = extract_stock_from_question(req.question)
       print("Clean extracted stock text:", clean_question)
       matches = search_stocks(clean_question, limit=5)

       if len(matches) > 1:
         return {
           "status": "need_selection",
           "options": matches
        }
       question_stock = resolve_stock(clean_question)

    if question_stock["status"] == "success": 
       question_ticker = question_stock["ticker"]


    # -----------------------------------
    # Resolve portfolio stocks
    # -----------------------------------
    portfolio_result = resolve_portfolio_stocks(req.portfolio)

    # -----------------------------------
    # Combine all tickers
    # -----------------------------------
    tickers = portfolio_result["resolved_tickers"]

    if question_ticker:
      tickers = [question_ticker] + tickers

# remove duplicates while preserving order
    seen = set()
    ordered_tickers = []
    for t in tickers:
      if t not in seen:
        seen.add(t)
        ordered_tickers.append(t)

    tickers = ordered_tickers

    print("Final tickers for analysis:", tickers)

    prices: Dict[str, Dict[str, Any]] = {}
    rsi_by_ticker: Dict[str, Dict[str, Any]] = {}
    technical_levels: Dict[str, Dict[str, Any]] = {}
    fetched_sources_used: List[str] = []

    for t in tickers:
     fetch_time_ist = _ist_time_str()
     try:
        print("Trying ticker:", t)

        df = _fetch_last_20_days(t)
        close_col = "Close" if "Close" in df.columns else [c for c in df.columns if c.lower() == "close"][0]
        rsi_val, rsi_expl = _compute_rsi(df[close_col])
        current_price = float(df[close_col].iloc[-1])

        sr = _compute_support_resistance(df, current_price, req.timeframe)
        technical_levels[t] = sr

        if rsi_val is None:
            fetched_sources_used.append(f"{t}: data unavailable — please verify NSE symbol")
        else:
            fetched_sources_used.append(
                f"{t}: current price={current_price:.2f}, RSI={rsi_val:.2f}, fetched_at={fetch_time_ist}"
            )

        prices[t] = {
            "last_20_days": [
                {
                    "date": idx.date().isoformat() if hasattr(idx, "date") else str(idx),
                    "close": float(row[close_col])
                }
                for idx, row in df.iterrows()
            ]
        }

        rsi_by_ticker[t] = {
            "rsi_value": rsi_val,
            "rsi_explanation": rsi_expl
        }

     except Exception as e:
        print("FAILED:", t, str(e))

        fetched_sources_used.append(f"{t}: data unavailable — please verify NSE symbol")
        prices[t] = {"error": str(e)}
        rsi_by_ticker[t] = {
            "rsi_value": None,
            "rsi_explanation": "RSI unavailable due to missing price data."
        }

    concentration_notes = _portfolio_concentration_flags(req.portfolio)
    concentration_warning = _concentration_warning(tickers, req.investment_amount)
    bulk_deals = _fetch_nse_bulk_deals_for_portfolio(tickers)
    budget_note = None
    portfolio_context_note = None

    if req.total_invested > 0 and tickers:
      avg_per_stock = req.total_invested / len(tickers)
      portfolio_context_note = (
        f"User has already invested approximately ₹{int(req.total_invested):,} "
        f"across {len(tickers)} stock(s), averaging about ₹{avg_per_stock:,.0f} per stock."
     )

    primary = question_ticker if question_ticker else (tickers[0] if tickers else None)

    if primary and primary in prices and "error" not in prices[primary]:
     try:
        latest_price = prices[primary]["last_20_days"][-1]["close"]

        if req.investment_amount < latest_price:
            budget_note = (
              f"⚠️ Your budget of ₹{int(req.investment_amount):,} is less than "
              f"the current price of ₹{latest_price:,.2f}. "
              f"You cannot buy even 1 share."
            )
        else:
            shares = int(req.investment_amount // latest_price)
            remaining_cash = round(req.investment_amount - (shares * latest_price), 2)

            budget_note = (
               f"With ₹{int(req.investment_amount):,}, you can buy approximately "
               f"{shares} share(s) at ₹{latest_price:,.2f} each, "
               f"with about ₹{remaining_cash:,.2f} left."
            )
     except Exception:
        pass

    user_payload = {
        "question": req.question,
        "portfolio": req.portfolio,
        "investment_amount": req.investment_amount,
        "total_invested": req.total_invested,
        "portfolio_context_note": portfolio_context_note,
        "timeframe": req.timeframe,
        "nse_tickers_found": tickers,
        "prices": prices,
        "rsi": rsi_by_ticker,
        "technical_levels": technical_levels,
        "budget_note": budget_note,
        "concentration_notes": concentration_notes,
        "concentration_warning": concentration_warning,
        "bulk_deals": bulk_deals,
        "bulk_deals_note": "Bulk deals indicate large institutional buying or selling activity.",
        "output_format": {
            "must_be_json": True,
            "fields": [
                "answer",
                "entry_price",
                "target_price",
                "stop_loss",
                "rsi_value",
                "rsi_explanation",
                "sources_used",
                "timestamp",
                "concentration_warning",
                "bulk_deals",
                "budget_note",
            ],
        },
    }

    try:
        client = _groq_client()
        system_prompt = SYSTEM_PROMPT

        if concentration_warning:
            system_prompt = (
                SYSTEM_PROMPT
                + " Concentration warning (reference this in the answer if relevant): "
                + concentration_warning
            )

        if bulk_deals:
            system_prompt = (
                system_prompt
                + " Additional context: bulk deals indicate large institutional buying or selling activity."
            )

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Use the provided NSE price data (last 20 trading days), RSI info, technical levels, and budget note to answer. "
                        "Write the answer in a natural, beginner-friendly, slightly conversational tone. "
                        "Explain WHY the stock looks attractive or risky in 2–3 lines, not just raw numbers. "
                        "Always mention RSI meaning in simple words. "
                        "Always mention entry, target, stop loss, and budget note if available. "
                        "If total invested amount is available, mention whether this looks like a fresh buy, a small add-on, or a major portfolio exposure increase. "
                        "If concentration risk exists, explain it clearly in simple words. "
                        "Return ONLY a single valid JSON object with the required fields. "
                        "If multiple tickers exist, focus on the most relevant one to the user's question, "
                        "but still mention the others briefly in the answer.\n\n"
                        
                        f"{json.dumps(user_payload, ensure_ascii=False)}"
                    ),
                },
            ],
            temperature=0.45,
        )

        content = (completion.choices[0].message.content or "").strip()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    obj = _safe_json_extract(content)

    if not obj:
        primary = tickers[0] if tickers else None
        rsi_val = (rsi_by_ticker.get(primary, {}) or {}).get("rsi_value") if primary else None
        rsi_expl = (rsi_by_ticker.get(primary, {}) or {}).get("rsi_explanation") if primary else "RSI unavailable."

        return ChatResponse(
            answer=(
                "I couldn't parse the model response as JSON. "
                "Please try again, or shorten the question."
                "\n\nThis is for informational purposes only — not financial advice. The final decision is always yours."
            ),
            entry_price=None,
            target_price=None,
            stop_loss=None,
            rsi_value=rsi_val,
            rsi_explanation=rsi_expl,
            sources_used=fetched_sources_used,
            timestamp=_ist_timestamp_str(),
            concentration_warning=concentration_warning,
            bulk_deals=bulk_deals,
        )

    obj.setdefault("status", "success")
    obj.setdefault("options", None)

    obj["timestamp"] = _ist_timestamp_str()
    obj["sources_used"] = fetched_sources_used
    obj["concentration_warning"] = concentration_warning
    obj["bulk_deals"] = bulk_deals
    obj["budget_note"] = budget_note

    primary = tickers[0] if tickers else None

    if "rsi_value" not in obj:
      obj["rsi_value"] = (rsi_by_ticker.get(primary, {}) or {}).get("rsi_value") if primary else None

    if "rsi_explanation" not in obj or not obj.get("rsi_explanation"):
      obj["rsi_explanation"] = (
         (rsi_by_ticker.get(primary, {}) or {}).get("rsi_explanation")
         if primary else "RSI unavailable."
    )

    required_fields = ["answer"]
    missing = [k for k in required_fields if k not in obj]
    if missing:
        raise HTTPException(status_code=500, detail=f"Model JSON missing required fields: {missing}")


    # Fix bad Groq response types for portfolio summary
    if isinstance(obj.get("rsi_explanation"), dict):
       obj["rsi_explanation"] = "Mixed RSI signals across your portfolio holdings."

    if isinstance(obj.get("rsi_value"), dict):
       obj["rsi_value"] = ", ".join(
           [f"{k}: {v}" for k, v in obj["rsi_value"].items()]
    )
    if isinstance(obj.get("rsi_value"), (int, float)):
     obj["rsi_value"] = round(float(obj["rsi_value"]), 2)
    return ChatResponse(**obj)
