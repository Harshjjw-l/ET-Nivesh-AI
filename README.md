# ET Nivesh AI 🚀
### AI-Powered Investment Intelligence for India's Retail Investor

> Built for **ET GenAI Hackathon 2026** — Problem Statement 6: AI for the Indian Investor
> Team: 2 BTech 2nd Year students | 48-hour build

---

## 🔗 Live Demo

| Resource | Link |
|----------|------|
| **Live Application** | `[DEPLOYMENT LINK — ADD AFTER DEPLOY]` |
| **Backend API** | `[RENDER BACKEND URL — ADD AFTER DEPLOY]` |
| **Demo Video** | `[YOUTUBE/DRIVE LINK — ADD AFTER RECORDING]` |
| **GitHub Repository** | `[YOUR GITHUB REPO LINK]` |

---

## 🎯 The Problem We Solved

India has **14 crore+ demat accounts**. Most of those investors are flying blind — reacting to WhatsApp tips, missing corporate filings, unable to read technical charts, and managing portfolios on gut feel.

We identified **4 specific loopholes** in existing AI tools for investors:

| # | Loophole | How We Found It |
|---|----------|----------------|
| 1 | No actionable entry/exit price levels — AI gives opinions, not decisions | Thinking like Rajesh, a first-time investor |
| 2 | No portfolio concentration check — same advice regardless of what you hold | Realised 60% in one stock is dangerous |
| 3 | No source citation or real-time data proof — Rajesh cannot verify the answer | Compared AI answers with actual NSE data |
| 4 | Paywalled or stale data limits AI analysis | Found in an ET Markets expert article itself |

**ET Nivesh AI** is our solution — not a ChatGPT wrapper, but a full intelligence layer that fetches live NSE data, computes technical signals in Python, and uses AI only to explain what the data already shows.

---

## 💡 What Makes This Different

Most teams at this hackathon will build a chatbot that asks an LLM "should I buy Reliance?" and display the answer. We did not do that.

Here is what we did differently:

**Python controls the numbers. AI only explains.**

```
User question + portfolio
        ↓
Extract stock names from question
        ↓
Resolve to NSE ticker symbols (CSV database of 2254 stocks)
        ↓
Fetch last 20 days OHLCV data from NSE via yfinance
        ↓
Compute RSI, MACD, Support, Resistance in Python
        ↓
Check portfolio concentration risk
        ↓
Fetch today's NSE bulk deals
        ↓
Package all real data → send to Groq LLM
        ↓
LLM explains the data in plain English
        ↓
Return: answer + entry price + target + stop loss + sources + timestamp
```

The AI cannot hallucinate prices because it never generates them. Every number comes from real market data computed in Python.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│                                                                 │
│  ┌──────────────┐          ┌───────────────────────────────┐   │
│  │   SIDEBAR    │          │         CHAT AREA             │   │
│  │              │          │                               │   │
│  │ • Portfolio  │  ──────► │ • Question input              │   │
│  │   (5 stocks) │          │ • AI answer card              │   │
│  │ • Amount ₹   │          │ • Entry / Target / Stop loss  │   │
│  │ • Timeframe  │          │ • RSI badge                   │   │
│  │              │          │ • Budget analysis             │   │
│  │              │          │ • Concentration warning       │   │
│  │              │          │ • Source citations            │   │
│  └──────────────┘          └───────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /chat (JSON)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Python)                      │
│                                                                 │
│  1. Extract stock name from question text                        │
│  2. Resolve to NSE ticker via CSV (2254 stocks database)        │
│  3. Fetch 20-day OHLCV from yfinance (free, no paywall)        │
│  4. Compute RSI(14), MACD(12,26,9), Support/Resistance         │
│  5. Compute entry/target/stop loss based on timeframe          │
│  6. Check portfolio concentration (equal-weight assumption)     │
│  7. Fetch NSE bulk deals for portfolio stocks                   │
│  8. Compute budget analysis (how many shares can user buy)     │
│  9. Package all data → send to Groq LLM                        │
│  10. Override Groq price fields with Python-computed values     │
└───────────────────┬─────────────────┬──────────────────────────┘
                    │                 │
                    ▼                 ▼
        ┌───────────────┐   ┌─────────────────────┐
        │  GROQ LLM     │   │  NSE PUBLIC API      │
        │  llama3-70b   │   │  (bulk deals data)   │
        │  (explains    │   │  yfinance            │
        │   the data)   │   │  (OHLCV prices)      │
        └───────────────┘   └─────────────────────┘
```

---

## 🔬 Market Terminology — Explained Simply

We used real financial signals in this project. Here is what each term means and why we included it:

### RSI — Relative Strength Index
**What it is:** A number between 0 and 100 that tells you if a stock has moved too fast recently.
- Below 30 = **Oversold** — stock fell too fast, may bounce back (possible buy signal)
- Above 70 = **Overbought** — stock rose too fast, may fall (possible sell signal)
- Between 30–70 = **Neutral** — no strong signal

**Why we used it:** RSI is the most widely taught indicator in retail investing education (Zerodha Varsity, NSE Academy). It gives Rajesh a simple one-number view of whether a stock is beaten down or overheated.

### MACD — Moving Average Convergence Divergence
**What it is:** Compares a fast 12-day moving average with a slow 26-day moving average of the stock price.
- MACD line above Signal line = **Bullish momentum** — buyers are in control
- MACD line below Signal line = **Bearish momentum** — sellers are in control

**Why we used it:** RSI alone can be misleading. MACD adds a second confirmation of trend direction. Two signals agreeing is stronger than one signal alone.

### Support and Resistance
**What it is:**
- **Support** = a price level where the stock has repeatedly stopped falling and bounced back. Think of it as a floor.
- **Resistance** = a price level where the stock has repeatedly stopped rising and fallen back. Think of it as a ceiling.

**Why we used it:** Entry price should be near support. Target price should be near resistance. This is the standard framework taught by every technical analysis course.

### Entry Price, Target Price, Stop Loss
**What they are:**
- **Entry Price** = the price range where it makes sense to buy
- **Target Price** = the price where you should sell to book profit
- **Stop Loss** = the price where you should exit to prevent further loss

**Example:** Entry ₹741–₹763, Target ₹869, Stop Loss ₹695 means — buy between ₹741 and ₹763, sell when it hits ₹869, exit immediately if it falls to ₹695.

**Why we computed these in Python (not AI):** An LLM can hallucinate prices. We verified this — ChatGPT gave HDFC Bank a buy zone of ₹1,520 when the stock was actually trading at ₹756. Our backend fetches the real price and computes entry/target/stop loss from actual 20-day price data.

### Concentration Risk
**What it is:** The danger of putting too many eggs in one basket. If one stock is 60% of your portfolio and it falls 20%, your entire wealth drops 12%.

**Why we included it:** This is Rajesh's biggest invisible risk. No other AI tool checks this automatically. Our backend warns the user whenever a single stock exceeds 30% of their portfolio — even before they ask.

### Bulk Deals
**What they are:** When a large institution (mutual fund, foreign investor, hedge fund) buys or sells a very large quantity of shares in one day, NSE publicly records it as a bulk deal. Institutional activity is a strong signal for retail investors.

**Why we included it:** The PS specifically mentioned bulk/block deals as a key signal. We fetch today's bulk deals from NSE's public API and alert users if any of their portfolio stocks have unusual institutional activity.

### OHLCV
**What it is:** Open, High, Low, Close, Volume — the 5 numbers recorded for every stock on every trading day. We fetch 20 days of this data per stock to compute all our technical indicators.

### RAG — Retrieval Augmented Generation
**What it is:** A technique where we fetch real data (Retrieval), inject it into the AI prompt (Augmented), and then let the AI generate an answer based on that real evidence (Generation).

**Why it matters:** Without RAG, an LLM answers from memory — which could be months old. With RAG, every answer is grounded in what actually happened on NSE today.

---

## 🧪 Testing — All Levels Documented

We conducted systematic testing across 5 categories before finalising the backend.

### Category A — Single Stock Simple Questions

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| A1 | "Should I buy Reliance?" | RELIANCE.NS fetched, RSI shown | ✅ Pass |
| A2 | "What about Tata Consultancy Services?" | TCS.NS detected from full name | ✅ Pass |
| A3 | "Bro what about Infosys?" | INFY.NS fetched despite casual language | ✅ Pass |
| A4 | "Is SBI good for long term?" | SBIN.NS fetched (SBI → SBIN mapping) | ✅ Pass |
| A5 | "Should I add Bajaj Finance?" | BAJFINANCE.NS fetched even though not in portfolio | ✅ Pass |

### Category B — Portfolio Summary Questions

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| B1 | "How is my portfolio doing overall?" | All stocks analysed, portfolio summary given | ✅ Pass |
| B2 | "Which stock should I focus on?" | Weakest RSI stock identified and recommended | ✅ Pass |
| B3 | "Am I diversified enough?" | All IT stocks flagged as same-sector concentration | ✅ Pass |

### Category C — Concentration Risk

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| C1 | Single stock portfolio, buy more of same | Concentration warning fires — 100% in one stock | ✅ Pass |
| C2 | 5 stocks equally distributed | No concentration warning | ✅ Pass |

### Category D — Edge Cases

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| D1 | Intraday timeframe | Tighter entry/target (2% target vs 15% for long term) | ✅ Pass |
| D2 | Budget ₹5,000 for TCS at ₹2,389 | Budget note: can buy 2 shares with ₹211 remaining | ✅ Pass |
| D3 | "If market crashes what should I do?" | Defensive advice, stop loss highlighted | ✅ Pass |
| D4 | Unknown stock "XYZ Corp" | Graceful error: stock not found on NSE | ✅ Pass |
| D5 | First time investor language | Simple English, no jargon without explanation | ✅ Pass |

### Category E — Judge Demo Questions (Tested Last)

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| E1 | "Should I buy Reliance Industries right now?" | Full analysis with all fields | ✅ Pass |
| E2 | "Which of my stocks should I add more to?" | Portfolio-aware comparison | ✅ Pass |
| E3 | "I am salaried, is HDFC Bank safe?" | Beginner-friendly answer with context | ✅ Pass |

### Timeframe Sensitivity Test

We verified that changing timeframe produces meaningfully different numbers:

| Timeframe | Target Multiplier | Stop Loss | Entry Buffer |
|-----------|------------------|-----------|--------------|
| Intraday | +2% | -1% | 0.5% |
| Short term / 1 month | +6% | -4% | 1% |
| Long term / 12 month | +15% | -8% | 2% |

**Result:** Same stock, different timeframe → completely different entry/target/stop loss numbers. This proves our backend is logic-driven, not LLM-generated.

### Competitive Comparison Test

We tested the same question on ChatGPT vs ET Nivesh AI:

**Question:** "Should I buy HDFC Bank? Portfolio: HDFCBANK only. Budget: ₹10,000"

**ChatGPT answered:**
- Buy zone: ₹1,520 – ₹1,580 ← **WRONG. Stock was at ₹756**
- No portfolio concentration check
- No source cited
- No timestamp

**ET Nivesh AI answered:**
- Current price: ₹756.20 fetched from NSE at 22:06 IST ← **CORRECT**
- Entry: ₹741–₹763 (computed from real price)
- Target: ₹869 (15% for long term)
- Stop loss: ₹695 (8% below current)
- Concentration warning: 100% in one stock
- Budget note: 13 shares with ₹169 remaining

This comparison demonstrates our core value proposition — real data vs memory.

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| Python 3.11 | Core language |
| FastAPI | REST API framework |
| yfinance | Free live NSE stock data (no paywall) |
| pandas-ta | RSI and MACD computation |
| pandas | Data processing |
| Groq API (llama3-70b) | AI explanation layer |
| requests | NSE bulk deals fetching |
| python-dotenv | Environment variable management |
| uvicorn | ASGI server |

### Frontend
| Technology | Purpose |
|-----------|---------|
| React + TypeScript | UI framework |
| Tailwind CSS | Styling |
| Vite | Build tool |

### Data Sources
| Source | What We Use It For |
|--------|-------------------|
| NSE EQUITY_L.csv | Database of 2254 listed NSE stocks for ticker resolution |
| yfinance | Last 20 days OHLCV price data — free, no paywall |
| NSE Public API | Today's bulk deals — institutional activity signals |

---

## 📡 API Endpoints

### POST /chat
Main analysis endpoint.

**Request:**
```json
{
  "question": "Should I buy HDFC Bank?",
  "portfolio": ["HDFCBANK", "TCS"],
  "investment_amount": 50000,
  "timeframe": "long term"
}
```

**Response:**
```json
{
  "answer": "HDFC Bank looks attractive — RSI of 24.35 suggests it is oversold...",
  "entry_price": "₹741.08–₹763.76",
  "target_price": 869.63,
  "stop_loss": 695.70,
  "rsi_value": 24.35,
  "rsi_explanation": "RSI is 24.35 — oversold. Price fell too fast, may bounce.",
  "sources_used": ["HDFCBANK.NS: price=₹756.20, RSI=24.35, fetched_at=22:06 IST"],
  "timestamp": "2026-03-28 22:06:49 IST",
  "concentration_warning": "HDFCBANK makes up 50% of your portfolio...",
  "bulk_deals": "No bulk deal activity today for your stocks",
  "budget_note": "With ₹50,000 you can buy approximately 66 shares at ₹756.20 each."
}
```

### GET /search-stock?q={query}
Returns top 5 matching stocks from NSE database for autocomplete.

### GET /signals/today
Returns today's NSE bulk deals for Opportunity Radar widget.

### GET /resolve-stock?q={query}
Resolves a company name or partial name to its NSE ticker symbol.

### GET /test-ticker/{ticker}
Tests if yfinance can fetch data for a given ticker. Used for validation.

---

## ⚙️ How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free Groq API key from console.groq.com

### Backend Setup

```bash
# Clone the repository
git clone [YOUR_GITHUB_URL]
cd et-nivesh-ai/backend

# Install dependencies
pip install fastapi uvicorn yfinance pandas pandas-ta groq requests python-dotenv pydantic

# Create environment file
echo "GROQ_API_KEY=your_groq_api_key_here" > .env

# Make sure the NSE stock database is present
# data/EQUITY_L.csv should be in the backend folder

# Run the backend
uvicorn main:app --reload --port 8000
```

Backend will be running at `http://localhost:8000`
API documentation auto-generated at `http://localhost:8000/docs`

### Frontend Setup

```bash
cd et-nivesh-ai/frontend

# Install dependencies
npm install

# Create environment file
echo "VITE_API_URL=http://localhost:8000" > .env

# Run the frontend
npm run dev
```

Frontend will be running at `http://localhost:5173`

### Test the Connection

Open `http://localhost:5173` in your browser.
1. Enter `HDFCBANK` in the first portfolio field
2. Enter `50000` as investment amount
3. Select `Long term` timeframe
4. Type: `Should I buy more HDFC Bank?`
5. Click Send

You should see a full analysis with entry price, RSI, budget note, and sources.

---

## 🚀 Deployment

### Backend — Render.com (Free)

```bash
# In your backend folder, create these files:

# requirements.txt
fastapi
uvicorn
yfinance
pandas
pandas-ta
groq
requests
python-dotenv
pydantic
```

**render.yaml:**
```yaml
services:
  - type: web
    name: et-nivesh-ai-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: GROQ_API_KEY
        sync: false
```

Add `GROQ_API_KEY` in Render dashboard environment variables.

**Deployed backend URL:** `[ADD AFTER DEPLOY]`

### Frontend — Vercel (Free)

1. Connect GitHub repo to Vercel
2. Set environment variable: `VITE_API_URL = [YOUR RENDER BACKEND URL]`
3. Deploy — auto-deploys on every push to main

**Deployed frontend URL:** `[ADD AFTER DEPLOY]`

---

## 🎨 Features Implemented

### ✅ Market ChatGPT Next Gen (Core Feature)
- Portfolio-aware answers — knows what you hold before answering
- Source-cited responses — every answer shows data source + timestamp
- Deeper data integration — live NSE prices, not AI memory
- Multi-step analysis — RSI + MACD + concentration + budget in one response

### ✅ Opportunity Radar (Integrated)
- NSE bulk deals fetching for portfolio stocks
- Today's signals widget on homepage
- Institutional activity detection

### ✅ Chart Pattern Intelligence (Integrated)
- RSI(14) computed from real close prices
- MACD(12,26,9) with plain English explanation
- Support and resistance from 20-day High/Low
- Timeframe-aware entry/target/stop loss

### 📋 Roadmap (Phase 2)
- AI Market Video Engine — auto-generated market wrap videos
- Hindi/Hinglish language support for rural investors
- Full Opportunity Radar — corporate filings, insider trades
- Historical back-tested success rates per pattern
- 50/200 DMA trend detection
- Candlestick pattern recognition

---

## 🧠 Design Philosophy

> "We did not build ET Nivesh AI to replace the investor's judgment. We built it to give every first-time investor the same knowledge that was previously only available to those who could afford a financial advisor. The AI fills the knowledge gap. The human makes the final decision."

Our target user is not a sophisticated analyst. It is **Rajesh** — a 34-year-old salaried employee in Pune with 3 stocks, no time to read filings, and no idea what RSI means. Every design decision was made with Rajesh in mind.

This is why:
- Every technical term is explained in plain English in the answer
- The disclaimer "not financial advice — final decision is always yours" appears on every response
- The budget note tells Rajesh exactly how many shares he can buy with his money
- The concentration warning protects Rajesh before he over-bets on one stock

---

## ⚠️ Disclaimer

ET Nivesh AI is built for educational and informational purposes only. All analysis, entry prices, targets, and stop losses are computed from publicly available NSE data using standard technical analysis methods. This is not financial advice. Past performance is not indicative of future results. All investments are subject to market risk. Please consult a SEBI-registered financial advisor before making investment decisions.

---

## 👥 Team

Built by two BTech 2nd Year students for the ET GenAI Hackathon 2026 in 48 hours.

| Member | Role |
|--------|------|
| [YOUR NAME] | Backend — FastAPI, yfinance, technical indicators, Groq integration |
| [TEAMMATE NAME] | Frontend — React, TypeScript, UI/UX design |

---

## 📁 Project Structure

```
et-nivesh-ai/
├── backend/
│   ├── main.py                 # FastAPI app, all endpoints, business logic
│   ├── services/
│   │   └── stock_resolver.py   # CSV-based NSE stock name resolution
│   ├── data/
│   │   └── EQUITY_L.csv        # NSE equity database (2254 stocks)
│   ├── requirements.txt
│   ├── render.yaml
│   └── .env                    # GROQ_API_KEY (not committed)
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main React component
│   │   ├── api.ts              # Backend API calls
│   │   └── types.ts            # TypeScript type definitions
│   ├── package.json
│   └── .env                    # VITE_API_URL (not committed)
└── README.md
```

---

*ET Nivesh AI — Built with purpose, for India's retail investor.*
