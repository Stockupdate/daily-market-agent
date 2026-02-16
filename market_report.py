import yfinance as yf
import pandas as pd
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD = os.environ["SENDER_PASSWORD"]
RECEIVER_EMAIL = os.environ["RECEIVER_EMAIL"]

# Tech Stocks (Indian IT)
TECH_STOCKS = [
    "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS",
    "TECHM.NS", "LTIM.NS", "PERSISTENT.NS",
    "COFORGE.NS", "MPHASIS.NS", "LTTS.NS"
]

# Commodity Stocks (Metals, Oil & Gas)
COMMODITY_STOCKS = [
    "RELIANCE.NS", "ONGC.NS", "COALINDIA.NS",
    "TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS",
    "SAIL.NS", "BPCL.NS", "IOC.NS", "GAIL.NS"
]

# -----------------------------
# FETCH DATA
# -----------------------------
def get_stock_data(tickers):
    data = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")
        if len(hist) >= 2:
            close_today = hist["Close"].iloc[-1]
            close_yesterday = hist["Close"].iloc[-2]
            pct_change = ((close_today - close_yesterday) / close_yesterday) * 100
            data.append({
                "Stock": ticker.replace(".NS", ""),
                "Price": round(close_today, 2),
                "Change (%)": round(pct_change, 2)
            })
    return pd.DataFrame(data)

def format_table(df):
    return df.to_html(index=False)

# -----------------------------
# MAIN LOGIC
# -----------------------------
def generate_report():
    # SENSEX
    sensex = yf.Ticker("^BSESN")
    hist = sensex.history(period="2d")
    sensex_today = hist["Close"].iloc[-1]
    sensex_yesterday = hist["Close"].iloc[-2]
    sensex_change = ((sensex_today - sensex_yesterday) / sensex_yesterday) * 100

    tech_df = get_stock_data(TECH_STOCKS)
    comm_df = get_stock_data(COMMODITY_STOCKS)

    tech_gainers = tech_df.sort_values("Change (%)", ascending=False).head(10)
    tech_losers = tech_df.sort_values("Change (%)").head(10)

    comm_gainers = comm_df.sort_values("Change (%)", ascending=False).head(10)
    comm_losers = comm_df.sort_values("Change (%)").head(10)

    today = datetime.now().strftime("%d %b %Y")

    html = f"""
    <h2>📊 Indian Market Report – {today}</h2>
    <h3>SENSEX: {round(sensex_today,2)} ({round(sensex_change,2)}%)</h3>

    <h3>🔼 Top Tech Gainers</h3>
    {format_table(tech_gainers)}

    <h3>🔽 Top Tech Losers</h3>
    {format_table(tech_losers)}

    <h3>🔼 Top Commodity Gainers</h3>
    {format_table(comm_gainers)}

    <h3>🔽 Top Commodity Losers</h3>
    {format_table(comm_losers)}
    """

    return html

# -----------------------------
# SEND EMAIL
# -----------------------------
def send_email(html_content):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = "📊 Daily Indian Market Report"

    msg.attach(MIMEText(html_content, "html"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()

if __name__ == "__main__":
    report = generate_report()
    send_email(report)

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(html_content):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = "📊 Daily Indian Market Report"

        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("✅ Email sent successfully!")  # Log success
    except Exception as e:
        print("❌ Failed to send email:", e)  # Log failure
        raise
