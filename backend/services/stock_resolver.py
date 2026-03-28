import pandas as pd
import re
from typing import List, Dict, Optional

# Global dataframe (loaded once at startup)
stock_df = None


# -------------------------------
# Utility: normalize text
# -------------------------------
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)  # remove extra spaces
    return text


# -------------------------------
# Load CSV once at startup
# -------------------------------
def load_stock_data(csv_path: str = "data/EQUITY_L.csv"):
    global stock_df

    df = pd.read_csv(csv_path)

    # Keep only required columns
    df = df[["SYMBOL", "NAME OF COMPANY"]].copy()

    # Clean data
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip()
    df["NAME OF COMPANY"] = df["NAME OF COMPANY"].astype(str).str.strip()

    # Normalized columns for matching
    df["symbol_norm"] = df["SYMBOL"].apply(normalize_text)
    df["company_norm"] = df["NAME OF COMPANY"].apply(normalize_text)

    stock_df = df
    print(f"[stock_resolver] Loaded {len(stock_df)} stocks from {csv_path}")


# -------------------------------
# Resolve stock input to Yahoo ticker
# -------------------------------

def resolve_stock(user_input: str) -> Dict:
    global stock_df

    if stock_df is None:
        raise RuntimeError("Stock data not loaded. Call load_stock_data() at startup.")

    query = normalize_text(user_input)

    print(f"[resolve_stock] User input: {user_input}")
    print(f"[resolve_stock] Normalized query: {query}")

    if not query:
        return {
            "status": "error",
            "message": "Empty stock input"
        }

    # 1) Exact SYMBOL match
    exact_match = stock_df[stock_df["symbol_norm"] == query]

    if not exact_match.empty:
        row = exact_match.iloc[0]
        print(f"[resolve_stock] Exact symbol match found: {row['SYMBOL']}")
        return {
            "status": "success",
            "symbol": row["SYMBOL"],
            "company_name": row["NAME OF COMPANY"],
            "ticker": f"{row['SYMBOL']}.NS"
        }
        # 1.5) Symbol starts-with check — ADD THIS BLOCK
    startswith_symbol = stock_df[stock_df["symbol_norm"].str.startswith(query)]
    if not startswith_symbol.empty:
         row = startswith_symbol.iloc[0]
         return {
          "status": "success",
          "symbol": row["SYMBOL"],
          "company_name": row["NAME OF COMPANY"],
          "ticker": f"{row['SYMBOL']}.NS"
     }

# 1.6) Company name starts-with — ADD THIS BLOCK  
    startswith_company = stock_df[stock_df["company_norm"].str.startswith(query)]
    if not startswith_company.empty:
        row = startswith_company.iloc[0]
        return {
        "status": "success",
        "symbol": row["SYMBOL"],
        "company_name": row["NAME OF COMPANY"],
        "ticker": f"{row['SYMBOL']}.NS"
    }

    # 2) Partial company name match
    query_words = query.split()

    def company_match_score(company_name: str) -> int:
        score = 0
        for word in query_words:
            if word in company_name:
                score += 1
        return score

    temp_df = stock_df.copy()
    temp_df["match_score"] = temp_df["company_norm"].apply(company_match_score)

    partial_matches = temp_df[temp_df["match_score"] > 0].sort_values(
        by="match_score", ascending=False
    )

    if not partial_matches.empty:
        row = partial_matches.iloc[0]
        print(f"[resolve_stock] Partial company match found: {row['SYMBOL']}")
        return {
            "status": "success",
            "symbol": row["SYMBOL"],
            "company_name": row["NAME OF COMPANY"],
            "ticker": f"{row['SYMBOL']}.NS"
        }

    # 3) No match found
    print("[resolve_stock] No stock match found")
    return {
        "status": "error",
        "message": "Stock not found in NSE equity list — please use exact NSE symbol"
    }

# -------------------------------
# Search top 3 matches for frontend autocomplete
# -------------------------------
def search_stocks(query: str, limit: int = 5) -> List[Dict]:
    """
    Smart stock search for frontend suggestions.
    Supports:
    - exact symbol match
    - exact company name match
    - startswith symbol/company
    - partial company/symbol search

    Example input:
        "adani"
        "tata"
        "sbi"
        "reliance"

    Example output:
    [
        {"symbol": "ADANIENT", "company_name": "Adani Enterprises Limited", "ticker": "ADANIENT.NS"},
        ...
    ]
    """

    global stock_df

    if stock_df is None:
        raise RuntimeError("Stock data not loaded. Call load_stock_data() at startup.")

    query_norm = normalize_text(query)

    if not query_norm:
        return []

    query_words = query_norm.split()

    def search_score(row) -> int:
        score = 0
        symbol = row["symbol_norm"]
        company = row["company_norm"]

        # 1) Exact symbol match
        if query_norm == symbol:
            score += 100

        # 2) Exact company match
        if query_norm == company:
            score += 90

        # 3) Symbol startswith
        if symbol.startswith(query_norm):
            score += 70

        # 4) Company startswith
        if company.startswith(query_norm):
            score += 60

        # 5) Symbol contains
        if query_norm in symbol:
            score += 50

        # 6) Company contains
        if query_norm in company:
            score += 40

        # 7) Per-word company matches
        for word in query_words:
            if word in company:
                score += 10

        # 8) Per-word symbol matches
        for word in query_words:
            if word in symbol:
                score += 15

        return score

    temp_df = stock_df.copy()
    temp_df["search_score"] = temp_df.apply(search_score, axis=1)

    results = (
        temp_df[temp_df["search_score"] > 0]
        .sort_values(by="search_score", ascending=False)
        .head(limit)
    )

    output = []
    for _, row in results.iterrows():
        output.append({
            "symbol": row["SYMBOL"],
            "company_name": row["NAME OF COMPANY"],
            "ticker": f"{row['SYMBOL']}.NS"
        })

    return output
def resolve_portfolio_stocks(portfolio_list):
    resolved = []
    errors = []

    for stock in portfolio_list:
        result = resolve_stock(stock)

        if result["status"] == "success":
            resolved.append(result["ticker"])
        else:
            errors.append({
                "input": stock,
                "error": result["message"]
            })

    return {
        "resolved_tickers": list(set(resolved)),
        "errors": errors
    }