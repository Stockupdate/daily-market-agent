import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# ---------------- CONFIG ----------------
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "yourgmail@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your-app-password")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "receiver@gmail.com")

# Commodities to track
commodities = {
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Crude Oil": "CL=F",
    "Natural Gas": "NG=F",
    "Coal": "KOL"
}

# Example large-cap and mid-cap symbols (replace with NSE/BSE symbols)
large_caps = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
              "HINDUNILVR.NS", "SBIN.NS", "KOTAKBANK.NS", "LT.NS", "BHARTIARTL.NS"]

mid_caps = ["MUTHOOTFIN.NS", "MARUTI.NS", "PIIND.NS", "BALKRISIND.NS", "GICRE.NS"]

indices = {"SENSEX": "^BSESN", "NIFTY": "^NSEI"}

# ---------------- FUNCTIONS ----------------
def get_weekly_change(symbol):
    try:
        today = datetime.today()
        last_week = today - timedelta(days=7)
        data = yf.download(symbol, start=last_week.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"), progress=False)
        if len(data) < 2:
            return 0
        first = data['Close'].iloc[0]
        last = data['Close'].iloc[-1]
        # Ensure we return a float, not a Series
        return round(float((last - first) / first * 100), 2)
    except Exception as e:
        print(f"Error getting weekly change for {symbol}: {e}")
        return 0

def get_daily_top_gainers(symbols, top_n=5):
    perf = []
    for sym in symbols:
        try:
            data = yf.download(sym, period="2d", progress=False)
            if len(data) < 2:
                continue
            close_last = data['Close'].iloc[-1]
            close_prev = data['Close'].iloc[-2]
            pct_change = float((close_last - close_prev) / close_prev * 100)
            perf.append((sym, round(pct_change, 2)))
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            continue
    perf.sort(key=lambda x: x[1], reverse=True)
    return perf[:top_n]

def get_daily_bottom_performers(symbols, bottom_n=5):
    perf = []
    for sym in symbols:
        try:
            data = yf.download(sym, period="2d", progress=False)
            if len(data) < 2:
                continue
            close_last = data['Close'].iloc[-1]
            close_prev = data['Close'].iloc[-2]
            pct_change = float((close_last - close_prev) / close_prev * 100)
            perf.append((sym, round(pct_change, 2)))
        except Exception as e:
            print(f"Error processing {sym}: {e}")
            continue
    perf.sort(key=lambda x: x[1])
    return perf[:bottom_n]

def get_index_weekly_changes(symbol):
    try:
        today = datetime.today()
        data = yf.download(symbol, period="10d", progress=False)
        changes = []
        for i in range(0, len(data)-5):
            last_week_close = data['Close'].iloc[i]
            this_week_close = data['Close'].iloc[i+5]
            day = data.index[i].strftime("%A")
            pct_change = round(float((this_week_close - last_week_close)/last_week_close*100), 2)
            changes.append((day, pct_change))
        return changes, data
    except Exception as e:
        print(f"Error getting index changes for {symbol}: {e}")
        return [], pd.DataFrame()

def plot_chart(data_dict, title):
    plt.figure(figsize=(10,5))
    for name, series in data_dict.items():
        plt.plot(series.index, series.values, label=name)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Price/Value")
    plt.legend()
    plt.grid(True)
    # Save to base64 string for embedding
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# ---------------- PROCESS COMMODITIES ----------------
print("Processing commodities...")
commodity_perf = []
commodity_charts = {}
for name, sym in commodities.items():
    print(f"Fetching {name}...")
    change = get_weekly_change(sym)
    commodity_perf.append((name, change))
    try:
        data = yf.download(sym, period="8d", progress=False)['Close']
        commodity_charts[name] = data
    except Exception as e:
        print(f"Error getting chart data for {name}: {e}")

# Sort by change value (which is now guaranteed to be a float)
commodity_perf.sort(key=lambda x: x[1], reverse=True)
top_5_commodities = commodity_perf[:5]

# ---------------- PROCESS STOCKS ----------------
print("Processing stocks...")
top_10_large = get_daily_top_gainers(large_caps, top_n=10)
top_5_mid = get_daily_top_gainers(mid_caps, top_n=5)
bottom_5_stocks = get_daily_bottom_performers(large_caps + mid_caps, bottom_n=5)

# ---------------- PROCESS INDICES ----------------
print("Processing indices...")
index_changes = {}
index_charts_data = {}
for idx_name, idx_sym in indices.items():
    print(f"Fetching {idx_name}...")
    changes, data = get_index_weekly_changes(idx_sym)
    index_changes[idx_name] = changes
    if not data.empty:
        index_charts_data[idx_name] = data['Close']

# Generate charts
print("Generating charts...")
commodity_chart_img = plot_chart(commodity_charts, "Top 5 Commodities")
index_chart_img = plot_chart(index_charts_data, "SENSEX & NIFTY Last Week Prices")

# ---------------- CREATE HTML REPORT ----------------
print("Creating HTML report...")
html_content = "<h2>📊 Weekly Market & Commodity Report</h2>"

# Commodities Table
html_content += "<h3>Top 5 Commodity Performers (Week-over-Week)</h3>"
html_content += "<table border='1' cellpadding='5'><tr><th>Commodity</th><th>Week % Change</th></tr>"
for name, change in top_5_commodities:
    html_content += f"<tr><td>{name}</td><td>{change}%</td></tr>"
html_content += "</table><br>"
html_content += f"<img src='data:image/png;base64,{commodity_chart_img}' width='700'><br>"

# Large Cap
html_content += "<h3>Top 10 Large Cap Performers (Daily)</h3>"
html_content += "<table border='1' cellpadding='5'><tr><th>Symbol</th><th>% Change</th></tr>"
for sym, change in top_10_large:
    html_content += f"<tr><td>{sym}</td><td>{change}%</td></tr>"
html_content += "</table><br>"

# Mid Cap
html_content += "<h3>Top 5 Mid Cap Performers (Daily)</h3>"
html_content += "<table border='1' cellpadding='5'><tr><th>Symbol</th><th>% Change</th></tr>"
for sym, change in top_5_mid:
    html_content += f"<tr><td>{sym}</td><td>{change}%</td></tr>"
html_content += "</table><br>"

# Bottom 5
html_content += "<h3>Bottom 5 Performers (Daily)</h3>"
html_content += "<table border='1' cellpadding='5'><tr><th>Symbol</th><th>% Change</th></tr>"
for sym, change in bottom_5_stocks:
    html_content += f"<tr><td>{sym}</td><td>{change}%</td></tr>"
html_content += "</table><br>"

# Indices
html_content += "<h3>SENSEX & NIFTY Week-over-Week Daily Comparison</h3>"
for idx_name, changes in index_changes.items():
    html_content += f"<h4>{idx_name}</h4>"
    html_content += "<table border='1' cellpadding='5'><tr><th>Day</th><th>% Change</th></tr>"
    for day, change in changes:
        html_content += f"<tr><td>{day}</td><td>{change}%</td></tr>"
    html_content += "</table><br>"
html_content += f"<img src='data:image/png;base64,{index_chart_img}' width='700'><br>"

# ---------------- SEND EMAIL ----------------
print("Sending email...")
try:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "📊 Weekly Market & Commodity Report"
    msg.attach(MIMEText(html_content, "html"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✅ Email sent successfully!")
except Exception as e:
    print("❌ Failed to send email:", e)
    raise
