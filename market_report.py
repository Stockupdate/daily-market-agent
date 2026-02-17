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
import numpy as np

# ---------------- CONFIG ----------------
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "yourgmail@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your-app-password")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "receiver@gmail.com")

# Commodities to track - using ETFs for more reliable data
commodities = {
    "Gold": "GLD",           # Gold ETF
    "Silver": "SLV",         # Silver ETF
    "Crude Oil": "USO",      # Oil ETF
    "Natural Gas": "UNG",    # Natural Gas ETF
    "Copper": "CPER"         # Copper ETF (replacing Coal)
}

# Example large-cap and mid-cap symbols
large_caps = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
              "HINDUNILVR.NS", "SBIN.NS", "KOTAKBANK.NS", "LT.NS", "BHARTIARTL.NS"]

mid_caps = ["MUTHOOTFIN.NS", "MARUTI.NS", "PIIND.NS", "BALKRISIND.NS", "GICRE.NS"]

indices = {"SENSEX": "^BSESN", "NIFTY": "^NSEI"}

# ---------------- HELPER FUNCTION ----------------
def safe_float(value):
    """Safely convert pandas Series, numpy array, or scalar to float"""
    if isinstance(value, (pd.Series, np.ndarray)):
        return float(value.iloc[0] if hasattr(value, 'iloc') else value[0])
    return float(value)

# ---------------- FUNCTIONS ----------------
def get_weekly_change(symbol):
    try:
        # Get more days to ensure we have enough data
        end_date = datetime.today()
        start_date = end_date - timedelta(days=10)
        
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if data.empty or len(data) < 2:
            print(f"⚠️  No data available for {symbol}")
            return 0
        
        # Safely extract first and last closing prices
        first = safe_float(data['Close'].iloc[0])
        last = safe_float(data['Close'].iloc[-1])
        
        change = round((last - first) / first * 100, 2)
        print(f"✓ {symbol}: {first:.2f} → {last:.2f} = {change}%")
        return change
        
    except Exception as e:
        print(f"❌ Error getting weekly change for {symbol}: {e}")
        return 0

def get_daily_top_gainers(symbols, top_n=5):
    perf = []
    for sym in symbols:
        try:
            # Get last 5 days to ensure we have 2 trading days
            data = yf.download(sym, period="5d", progress=False)
            
            if data.empty or len(data) < 2:
                print(f"⚠️  Insufficient data for {sym}")
                continue
            
            close_last = safe_float(data['Close'].iloc[-1])
            close_prev = safe_float(data['Close'].iloc[-2])
            pct_change = round((close_last - close_prev) / close_prev * 100, 2)
            perf.append((sym, pct_change))
            print(f"✓ {sym}: {pct_change}%")
            
        except Exception as e:
            print(f"❌ Error processing {sym}: {e}")
            continue
    
    if not perf:
        print("⚠️  No performance data collected")
        return []
    
    perf.sort(key=lambda x: x[1], reverse=True)
    return perf[:top_n]

def get_daily_bottom_performers(symbols, bottom_n=5):
    perf = []
    for sym in symbols:
        try:
            data = yf.download(sym, period="5d", progress=False)
            
            if data.empty or len(data) < 2:
                continue
            
            close_last = safe_float(data['Close'].iloc[-1])
            close_prev = safe_float(data['Close'].iloc[-2])
            pct_change = round((close_last - close_prev) / close_prev * 100, 2)
            perf.append((sym, pct_change))
            
        except Exception as e:
            print(f"❌ Error processing {sym}: {e}")
            continue
    
    if not perf:
        return []
    
    perf.sort(key=lambda x: x[1])
    return perf[:bottom_n]

def get_index_weekly_changes(symbol):
    try:
        # Get more data to ensure we have enough trading days
        data = yf.download(symbol, period="1mo", progress=False)
        
        if data.empty or len(data) < 6:
            print(f"⚠️  Insufficient data for {symbol}")
            return [], pd.DataFrame()
        
        changes = []
        # Calculate week-over-week for last 5 trading days
        if len(data) >= 10:
            for i in range(len(data) - 5):
                if i + 5 >= len(data):
                    break
                last_week_close = safe_float(data['Close'].iloc[i])
                this_week_close = safe_float(data['Close'].iloc[i+5])
                day = data.index[i+5].strftime("%Y-%m-%d")
                pct_change = round((this_week_close - last_week_close)/last_week_close*100, 2)
                changes.append((day, pct_change))
        
        return changes, data
        
    except Exception as e:
        print(f"❌ Error getting index changes for {symbol}: {e}")
        return [], pd.DataFrame()

def plot_chart(data_dict, title):
    if not data_dict:
        # Return empty chart if no data
        plt.figure(figsize=(10,5))
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center')
        plt.title(title)
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    
    plt.figure(figsize=(10,5))
    has_data = False
    for name, series in data_dict.items():
        if not series.empty and len(series) > 0:
            plt.plot(series.index, series.values, label=name, marker='o')
            has_data = True
    
    if not has_data:
        plt.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=plt.gca().transAxes)
    else:
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
    
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64

# ---------------- PROCESS COMMODITIES ----------------
print("\n" + "="*50)
print("PROCESSING COMMODITIES")
print("="*50)

commodity_perf = []
commodity_charts = {}

for name, sym in commodities.items():
    print(f"\nFetching {name} ({sym})...")
    change = get_weekly_change(sym)
    commodity_perf.append((name, change))
    
    try:
        data = yf.download(sym, period="1mo", progress=False)
        if not data.empty:
            commodity_charts[name] = data['Close']
        else:
            print(f"⚠️  No chart data for {name}")
    except Exception as e:
        print(f"❌ Error getting chart data for {name}: {e}")

# Sort by change value
commodity_perf.sort(key=lambda x: x[1], reverse=True)
top_5_commodities = commodity_perf[:5]

print(f"\n✓ Processed {len(commodity_perf)} commodities")

# ---------------- PROCESS STOCKS ----------------
print("\n" + "="*50)
print("PROCESSING STOCKS")
print("="*50)

print("\nFetching Large Caps...")
top_10_large = get_daily_top_gainers(large_caps, top_n=10)

print("\nFetching Mid Caps...")
top_5_mid = get_daily_top_gainers(mid_caps, top_n=5)

print("\nFetching Bottom Performers...")
bottom_5_stocks = get_daily_bottom_performers(large_caps + mid_caps, bottom_n=5)

# ---------------- PROCESS INDICES ----------------
print("\n" + "="*50)
print("PROCESSING INDICES")
print("="*50)

index_changes = {}
index_charts_data = {}

for idx_name, idx_sym in indices.items():
    print(f"\nFetching {idx_name} ({idx_sym})...")
    changes, data = get_index_weekly_changes(idx_sym)
    index_changes[idx_name] = changes
    if not data.empty:
        index_charts_data[idx_name] = data['Close']
        print(f"✓ Got {len(data)} days of data for {idx_name}")

# Generate charts
print("\n" + "="*50)
print("GENERATING CHARTS")
print("="*50)

commodity_chart_img = plot_chart(commodity_charts, "Commodities - Last Month")
index_chart_img = plot_chart(index_charts_data, "SENSEX & NIFTY - Last Month")

# ---------------- CREATE HTML REPORT ----------------
print("\n" + "="*50)
print("CREATING HTML REPORT")
print("="*50)

html_content = """
<html>
<head>
<style>
body { font-family: Arial, sans-serif; padding: 20px; }
table { border-collapse: collapse; margin: 20px 0; width: 100%; max-width: 600px; }
th { background-color: #4CAF50; color: white; padding: 10px; text-align: left; }
td { padding: 8px; border-bottom: 1px solid #ddd; }
tr:nth-child(even) { background-color: #f9f9f9; }
tr:hover { background-color: #f5f5f5; }
h2 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
h3 { color: #666; margin-top: 30px; border-left: 4px solid #4CAF50; padding-left: 10px; }
img { max-width: 100%; height: auto; margin: 20px 0; }
.positive { color: green; font-weight: bold; }
.negative { color: red; font-weight: bold; }
.neutral { color: #666; }
</style>
</head>
<body>
<h2>📊 Daily Market & Commodity Report</h2>
<p><strong>Report Date:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M UTC") + """</p>
"""

# Commodities Table
html_content += "<h3>🏆 Top 5 Commodity Performers (Week-over-Week)</h3>"
if top_5_commodities and any(change != 0 for _, change in top_5_commodities):
    html_content += "<table><tr><th>Commodity</th><th>Week % Change</th></tr>"
    for name, change in top_5_commodities:
        css_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
        sign = "+" if change > 0 else ""
        html_content += f"<tr><td>{name}</td><td class='{css_class}'>{sign}{change:.2f}%</td></tr>"
    html_content += "</table>"
    html_content += f"<img src='data:image/png;base64,{commodity_chart_img}' alt='Commodity Chart'>"
else:
    html_content += "<p>⚠️ No commodity data available</p>"

# Large Cap
html_content += "<h3>📈 Top 10 Large Cap Performers (Daily)</h3>"
if top_10_large:
    html_content += "<table><tr><th>Symbol</th><th>% Change</th></tr>"
    for sym, change in top_10_large:
        css_class = "positive" if change > 0 else "negative"
        sign = "+" if change > 0 else ""
        html_content += f"<tr><td>{sym}</td><td class='{css_class}'>{sign}{change:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No large cap data available</p>"

# Mid Cap
html_content += "<h3>📊 Top 5 Mid Cap Performers (Daily)</h3>"
if top_5_mid:
    html_content += "<table><tr><th>Symbol</th><th>% Change</th></tr>"
    for sym, change in top_5_mid:
        css_class = "positive" if change > 0 else "negative"
        sign = "+" if change > 0 else ""
        html_content += f"<tr><td>{sym}</td><td class='{css_class}'>{sign}{change:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No mid cap data available</p>"

# Bottom 5
html_content += "<h3>📉 Bottom 5 Performers (Daily)</h3>"
if bottom_5_stocks:
    html_content += "<table><tr><th>Symbol</th><th>% Change</th></tr>"
    for sym, change in bottom_5_stocks:
        html_content += f"<tr><td>{sym}</td><td class='negative'>{change:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No bottom performer data available</p>"

# Indices
html_content += "<h3>📊 SENSEX & NIFTY Performance</h3>"
if index_charts_data:
    html_content += f"<img src='data:image/png;base64,{index_chart_img}' alt='Index Chart'>"
    
    for idx_name, changes in index_changes.items():
        if changes:
            html_content += f"<h4>{idx_name} - Week-over-Week Comparison</h4>"
            html_content += "<table><tr><th>Date</th><th>% Change</th></tr>"
            for day, change in changes[-5:]:  # Show last 5 comparisons
                css_class = "positive" if change > 0 else "negative" if change < 0 else "neutral"
                sign = "+" if change > 0 else ""
                html_content += f"<tr><td>{day}</td><td class='{css_class}'>{sign}{change:.2f}%</td></tr>"
            html_content += "</table>"
else:
    html_content += "<p>⚠️ No index data available</p>"

html_content += """
<hr style="margin-top: 40px;">
<p style="color: #999; font-size: 12px;">
<em>This report is generated automatically. Data sourced from Yahoo Finance.</em>
</p>
</body>
</html>
"""

# ---------------- SEND EMAIL ----------------
print("\n" + "="*50)
print("SENDING EMAIL")
print("="*50)

try:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"📊 Market Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(html_content, "html"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✅ Email sent successfully!")
    print(f"   To: {RECEIVER_EMAIL}")
except Exception as e:
    print("❌ Failed to send email:", e)
    import traceback
    traceback.print_exc()
    raise
