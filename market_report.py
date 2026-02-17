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
def get_multi_timeframe_change(symbol):
    """
    Get price changes across multiple timeframes
    Returns: (current_price, 1day%, 1week%, 3month%, 6month%)
    """
    try:
        # Get 7 months of data to ensure we have enough for all timeframes
        end_date = datetime.today()
        start_date = end_date - timedelta(days=210)  # ~7 months
        
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if data.empty or len(data) < 2:
            print(f"⚠️  No data available for {symbol}")
            return 0, 0, 0, 0, 0
        
        # Current price
        current_price = safe_float(data['Close'].iloc[-1])
        
        # 1-day change (if we have at least 2 days)
        day_1_change = 0
        if len(data) >= 2:
            price_1d_ago = safe_float(data['Close'].iloc[-2])
            day_1_change = round((current_price - price_1d_ago) / price_1d_ago * 100, 2)
        
        # 1-week change (approximately 5 trading days)
        week_1_change = 0
        if len(data) >= 6:
            price_1w_ago = safe_float(data['Close'].iloc[-6])
            week_1_change = round((current_price - price_1w_ago) / price_1w_ago * 100, 2)
        
        # 3-month change (approximately 63 trading days)
        month_3_change = 0
        if len(data) >= 64:
            price_3m_ago = safe_float(data['Close'].iloc[-64])
            month_3_change = round((current_price - price_3m_ago) / price_3m_ago * 100, 2)
        
        # 6-month change (approximately 126 trading days)
        month_6_change = 0
        if len(data) >= 127:
            price_6m_ago = safe_float(data['Close'].iloc[-127])
            month_6_change = round((current_price - price_6m_ago) / price_6m_ago * 100, 2)
        
        print(f"✓ {symbol}: ${current_price:.2f} | 1D: {day_1_change:+.2f}% | 1W: {week_1_change:+.2f}% | 3M: {month_3_change:+.2f}% | 6M: {month_6_change:+.2f}%")
        return current_price, day_1_change, week_1_change, month_3_change, month_6_change
        
    except Exception as e:
        print(f"❌ Error getting changes for {symbol}: {e}")
        return 0, 0, 0, 0, 0

def get_daily_top_gainers(symbols, top_n=5):
    perf = []
    for sym in symbols:
        try:
            # Get 7 months of data for all timeframes
            end_date = datetime.today()
            start_date = end_date - timedelta(days=210)
            data = yf.download(sym, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < 2:
                print(f"⚠️  Insufficient data for {sym}")
                continue
            
            # Current price
            current_price = safe_float(data['Close'].iloc[-1])
            
            # 1-day change
            day_1_change = 0
            if len(data) >= 2:
                price_1d_ago = safe_float(data['Close'].iloc[-2])
                day_1_change = round((current_price - price_1d_ago) / price_1d_ago * 100, 2)
            
            # 1-week change
            week_1_change = 0
            if len(data) >= 6:
                price_1w_ago = safe_float(data['Close'].iloc[-6])
                week_1_change = round((current_price - price_1w_ago) / price_1w_ago * 100, 2)
            
            # 3-month change
            month_3_change = 0
            if len(data) >= 64:
                price_3m_ago = safe_float(data['Close'].iloc[-64])
                month_3_change = round((current_price - price_3m_ago) / price_3m_ago * 100, 2)
            
            # 6-month change
            month_6_change = 0
            if len(data) >= 127:
                price_6m_ago = safe_float(data['Close'].iloc[-127])
                month_6_change = round((current_price - price_6m_ago) / price_6m_ago * 100, 2)
            
            perf.append((sym, current_price, day_1_change, week_1_change, month_3_change, month_6_change))
            print(f"✓ {sym}: ₹{current_price:.2f} | 1D: {day_1_change:+.2f}% | 1W: {week_1_change:+.2f}%")
            
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
            # Get 7 months of data for all timeframes
            end_date = datetime.today()
            start_date = end_date - timedelta(days=210)
            data = yf.download(sym, start=start_date, end=end_date, progress=False)
            
            if data.empty or len(data) < 2:
                continue
            
            # Current price
            current_price = safe_float(data['Close'].iloc[-1])
            
            # 1-day change
            day_1_change = 0
            if len(data) >= 2:
                price_1d_ago = safe_float(data['Close'].iloc[-2])
                day_1_change = round((current_price - price_1d_ago) / price_1d_ago * 100, 2)
            
            # 1-week change
            week_1_change = 0
            if len(data) >= 6:
                price_1w_ago = safe_float(data['Close'].iloc[-6])
                week_1_change = round((current_price - price_1w_ago) / price_1w_ago * 100, 2)
            
            # 3-month change
            month_3_change = 0
            if len(data) >= 64:
                price_3m_ago = safe_float(data['Close'].iloc[-64])
                month_3_change = round((current_price - price_3m_ago) / price_3m_ago * 100, 2)
            
            # 6-month change
            month_6_change = 0
            if len(data) >= 127:
                price_6m_ago = safe_float(data['Close'].iloc[-127])
                month_6_change = round((current_price - price_6m_ago) / price_6m_ago * 100, 2)
            
            perf.append((sym, current_price, day_1_change, week_1_change, month_3_change, month_6_change))
            
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
    price, day_1, week_1, month_3, month_6 = get_multi_timeframe_change(sym)
    commodity_perf.append((name, price, day_1, week_1, month_3, month_6))
    
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
    """Generate investment tips based on market data"""
    insights = []
    
    # Commodity insights (now with multiple timeframes: name, price, 1d%, 1w%, 3m%, 6m%)
    if commodities:
        top_commodity = commodities[0]
        worst_commodity = commodities[-1]
        
        # Check different timeframes for momentum
        if top_commodity[2] > 3:  # 1-day change > 3%
            insights.append(f"🟢 <strong>Commodity Momentum:</strong> {top_commodity[0]} is showing strong daily momentum with a {top_commodity[2]:+.2f}% gain. 6-month trend: {top_commodity[5]:+.2f}%.")
        
        if worst_commodity[2] < -3:  # 1-day change < -3%
            insights.append(f"🔴 <strong>Commodity Weakness:</strong> {worst_commodity[0]} declined {worst_commodity[2]:.2f}% today. However, check 3-month trend ({worst_commodity[4]:+.2f}%) for longer-term context.")
    
    # Large cap insights (sym, price, 1d%, 1w%, 3m%, 6m%)
    if large_caps and len(large_caps) >= 3:
        top_3_avg = sum(item[2] for item in large_caps[:3]) / 3
        
        if top_3_avg > 2:
            top_stock = large_caps[0]
            insights.append(f"📈 <strong>Large Cap Leaders:</strong> {top_stock[0]} leading with {top_stock[2]:+.2f}% daily, {top_stock[3]:+.2f}% weekly. Strong consistent momentum across timeframes.")
        
        # Check for consistent gainers
        consistent_gainers = [stock for stock in large_caps if stock[2] > 1.5]
        if len(consistent_gainers) >= 5:
            insights.append(f"💚 <strong>Broad Market Strength:</strong> {len(consistent_gainers)} large caps up >1.5% today. Positive market sentiment favors equity exposure.")
    
    # Mid cap insights
    if mid_caps:
        top_mid = mid_caps[0]
        if top_mid[2] > 3:
            # Compare short-term vs long-term momentum
            if top_mid[5] > 15:  # 6-month > 15%
                insights.append(f"🚀 <strong>Mid Cap Hot Pick:</strong> {top_mid[0]} surged {top_mid[2]:+.2f}% today with strong 6-month gains of {top_mid[5]:+.2f}%. Sustained uptrend.")
            else:
                insights.append(f"🚀 <strong>Mid Cap Opportunity:</strong> {top_mid[0]} jumped {top_mid[2]:+.2f}% today. Check 3M/6M trends before entry - may be volatile.")
    
    # Small cap insights
    if small_caps:
        top_small = small_caps[0]
        if top_small[2] > 5:
            insights.append(f"💎 <strong>Small Cap Breakout:</strong> {top_small[0]} spiked {top_small[2]:+.2f}% today. High volatility - only for risk-tolerant investors.")
        
        # Check if small caps are outperforming large caps
        if small_caps and large_caps:
            small_avg = sum(s[2] for s in small_caps[:3]) / 3
            large_avg = sum(l[2] for l in large_caps[:3]) / 3
            if small_avg > large_avg + 2:
                insights.append(f"🔥 <strong>Small Cap Outperformance:</strong> Small caps significantly outperforming large caps (avg {small_avg:.1f}% vs {large_avg:.1f}%). Risk-on market mode.")
    
    # Bottom performers - potential opportunities or warnings
    if bottom_performers and len(bottom_performers) >= 2:
        worst_stock = bottom_performers[0]
        
        if worst_stock[2] < -5:
            # Check if it's a long-term decline or just today
            if worst_stock[5] < -20:  # 6-month also very negative
                insights.append(f"⚠️ <strong>Structural Decline:</strong> {worst_stock[0]} down {worst_stock[2]:.2f}% today and {worst_stock[5]:.2f}% over 6 months. Avoid until fundamentals improve.")
            else:
                insights.append(f"⚠️ <strong>Sharp Drop Alert:</strong> {worst_stock[0]} fell {worst_stock[2]:.2f}% today but 6M trend is {worst_stock[5]:+.2f}%. Could be temporary dip or warning sign - investigate.")
        
        # Check if multiple stocks are down significantly
        heavy_losers = [stock for stock in bottom_performers if stock[2] < -3]
        if len(heavy_losers) >= 3:
            insights.append(f"🔻 <strong>Market Weakness Detected:</strong> {len(heavy_losers)} stocks down >3% today. Consider defensive positioning or profit booking.")
    
    # Index insights
    if indices:
        for idx_name, changes in indices.items():
            if changes and len(changes) > 0:
                latest_change = changes[-1][1] if changes else 0
                
                if latest_change > 2:
                    insights.append(f"📊 <strong>{idx_name} Bullish:</strong> Index up {latest_change:+.2f}% week-over-week. Good for long-term SIP investments.")
                elif latest_change < -2:
                    insights.append(f"📊 <strong>{idx_name} Bearish:</strong> Index down {latest_change:.2f}% week-over-week. Maintain cash reserves, wait for stabilization.")
    
    # General market sentiment
    if large_caps and mid_caps:
        all_tracked = large_caps + mid_caps + (small_caps if small_caps else [])
        total_gainers = len([s for s in all_tracked if s[2] > 0])
        total_stocks = len(all_tracked)
        gainer_ratio = total_gainers / total_stocks if total_stocks > 0 else 0
        
        if gainer_ratio > 0.7:
            insights.append(f"🌟 <strong>Strong Market Breadth:</strong> {int(gainer_ratio*100)}% of stocks in the green. Broad strength favors momentum and growth strategies.")
        elif gainer_ratio < 0.3:
            insights.append(f"🛡️ <strong>Weak Market Breadth:</strong> Only {int(gainer_ratio*100)}% positive. Consider defensive sectors (FMCG, Pharma) or quality large-caps.")
    
    # Add disclaimer
    insights.append("<br><em><strong>⚠️ Disclaimer:</strong> These insights are based on price movements and technical indicators only. Always conduct thorough fundamental analysis, consider your risk tolerance, and consult a financial advisor before making investment decisions. Past performance does not guarantee future results.</em>")
    
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
html_content += "<h3>🏆 Top 5 Commodity Performers (Multiple Timeframes)</h3>"
if top_5_commodities and any(day_1 != 0 for _, _, day_1, _, _, _ in top_5_commodities):
    html_content += "<table><tr><th>Commodity</th><th>Current Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for name, price, day_1, week_1, month_3, month_6 in top_5_commodities:
        # Color code each timeframe
        d1_class = "positive" if day_1 > 0 else "negative" if day_1 < 0 else "neutral"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td>{name}</td><td>${price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
    html_content += "</table>"
    html_content += f"<img src='data:image/png;base64,{commodity_chart_img}' alt='Commodity Chart'>"
else:
    html_content += "<p>⚠️ No commodity data available</p>"

# Overall Top Gainers (NEW SECTION)
html_content += "<h3>🔥 Top 10 Overall Market Gainers (Multiple Timeframes)</h3>"
if top_10_overall:
    html_content += "<table><tr><th>Rank</th><th>Symbol</th><th>Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for idx, (sym, price, day_1, week_1, month_3, month_6) in enumerate(top_10_overall, 1):
        # Determine badge based on which list it belongs to
        if sym in large_caps:
            badge = "🔵"
        elif sym in mid_caps:
            badge = "🟢"
        else:
            badge = "🟡"
        
        # Color code each timeframe
        d1_class = "positive" if day_1 > 0 else "negative"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td><strong>#{idx}</strong></td><td>{badge} {sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No overall market data available</p>"

# Large Cap
html_content += "<h3>📈 Top 10 Large Cap Performers (Multiple Timeframes)</h3>"
if top_10_large:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for sym, price, day_1, week_1, month_3, month_6 in top_10_large:
        d1_class = "positive" if day_1 > 0 else "negative"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No large cap data available</p>"

# Mid Cap
html_content += "<h3>📊 Top 5 Mid Cap Performers (Multiple Timeframes)</h3>"
if top_5_mid:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for sym, price, day_1, week_1, month_3, month_6 in top_5_mid:
        d1_class = "positive" if day_1 > 0 else "negative"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No mid cap data available</p>"

# Small Cap (NEW SECTION)
html_content += "<h3>⚡ Top 5 Small Cap Performers (Multiple Timeframes)</h3>"
if top_5_small:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for sym, price, day_1, week_1, month_3, month_6 in top_5_small:
        d1_class = "positive" if day_1 > 0 else "negative"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        d1_sign = "+" if day_1 > 0 else ""
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{d1_sign}{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
    html_content += "</table>"
else:
    html_content += "<p>⚠️ No small cap data available</p>"

# Bottom 5
html_content += "<h3>📉 Bottom 5 Performers (Multiple Timeframes)</h3>"
if bottom_5_stocks:
    html_content += "<table><tr><th>Symbol</th><th>Price</th><th>1-Day %</th><th>1-Week %</th><th>3-Month %</th><th>6-Month %</th></tr>"
    for sym, price, day_1, week_1, month_3, month_6 in bottom_5_stocks:
        d1_class = "negative"
        w1_class = "positive" if week_1 > 0 else "negative" if week_1 < 0 else "neutral"
        m3_class = "positive" if month_3 > 0 else "negative" if month_3 < 0 else "neutral"
        m6_class = "positive" if month_6 > 0 else "negative" if month_6 < 0 else "neutral"
        
        w1_sign = "+" if week_1 > 0 else ""
        m3_sign = "+" if month_3 > 0 else ""
        m6_sign = "+" if month_6 > 0 else ""
        
        html_content += f"<tr><td>{sym}</td><td>₹{price:.2f}</td>"
        html_content += f"<td class='{d1_class}'>{day_1:.2f}%</td>"
        html_content += f"<td class='{w1_class}'>{w1_sign}{week_1:.2f}%</td>"
        html_content += f"<td class='{m3_class}'>{m3_sign}{month_3:.2f}%</td>"
        html_content += f"<td class='{m6_class}'>{m6_sign}{month_6:.2f}%</td></tr>"
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
