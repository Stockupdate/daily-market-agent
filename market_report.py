import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# ---------------- CONFIG ----------------
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL",    "yourgmail@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your-app-password")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL",  "receiver@gmail.com")

# ---------------- TRACKED INSTRUMENTS ----------------
COMMODITIES = {
    "Gold":        "GLD",
    "Silver":      "SLV",
    "Crude Oil":   "USO",
    "Natural Gas": "UNG",
    "Copper":      "CPER",
    "Aluminium":   "JJU",
    "Wheat":       "WEAT",
    "Soybean":     "SOYB",
}

INDICES = {
    "NIFTY 50": "^NSEI",
    "SENSEX":   "^BSESN",
    "NASDAQ":   "^IXIC",
}

MARKET_CAP_INDICES = {
    "NSE Large Cap (Nifty 50)":       {"symbol": "^NSEI",         "exchange": "NSE", "cap": "Large"},
    "NSE Mid Cap (Nifty Midcap 100)": {"symbol": "^CNXMIDCAP",    "exchange": "NSE", "cap": "Mid"},
    "NSE Small Cap (Nifty SC 100)":   {"symbol": "^CNXSC",        "exchange": "NSE", "cap": "Small"},
    "BSE Large Cap (Sensex 30)":      {"symbol": "^BSESN",        "exchange": "BSE", "cap": "Large"},
    "BSE Mid Cap":                    {"symbol": "BSE-MIDCAP.BO", "exchange": "BSE", "cap": "Mid"},
    "BSE Small Cap":                  {"symbol": "BSE-SMLCAP.BO", "exchange": "BSE", "cap": "Small"},
}

# ================================================================
#  SESSION DETECTION
#  open   = before 11:00 AM IST  → only prev close + open + gap
#  midday = 11:00 AM – 2:00 PM   → open + midday + open→mid
#  close  = after  2:00 PM IST   → full picture
# ================================================================
def get_session():
    ist  = timezone(timedelta(hours=5, minutes=30))
    now  = datetime.now(ist)
    hour = now.hour
    if hour < 11:
        return "open",   "🌅 Market Open Report"
    elif hour < 14:
        return "midday", "☀️ Mid-Day Report"
    else:
        return "close",  "🌆 End of Day Report"

# ================================================================
#  DATA FETCHING
# ================================================================
def fetch_intraday(symbol):
    """Return a dict with all price points. Caller decides what to show."""
    try:
        ticker = yf.Ticker(symbol)
        daily  = ticker.history(period="5d")
        if daily.empty or len(daily) < 2:
            return None

        prev_close    = float(daily['Close'].iloc[-2])
        current_price = float(daily['Close'].iloc[-1])
        day_change    = round((current_price - prev_close) / prev_close * 100, 2)

        intraday = ticker.history(period="1d", interval="5m")
        if intraday.empty or len(intraday) < 3:
            return {
                "current":      current_price,
                "prev_close":   prev_close,
                "open":         current_price,
                "midday":       None,
                "day_change":   day_change,
                "gap":          0.0,
                "open_to_mid":  None,
                "mid_to_close": None,
            }

        today_open = float(intraday['Open'].iloc[0])
        gap_pct    = round((today_open - prev_close) / prev_close * 100, 2) if prev_close else 0

        # Find midday price — 1:00 PM IST ≈ 07:30 UTC
        midday_price = None
        for ts, row in intraday.iterrows():
            h = ts.hour if hasattr(ts, 'hour') else 0
            if 7 <= h <= 8:
                midday_price = float(row['Close'])
                break
        if midday_price is None:
            mid_idx      = len(intraday) // 2
            midday_price = float(intraday['Close'].iloc[mid_idx])

        open_to_mid  = round((midday_price - today_open)    / today_open    * 100, 2) if today_open    else None
        mid_to_close = round((current_price - midday_price) / midday_price  * 100, 2) if midday_price  else None

        return {
            "current":      current_price,
            "prev_close":   prev_close,
            "open":         today_open,
            "midday":       midday_price,
            "day_change":   day_change,
            "gap":          gap_pct,
            "open_to_mid":  open_to_mid,
            "mid_to_close": mid_to_close,
        }

    except Exception as e:
        print(f"❌ {symbol}: {e}")
        return None


def fetch_history(symbol, period="1mo"):
    try:
        data = yf.Ticker(symbol).history(period=period)
        return data['Close'] if not data.empty else None
    except Exception as e:
        print(f"❌ history {symbol} ({period}): {e}")
        return None

# ================================================================
#  CHARTING
# ================================================================
def make_chart(series_1m, series_3m, title, currency_symbol="$"):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    fig.patch.set_facecolor('#f8f9fa')

    for ax, series, label in [(ax1, series_1m, "1 Month"), (ax2, series_3m, "3 Months")]:
        if series is not None and not series.empty:
            color = "#2ecc71" if float(series.iloc[-1]) >= float(series.iloc[0]) else "#e74c3c"
            ax.plot(series.index, series.values, color=color, linewidth=2)
            ax.fill_between(series.index, series.values, alpha=0.1, color=color)
            ax.set_title(label, fontsize=11, fontweight='bold', pad=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{currency_symbol}{x:,.0f}"))
            ax.grid(True, linestyle='--', alpha=0.4)
            ax.set_facecolor('white')
            ax.annotate(f"{currency_symbol}{float(series.iloc[0]):,.2f}",
                        xy=(series.index[0],  float(series.iloc[0])),  fontsize=8, color='#555', ha='left')
            ax.annotate(f"{currency_symbol}{float(series.iloc[-1]):,.2f}",
                        xy=(series.index[-1], float(series.iloc[-1])), fontsize=8, color=color,
                        fontweight='bold', ha='right')
        else:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label, fontsize=11)

    fig.suptitle(title, fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=130)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

# ================================================================
#  HTML HELPERS
# ================================================================
def cc(val):
    """CSS color class."""
    if val is None: return "neutral"
    return "positive" if val > 0 else "negative" if val < 0 else "neutral"

def fmt_pct(val):
    """Format a % value with sign, or '—' if unknown."""
    if val is None: return "<span style='color:#bbb'>—</span>"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"

def fmt_price(val, currency):
    if val is None: return "<span style='color:#bbb'>—</span>"
    return f"{currency}{val:,.2f}"

def cell(val, currency=None, is_pct=False):
    """Return a <td> string, coloured if it's a % change."""
    if is_pct:
        return f"<td class='{cc(val)}'>{fmt_pct(val)}</td>"
    return f"<td>{fmt_price(val, currency)}</td>"

# ── Session-aware table headers & row builders ──────────────────

def table_header(session):
    """Return the correct <thead> columns for this session."""
    base = "<table><tr><th>Name</th><th>Prev Close</th><th>Open</th><th>Gap %</th>"
    if session == "open":
        # At open: we know prev close, open price, and gap
        return base + "</tr>"
    elif session == "midday":
        # By midday: we also know midday price and open→midday move
        return base + "<th>Midday</th><th>Open → Midday %</th></tr>"
    else:
        # End of day: full picture
        return base + "<th>Midday</th><th>Close</th><th>1-Day %</th><th>Open → Midday %</th><th>Midday → Close %</th></tr>"


def build_row(label, symbol, d, session, currency="₹"):
    """Build a session-aware <tr> for one instrument."""
    if not d:
        cols = {"open": 3, "midday": 5, "close": 8}
        return f"<tr><td><strong>{label}</strong><br><small style='color:#888'>{symbol}</small></td>" + \
               "<td>—</td>" * cols.get(session, 3) + "</tr>"

    # Columns always shown
    row  = f"<tr>"
    row += f"<td><strong>{label}</strong><br><small style='color:#888'>{symbol}</small></td>"
    row += cell(d['prev_close'], currency)
    row += cell(d['open'],       currency)
    row += f"<td class='{cc(d['gap'])}'>{fmt_pct(d['gap'])}</td>"

    if session == "open":
        # Nothing more to show yet
        pass

    elif session == "midday":
        row += cell(d['midday'], currency)
        row += f"<td class='{cc(d['open_to_mid'])}'>{fmt_pct(d['open_to_mid'])}</td>"

    else:  # close
        row += cell(d['midday'],  currency)
        row += cell(d['current'], currency)
        row += f"<td class='{cc(d['day_change'])}'>{fmt_pct(d['day_change'])}</td>"
        row += f"<td class='{cc(d['open_to_mid'])}'>{fmt_pct(d['open_to_mid'])}</td>"
        row += f"<td class='{cc(d['mid_to_close'])}'>{fmt_pct(d['mid_to_close'])}</td>"

    row += "</tr>"
    return row


def cap_badge(cap):
    colors = {"Large": "#1565c0", "Mid": "#6a1b9a", "Small": "#e65100"}
    c = colors.get(cap, "#555")
    return f"<span style='background:{c};color:white;border-radius:3px;padding:1px 7px;font-size:11px'>{cap} Cap</span>"

def exchange_badge(exchange):
    colors = {"NSE": "#1b5e20", "BSE": "#b71c1c"}
    c = colors.get(exchange, "#333")
    return f"<span style='background:{c};color:white;border-radius:3px;padding:1px 7px;font-size:11px'>{exchange}</span>"


def build_cap_row(name, info, d, session):
    """Market cap index row — same session-aware logic, with exchange/cap badges."""
    sym  = info["symbol"]
    exch = info["exchange"]
    cap  = info["cap"]

    if not d:
        cols = {"open": 5, "midday": 7, "close": 10}
        return f"<tr><td><strong>{name}</strong></td><td>{exchange_badge(exch)}</td><td>{cap_badge(cap)}</td>" + \
               "<td>—</td>" * (cols.get(session, 5) - 2) + "</tr>"

    row  = f"<tr>"
    row += f"<td><strong>{name}</strong><br><small style='color:#888'>{sym}</small></td>"
    row += f"<td>{exchange_badge(exch)}</td>"
    row += f"<td>{cap_badge(cap)}</td>"
    row += cell(d['prev_close'], "₹")
    row += cell(d['open'],       "₹")
    row += f"<td class='{cc(d['gap'])}'>{fmt_pct(d['gap'])}</td>"

    if session == "midday":
        row += cell(d['midday'], "₹")
        row += f"<td class='{cc(d['open_to_mid'])}'>{fmt_pct(d['open_to_mid'])}</td>"
    elif session == "close":
        row += cell(d['midday'],  "₹")
        row += cell(d['current'], "₹")
        row += f"<td class='{cc(d['day_change'])}'>{fmt_pct(d['day_change'])}</td>"
        row += f"<td class='{cc(d['open_to_mid'])}'>{fmt_pct(d['open_to_mid'])}</td>"
        row += f"<td class='{cc(d['mid_to_close'])}'>{fmt_pct(d['mid_to_close'])}</td>"

    row += "</tr>"
    return row


def cap_table_header(session):
    base = "<table><tr><th>Index</th><th>Exchange</th><th>Segment</th><th>Prev Close</th><th>Open</th><th>Gap %</th>"
    if session == "open":
        return base + "</tr>"
    elif session == "midday":
        return base + "<th>Midday</th><th>Open → Midday %</th></tr>"
    else:
        return base + "<th>Midday</th><th>Close</th><th>1-Day %</th><th>Open → Midday %</th><th>Midday → Close %</th></tr>"


def session_note(session):
    notes = {
        "open":   "📌 Open report — showing previous close, today's open and gap only. Midday & close data not yet available.",
        "midday": "📌 Mid-day report — showing open to midday movement. End-of-day close data not yet available.",
        "close":  "📌 End of day report — full intraday breakdown available.",
    }
    colors = {"open": "#fff3e0", "midday": "#e3f2fd", "close": "#e8f5e9"}
    borders = {"open": "#ff9800", "midday": "#2196F3", "close": "#4CAF50"}
    return (f"<div style='background:{colors[session]};border-left:4px solid {borders[session]};"
            f"padding:10px 14px;border-radius:4px;font-size:12px;margin-bottom:16px;color:#333'>"
            f"{notes[session]}</div>")

# ================================================================
#  MAIN
# ================================================================
if __name__ == "__main__":

    ist             = timezone(timedelta(hours=5, minutes=30))
    now_ist         = datetime.now(ist)
    session, label  = get_session()

    print("\n" + "="*60)
    print(f"DAILY MARKET REPORT — {label}")
    print(f"Session : {session.upper()}")
    print(f"IST Time: {now_ist.strftime('%d %b %Y  %I:%M %p')}")
    print("="*60)

    # ── Fetch data ───────────────────────────────────────────────
    print("\n📦 Fetching index data...")
    index_data, index_charts = {}, {}
    for name, sym in INDICES.items():
        print(f"  {name} ({sym})...")
        index_data[name]   = fetch_intraday(sym)
        index_charts[name] = {"1m": fetch_history(sym, "1mo"), "3m": fetch_history(sym, "3mo")}

    print("\n📦 Fetching market cap index data...")
    cap_data = {}
    for name, info in MARKET_CAP_INDICES.items():
        print(f"  {name} ({info['symbol']})...")
        cap_data[name] = fetch_intraday(info["symbol"])

    print("\n📦 Fetching commodity data...")
    commodity_data, commodity_charts = {}, {}
    for name, sym in COMMODITIES.items():
        print(f"  {name} ({sym})...")
        commodity_data[name]   = fetch_intraday(sym)
        commodity_charts[name] = {"1m": fetch_history(sym, "1mo"), "3m": fetch_history(sym, "3mo")}

    # ── Build HTML ───────────────────────────────────────────────
    print("\n🖊️  Building HTML report...")

    def currency_for_index(name):
        return "₹" if name in ("NIFTY 50", "SENSEX") else "$"

    CSS = """
    <style>
        body      { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .wrap     { max-width: 1050px; margin: 0 auto; background: white;
                    padding: 30px; border-radius: 10px;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
        h3        { color: #444; border-left: 4px solid #4CAF50;
                    padding-left: 10px; margin-top: 36px; }
        h4        { color: #555; margin: 20px 0 6px 0; }
        table     { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 13px; }
        th        { background: #4CAF50; color: white; padding: 10px 12px; text-align: left; white-space:nowrap; }
        td        { padding: 9px 12px; border-bottom: 1px solid #eee; white-space:nowrap; }
        tr:nth-child(even) { background: #fafafa; }
        tr:hover  { background: #f0f7f0; }
        .positive { color: #27ae60; font-weight: bold; }
        .negative { color: #e74c3c; font-weight: bold; }
        .neutral  { color: #888; }
        .header-box { background: linear-gradient(135deg,#43a047,#1b5e20);
                      color: white; padding: 20px 24px; border-radius: 8px; margin-bottom: 24px; }
        .header-box h2 { color: white; margin: 0 0 4px 0; font-size: 22px; }
        .header-box p  { margin: 0; opacity: .85; font-size: 13px; }
        img  { max-width: 100%; border-radius: 8px; margin: 10px 0 20px 0; }
        .sn  { font-size: 12px; color: #888; margin: -6px 0 10px 0; }
        .footer { margin-top: 30px; padding-top: 16px; border-top: 1px solid #ddd;
                  color: #aaa; font-size: 11px; text-align: center; }
    </style>"""

    html = f"""<html><head>{CSS}</head><body><div class="wrap">
    <div class="header-box">
        <h2>📊 {label}</h2>
        <p>{now_ist.strftime('%A, %d %B %Y  —  %I:%M %p IST')}</p>
    </div>
    {session_note(session)}
    """

    # ── 1. MAIN INDICES ──────────────────────────────────────────
    html += "<h3>🌐 Market Indices — NIFTY · SENSEX · NASDAQ</h3>"
    html += f'<p class="sn">Intraday breakdown varies by session — {session} view</p>'
    html += table_header(session)
    for name, sym in INDICES.items():
        html += build_row(name, sym, index_data.get(name), session, currency=currency_for_index(name))
    html += "</table>"

    # Index charts (always shown regardless of session)
    for name, sym in INDICES.items():
        cdata = index_charts.get(name, {})
        img   = make_chart(cdata.get("1m"), cdata.get("3m"), name, currency_symbol=currency_for_index(name))
        html += f'<h4>{name} — 1 Month &amp; 3 Month Price History</h4>'
        html += f'<img src="data:image/png;base64,{img}" alt="{name} chart">'

    # ── 2. MARKET CAP INDICES ────────────────────────────────────
    html += "<h3>📊 NSE &amp; BSE — Large · Mid · Small Cap</h3>"
    html += f'<p class="sn">Overall segment performance — {session} view</p>'
    html += cap_table_header(session)
    for name, info in MARKET_CAP_INDICES.items():
        html += build_cap_row(name, info, cap_data.get(name), session)
    html += "</table>"

    # ── 3. COMMODITIES ───────────────────────────────────────────
    html += "<h3>🏅 Commodities</h3>"
    html += f'<p class="sn">ETF prices in USD — {session} view. Gap = prev close → today\'s open.</p>'
    html += table_header(session)
    for name, sym in COMMODITIES.items():
        html += build_row(name, sym, commodity_data.get(name), session, currency="$")
    html += "</table>"

    # Commodity charts
    for name, sym in COMMODITIES.items():
        cdata = commodity_charts.get(name, {})
        img   = make_chart(cdata.get("1m"), cdata.get("3m"), name, currency_symbol="$")
        html += f'<h4>{name} ({sym}) — 1 Month &amp; 3 Month Price History</h4>'
        html += f'<img src="data:image/png;base64,{img}" alt="{name} chart">'

    html += """
    <div class="footer">
        ⚠️ Data sourced from Yahoo Finance — may be delayed 15–20 minutes.
        For informational purposes only. Not financial advice.
    </div>
    </div></body></html>"""

    # ── SEND EMAIL ───────────────────────────────────────────────
    print("\n📧 Sending email...")
    try:
        msg            = MIMEMultipart()
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = RECEIVER_EMAIL
        msg["Subject"] = f"{label} — {now_ist.strftime('%d %b %Y  %I:%M %p IST')}"
        msg.attach(MIMEText(html, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent → {RECEIVER_EMAIL}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise

    print("\n" + "="*60)
    print("✅ Report Complete")
    print("="*60)
