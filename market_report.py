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

# Example large-cap and mid-cap symbols - these will be dynamically fetched
# We'll use NIFTY indices to get comprehensive market coverage
large_caps = []  # Will be populated dynamically
mid_caps = []    # Will be populated dynamically

indices = {"SENSEX": "^BSESN", "NIFTY": "^NSEI"}

# ---------------- HELPER FUNCTION ----------------
def get_nifty_500_stocks():
    """
    Fetch NIFTY 500 stock list dynamically
    Returns list of stock symbols
    """
    try:
        # Common large cap stocks (NIFTY 50 representatives)
        nifty_50 = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS",
            "ITC.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
            "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
            "WIPRO.NS", "M&M.NS", "NTPC.NS", "POWERGRID.NS", "TATASTEEL.NS",
            "BAJAJFINSV.NS", "TECHM.NS", "ADANIPORTS.NS", "ONGC.NS", "COALINDIA.NS",
            "TATAMOTORS.NS", "GRASIM.NS", "JSWSTEEL.NS", "HINDALCO.NS", "INDUSINDBK.NS",
            "BPCL.NS", "CIPLA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
            "HEROMOTOCO.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "SHRIRAMFIN.NS", "ADANIENT.NS",
            "SBILIFE.NS", "BAJAJ-AUTO.NS", "HDFCLIFE.NS", "TRENT.NS", "PIDILITIND.NS"
        ]
        
        # Mid cap stocks (NIFTY Midcap 50 representatives)
        nifty_midcap = [
            "GODREJCP.NS", "VEDL.NS", "DLF.NS", "SAIL.NS", "BANKBARODA.NS",
            "GAIL.NS", "LUPIN.NS", "SIEMENS.NS", "BEL.NS", "CANBK.NS",
            "PNB.NS", "INDIGO.NS", "NMDC.NS", "IOC.NS", "IDEA.NS",
            "TORNTPHARM.NS", "MOTHERSON.NS", "BOSCHLTD.NS", "PETRONET.NS", "HAVELLS.NS",
            "DABUR.NS", "AMBUJACEM.NS", "ACC.NS", "CONCOR.NS", "MUTHOOTFIN.NS",
            "PAGEIND.NS", "BERGEPAINT.NS", "COLPAL.NS", "MARICO.NS", "GODREJPROP.NS",
            "BANDHANBNK.NS", "ABBOTINDIA.NS", "BIOCON.NS", "ALKEM.NS", "PIIND.NS",
            "MCDOWELL-N.NS", "AUROPHARMA.NS", "LICI.NS", "HDFCAMC.NS", "INDUSTOWER.NS",
            "ZYDUSLIFE.NS", "TATACOMM.NS", "IPCALAB.NS", "BALKRISIND.NS", "TATAPOWER.NS",
            "ICICIGI.NS", "PERSISTENT.NS", "OBEROIRLTY.NS", "SBICARD.NS", "CUMMINSIND.NS"
        ]
        
        # Small cap stocks for additional coverage
        nifty_smallcap = [
            "IRCTC.NS", "POLYCAB.NS", "CROMPTON.NS", "HONAUT.NS", "JUBLFOOD.NS",
            "ASTRAL.NS", "Dixon.NS", "SCHAEFFLER.NS", "GICRE.NS", "LTIM.NS",
            "COFORGE.NS", "KPITTECH.NS", "MPHASIS.NS", "SONACOMS.NS", "OFSS.NS",
            "CLEAN.NS", "LTTS.NS", "FLUOROCHEM.NS", "KAJARIACER.NS", "VOLTAS.NS",
            "AMBER.NS", "ATUL.NS", "FINEORG.NS", "GNFC.NS", "NAVINFLUOR.NS",
            "IDFCFIRSTB.NS", "RECLTD.NS", "PFC.NS", "IRFC.NS", "CDSL.NS",
            "NYKAA.NS", "ZOMATO.NS", "PAYTM.NS", "POLICYBZR.NS", "DELHIVERY.NS"
        ]
        
        print(f"✓ Loaded {len(nifty_50)} large cap stocks")
        print(f"✓ Loaded {len(nifty_midcap)} mid cap stocks")
        print(f"✓ Loaded {len(nifty_smallcap)} small cap stocks")
        print(f"✓ Total universe: {len(nifty_50) + len(nifty_midcap) + len(nifty_smallcap)} stocks")
        
        return nifty_50, nifty_midcap, nifty_smallcap
        
    except Exception as e:
        print(f"❌ Error fetching stock list: {e}")
        # Fallback to minimal list
        return ["RELIANCE.NS", "TCS.NS", "INFY.NS"], ["MARUTI.NS"], []

# ---------------- HELPER FUNCTION ----------------
def safe_float(value):
    """Safely convert pandas Series, numpy array, or scalar to float"""
    if isinstance(value, (pd.Series, np.ndarray)):
        return float(value.iloc[0] if hasattr(value, 'iloc') else value[0])
    return float(value)

# ---------------- FUNCTIONS ----------------
def get_intraday_changes(symbol):
    """
    Get intraday price changes
    Returns: (current_price, 1day%, prev_close_to_open%, open_to_midday%, midday_to_close%)
    Midday = 1:00 PM IST (13:00)
    """
    try:
        from datetime import timezone
        
        # Get today's intraday data (1-minute intervals)
        today = datetime.today()
        
        # First get yesterday's close for 1-day change
        yesterday_data = yf.download(symbol, period="5d", progress=False)
        prev_close = 0
        day_1_change = 0
        
        if not yesterday_data.empty and len(yesterday_data) >= 2:
            prev_close = safe_float(yesterday_data['Close'].iloc[-2])
            current_close = safe_float(yesterday_data['Close'].iloc[-1])
            day_1_change = round((current_close - prev_close) / prev_close * 100, 2)
        
        # Get intraday data with 5-minute intervals (more reliable than 1-min)
        intraday_data = yf.download(symbol, period="1d", interval="5m", progress=False)
        
        if intraday_data.empty or len(intraday_data) < 3:
            print(f"⚠️  No intraday data for {symbol}, using daily close only")
            current_price = safe_float(yesterday_data['Close'].iloc[-1]) if not yesterday_data.empty else 0
            return current_price, day_1_change, 0, 0, 0
        
        # Extract key prices
        today_open = safe_float(intraday_data['Open'].iloc[0])
        current_price = safe_float(intraday_data['Close'].iloc[-1])
        
        # Find midday price (around 1:00 PM IST = 07:30 UTC)
        # Convert index to timezone-aware if needed
        midday_price = today_open  # Default fallback
        
        for idx, row in intraday_data.iterrows():
            # Get hour from the timestamp
            timestamp_hour = idx.hour if hasattr(idx, 'hour') else 0
            # Assuming data is in IST, look for 13:00 (1 PM)
            # If data is in UTC, 1 PM IST = 7:30 AM UTC, so look for hour 7
            if timestamp_hour >= 7 and timestamp_hour <= 8:  # Around 1 PM IST (7:30 UTC)
                midday_price = safe_float(row['Close'])
                break
        
        # If we couldn't find midday, estimate it as middle of the day
        if midday_price == today_open and len(intraday_data) > 3:
            mid_index = len(intraday_data) // 2
            midday_price = safe_float(intraday_data['Close'].iloc[mid_index])
        
        # Calculate changes
        prev_close_to_open = 0
        if prev_close > 0:
            prev_close_to_open = round((today_open - prev_close) / prev_close * 100, 2)
        
        open_to_midday = 0
        if today_open > 0:
            open_to_midday = round((midday_price - today_open) / today_open * 100, 2)
        
        midday_to_close = 0
        if midday_price > 0:
            midday_to_close = round((current_price - midday_price) / midday_price * 100, 2)
        
        print(f"✓ {symbol}: ₹{current_price:.2f} | 1D: {day_1_change:+.2f}% | Gap: {prev_close_to_open:+.2f}% | Morning: {open_to_midday:+.2f}% | Afternoon: {midday_to_close:+.2f}%")
        
        return current_price, day_1_change, prev_close_to_open, open_to_midday, midday_to_close
        
    except Exception as e:
        print(f"❌ Error getting intraday changes for {symbol}: {e}")
        # Fallback to daily data only
        try:
            data = yf.download(symbol, period="5d", progress=False)
            if not data.empty and len(data) >= 2:
                current_price = safe_float(data['Close'].iloc[-1])
                prev_close = safe_float(data['Close'].iloc[-2])
                day_1_change = round((current_price - prev_close) / prev_close * 100, 2)
                return current_price, day_1_change, 0, 0, 0
        except:
            pass
        return 0, 0, 0, 0, 0

def get_daily_top_gainers(symbols, top_n=5):
    perf = []
    for sym in symbols:
        try:
            price, day_1, gap, morning, afternoon = get_intraday_changes(sym)
            
            if price == 0:
                print(f"⚠️  Insufficient data for {sym}")
                continue
            
            perf.append((sym, price, day_1, gap, morning, afternoon))
            
        except Exception as e:
            print(f"❌ Error processing {sym}: {e}")
            continue
    
    if not perf:
        print("⚠️  No performance data collected")
        return []
    
    # Sort by 1-day change
    perf.sort(key=lambda x: x[2], reverse=True)
    return perf[:top_n]

def get_daily_bottom_performers(symbols, bottom_n=5):
    perf = []
    for sym in symbols:
        try:
            price, day_1, gap, morning, afternoon = get_intraday_changes(sym)
            
            if price == 0:
                continue
            
            perf.append((sym, price, day_1, gap, morning, afternoon))
            
        except Exception as e:
            print(f"❌ Error processing {sym}: {e}")
            continue
    
    if not perf:
        return []
    
    # Sort by 1-day change (ascending for bottom performers)
    perf.sort(key=lambda x: x[2])
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
    price, day_1, gap, morning, afternoon = get_intraday_changes(sym)
    commodity_perf.append((name, price, day_1, gap, morning, afternoon))
    
    try:
        data = yf.download(sym, period="1mo", progress=False)
        if not data.empty:
            commodity_charts[name] = data['Close']
        else:
            print(f"⚠️  No chart data for {name}")
    except Exception as e:
        print(f"❌ Error getting chart data for {name}: {e}")

# Sort by 1-day change value
commodity_perf.sort(key=lambda x: x[2], reverse=True)
top_5_commodities = commodity_perf[:5]

print(f"\n✓ Processed {len(commodity_perf)} commodities")

# ---------------- PROCESS STOCKS ----------------
print("\n" + "="*50)
print("PROCESSING STOCKS")
print("="*50)

# Dynamically load stock universe
print("\nLoading stock universe...")
large_caps, mid_caps, small_caps = get_nifty_500_stocks()

# Combine all stocks for comprehensive scanning
all_stocks = large_caps + mid_caps + small_caps

print(f"\nScanning {len(all_stocks)} stocks for performance...")
print("This may take a few minutes...")

# Get performance data for ALL stocks
print("\nFetching all stock data...")
all_stock_performance = get_daily_top_gainers(all_stocks, top_n=len(all_stocks))

# Filter by market cap category
large_cap_performance = [s for s in all_stock_performance if s[0] in large_caps]
mid_cap_performance = [s for s in all_stock_performance if s[0] in mid_caps]
small_cap_performance = [s for s in all_stock_performance if s[0] in small_caps]

# Get top performers from each category
top_10_large = large_cap_performance[:10] if large_cap_performance else []
top_5_mid = mid_cap_performance[:5] if mid_cap_performance else []
top_5_small = small_cap_performance[:5] if small_cap_performance else []

# Get overall market top gainers (across all caps)
top_10_overall = all_stock_performance[:10] if all_stock_performance else []

# Get bottom performers from entire universe
print("\nFetching bottom performers...")
bottom_5_stocks = get_daily_bottom_performers(all_stocks, bottom_n=5)

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

# ---------------- GENERATE INSIGHTS ----------------
print("\n" + "="*50)
print("GENERATING MARKET INSIGHTS")
print("="*50)

def generate_market_insights(commodities, large_caps, mid_caps, small_caps, bottom_performers, indices):
    """Generate investment tips based on intraday market data"""
    insights = []
    
    # Commodity insights (name, price, 1d%, gap%, morning%, afternoon%)
    if commodities:
        top_commodity = commodities[0]
        
        if top_commodity[2] > 3:  # 1-day change > 3%
            insights.append(f"🟢 <strong>Commodity Momentum:</strong> {top_commodity[0]} gained {top_commodity[2]:+.2f}% today. Morning session: {top_commodity[4]:+.2f}%, Afternoon: {top_commodity[5]:+.2f}%.")
    
    # Large cap insights (sym, price, 1d%, gap%, morning%, afternoon%)
    if large_caps and len(large_caps) >= 3:
        top_stock = large_caps[0]
        
        # Analyze intraday momentum
        if top_stock[2] > 2:
            if top_stock[4] > 0 and top_stock[5] > 0:
                insights.append(f"📈 <strong>Sustained Momentum:</strong> {top_stock[0]} up {top_stock[2]:+.2f}% with gains in both sessions (Morning: {top_stock[4]:+.2f}%, Afternoon: {top_stock[5]:+.2f}%). Strong bullish trend.")
            elif top_stock[5] > top_stock[4]:
                insights.append(f"📈 <strong>Afternoon Rally:</strong> {top_stock[0]} gained {top_stock[2]:+.2f}% with strong afternoon buying ({top_stock[5]:+.2f}%). Indicates positive sentiment.")
            else:
                insights.append(f"📈 <strong>Morning Leader:</strong> {top_stock[0]} up {top_stock[2]:+.2f}%, led by morning gains ({top_stock[4]:+.2f}%). Watch for consolidation.")
        
        # Check for consistent gainers
        consistent_gainers = [stock for stock in large_caps if stock[2] > 1.5]
        if len(consistent_gainers) >= 5:
            insights.append(f"💚 <strong>Broad Market Strength:</strong> {len(consistent_gainers)} large caps up >1.5%. Positive sentiment across the board.")
    
    # Mid cap insights
    if mid_caps:
        top_mid = mid_caps[0]
        if top_mid[2] > 3:
            insights.append(f"🚀 <strong>Mid Cap Breakout:</strong> {top_mid[0]} surged {top_mid[2]:+.2f}%. Gap: {top_mid[3]:+.2f}%. Higher risk but strong momentum.")
    
    # Small cap insights  
    if small_caps:
        top_small = small_caps[0]
        if top_small[2] > 5:
            insights.append(f"💎 <strong>Small Cap Spike:</strong> {top_small[0]} jumped {top_small[2]:+.2f}%. High volatility - suitable only for risk-tolerant traders.")
    
    # Gap analysis across market
    if large_caps:
        gap_ups = len([s for s in large_caps if s[3] > 1])  # Gap up > 1%
        gap_downs = len([s for s in large_caps if s[3] < -1])  # Gap down > 1%
        
        if gap_ups > 5:
            insights.append(f"🌅 <strong>Bullish Open:</strong> {gap_ups} stocks opened with significant gaps up. Strong overnight sentiment.")
        elif gap_downs > 5:
            insights.append(f"🌑 <strong>Weak Open:</strong> {gap_downs} stocks gapped down significantly. Cautious market sentiment.")
    
    # Bottom performers - intraday analysis
    if bottom_performers and len(bottom_performers) >= 2:
        worst_stock = bottom_performers[0]
        
        if worst_stock[2] < -5:
            if worst_stock[3] < -2:
                insights.append(f"⚠️ <strong>Gap Down Alert:</strong> {worst_stock[0]} opened {worst_stock[3]:.2f}% lower and ended down {worst_stock[2]:.2f}%. Strong selling pressure.")
            elif worst_stock[5] < -2:
                insights.append(f"⚠️ <strong>Afternoon Selloff:</strong> {worst_stock[0]} down {worst_stock[2]:.2f}%, most losses in afternoon ({worst_stock[5]:.2f}%). Late-day weakness.")
            else:
                insights.append(f"⚠️ <strong>Steady Decline:</strong> {worst_stock[0]} fell {worst_stock[2]:.2f}% throughout the day. Negative sentiment.")
    
    # Index insights
    if indices:
        for idx_name, changes in indices.items():
            if changes and len(changes) > 0:
                latest_change = changes[-1][1] if changes else 0
                
                if latest_change > 2:
                    insights.append(f"📊 <strong>{idx_name} Strong:</strong> Index up {latest_change:+.2f}% week-over-week. Favorable for SIP investments.")
                elif latest_change < -2:
                    insights.append(f"📊 <strong>{idx_name} Weak:</strong> Index down {latest_change:.2f}% week-over-week. Consider defensive positioning.")
    
    # General market sentiment
    if large_caps and mid_caps:
        all_tracked = large_caps + mid_caps + (small_caps if small_caps else [])
        total_gainers = len([s for s in all_tracked if s[2] > 0])
        total_stocks = len(all_tracked)
        gainer_ratio = total_gainers / total_stocks if total_stocks > 0 else 0
        
        if gainer_ratio > 0.7:
            insights.append(f"🌟 <strong>Strong Breadth:</strong> {int(gainer_ratio*100)}% of stocks positive. Broad-based rally favors momentum strategies.")
        elif gainer_ratio < 0.3:
            insights.append(f"🛡️ <strong>Weak Breadth:</strong> Only {int(gainer_ratio*100)}% positive. Shift to defensive sectors (FMCG, Pharma, IT).")
    
    # Add disclaimer
    insights.append("<br><em><strong>⚠️ Disclaimer:</strong> Insights based on intraday price movements and technical indicators only. Conduct fundamental analysis and consult a financial advisor before investing. Past performance does not guarantee future results.</em>")
    
    return insights

# Generate insights
market_insights = generate_market_insights(
    top_5_commodities,
    top_10_large,
    top_5_mid,
    top_5_small,
    bottom_5_stocks,
    index_changes
)

print(f"✓ Generated {len(market_insights)} market insights")

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
.stat-box { display: inline-block; background: #f0f0f0; padding: 15px; margin: 10px; border-radius: 8px; min-width: 150px; }
.stat-number { font-size: 24px; font-weight: bold; color: #4CAF50; }
.stat-label { font-size: 12px; color: #666; }
</style>
</head>
<body>
<h2>📊 Daily Market & Commodity Report</h2>
<p><strong>Report Date:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M UTC") + """</p>

<div style='background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;'>
<h4 style='margin-top: 0;'>📈 Market Coverage</h4>
<div class='stat-box'>
<div class='stat-number'>""" + str(len(all_stocks)) + """</div>
<div class='stat-label'>Stocks Tracked</div>
</div>
<div class='stat-box'>
<div class='stat-number'>""" + str(len([s for s in all_stock_performance if s[2] > 0])) + """</div>
<div class='stat-label'>Gainers</div>
</div>
<div class='stat-box'>
<div class='stat-number'>""" + str(len([s for s in all_stock_performance if s[2] < 0])) + """</div>
<div class='stat-label'>Losers</div>
</div>
<div class='stat-box'>
<div class='stat-number'>""" + f"{(len([s for s in all_stock_performance if s[2] > 0]) / len(all_stock_performance) * 100):.0f}" + """%</div>
<div class='stat-label'>Market Breadth</div>
</div>
</div>
"""

# Commodities Table
html_content += "<h3>🏆 Top 5 Commodity Performers (Intraday Tracking)</h3>"
if top_5_commodities and any(day_1 != 0 for _, _, day_1, _, _, _ in top_5_commodities):
    html_content += "<table><tr><th>Commodity</th><th>Current Price</th><th>1-Day %</th><th>Gap (Close→Open) %</th><th>Morning (Open→1PM) %</th><th>Afternoon (1PM→Close) %</th></tr>"
    for name, price, day_1, gap, morning, afternoon in top_5_commodities:
        # Color code each timeframe
        d1_class = "positive" if day_1 > 0 else "negative" if day_1 < 0 else "neutral"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td>{name}</td><td>${price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
    html_content += "</table>"
    html_content += f"<img src='data:image/png;base64,{commodity_chart_img}' alt='Commodity Chart'>"
else:
    html_content += "<p>⚠️ No commodity data available</p>"

# Overall Top Gainers (NEW SECTION)
html_content += "<h3>🔥 Top 10 Overall Market Gainers (Intraday Tracking)</h3>"
if top_10_overall:
    html_content += "<table><tr><th>Rank</th><th>Symbol</th><th>Price</th><th>1-Day %</th><th>Gap %</th><th>Morning %</th><th>Afternoon %</th></tr>"
    for idx, (sym, price, day_1, gap, morning, afternoon) in enumerate(top_10_overall, 1):
        # Determine badge based on which list it belongs to
        if sym in large_caps:
            badge = "🔵"
        elif sym in mid_caps:
            badge = "🟢"
        else:
            badge = "🟡"
        
        # Color code each timeframe
        d1_class = "positive" if day_1 > 0 else "negative"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td><strong>#{idx}</strong></td><td>{badge} {sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No overall market data available</p>"

# Large Cap
html_content += "<h3>📈 Top 10 Large Cap Performers (Intraday Tracking)</h3>"
if top_10_large:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>Gap %</th><th>Morning %</th><th>Afternoon %</th></tr>"
    for sym, price, day_1, gap, morning, afternoon in top_10_large:
        d1_class = "positive" if day_1 > 0 else "negative"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No large cap data available</p>"

# Mid Cap
html_content += "<h3>📊 Top 5 Mid Cap Performers (Intraday Tracking)</h3>"
if top_5_mid:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>Gap %</th><th>Morning %</th><th>Afternoon %</th></tr>"
    for sym, price, day_1, gap, morning, afternoon in top_5_mid:
        d1_class = "positive" if day_1 > 0 else "negative"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No mid cap data available</p>"

# Small Cap (NEW SECTION)
html_content += "<h3>⚡ Top 5 Small Cap Performers (Intraday Tracking)</h3>"
if top_5_small:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>Gap %</th><th>Morning %</th><th>Afternoon %</th></tr>"
    for sym, price, day_1, gap, morning, afternoon in top_5_small:
        d1_class = "positive" if day_1 > 0 else "negative"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No small cap data available</p>"

# Bottom 5
html_content += "<h3>📉 Bottom 5 Performers (Intraday Tracking)</h3>"
if bottom_5_stocks:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>Gap %</th><th>Morning %</th><th>Afternoon %</th></tr>"
    for sym, price, day_1, gap, morning, afternoon in bottom_5_stocks:
        d1_class = "negative"
        gap_class = "positive" if gap > 0 else "negative" if gap < 0 else "neutral"
        morn_class = "positive" if morning > 0 else "negative" if morning < 0 else "neutral"
        aft_class = "positive" if afternoon > 0 else "negative" if afternoon < 0 else "neutral"
        
        gap_sign = "+" if gap > 0 else ""
        morn_sign = "+" if morning > 0 else ""
        aft_sign = "+" if afternoon > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{day_1:.2f}%</td>"
        html_content += f"<td class='{gap_class}'>{gap_sign}{gap:.2f}%</td>"
        html_content += f"<td class='{morn_class}'>{morn_sign}{morning:.2f}%</td>"
        html_content += f"<td class='{aft_class}'>{aft_sign}{afternoon:.2f}%</td></tr>"
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

# Market Insights & Tips
html_content += "<h3>💡 Market Insights & Investment Tips</h3>"
html_content += "<div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50;'>"
for insight in market_insights:
    html_content += f"<p style='margin: 10px 0;'>{insight}</p>"
html_content += "</div>"

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

# Determine report type based on time
current_hour = datetime.now().hour
if current_hour < 9:
    report_type = "🌅 Morning Market Opening"
elif current_hour < 13:
    report_type = "☀️ Mid-Day Update"
elif current_hour < 16:
    report_type = "🌆 Pre-Close Analysis"
else:
    report_type = "🌙 Post-Market Summary"

try:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = f"{report_type} - {datetime.now().strftime('%b %d, %Y %I:%M %p')}"
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
