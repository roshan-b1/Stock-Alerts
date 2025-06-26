import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import os

# === EMAIL SETUP ===
EMAIL_ADDRESS = "roshanbharadwaj9@gmail.com"
EMAIL_PASSWORD = "ixqa lkry piwl mtnb"
TO_EMAIL = "roshanjb07@gmail.com"

# === RSI FUNCTION (Wilder's smoothing) ===


def compute_rsi_wilder(data, period=5):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period,
                        adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period,
                        adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# === SEND EMAIL WITH PRICE + CHART ===


def send_email_with_chart(subject, body, image_path, price):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = TO_EMAIL

    full_body = f"{body}\n\nCurrent AMZN Price: ${price:.2f}"
    msg.attach(MIMEText(full_body, 'plain'))

    with open(image_path, 'rb') as img_file:
        img = MIMEImage(img_file.read())
        img.add_header('Content-Disposition', 'attachment',
                       filename=os.path.basename(image_path))
        msg.attach(img)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print("❌ Failed to send email:", e)

# === MAIN ALERT FUNCTION ===


def check_amzn():
    df = yf.download("AMZN", period="3mo", interval="1d", progress=False)

    # Fix MultiIndex issue
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty or 'Close' not in df.columns:
        print("❌ No 'Close' data found.")
        return

    # Calculate indicators
    df['RSI_5'] = compute_rsi_wilder(df)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    df = df.dropna(subset=['RSI_5', 'SMA_50'])

    latest = df.iloc[-1]
    price = latest['Close']
    rsi = latest['RSI_5']
    sma_50 = latest['SMA_50']

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Price: ${price:.2f}, RSI(5): {rsi:.2f}")

    # === Alert condition: RSI < 30 and price below SMA 50 ===
    if rsi < 30 and price < sma_50:
        # Plot chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        df['Close'].plot(ax=ax1, label="Close", color='black')
        df['SMA_20'].plot(ax=ax1, label="SMA 20")
        df['SMA_50'].plot(ax=ax1, label="SMA 50")
        df['SMA_200'].plot(ax=ax1, label="SMA 200")
        ax1.set_title("AMZN Price + SMAs")
        ax1.grid()
        ax1.legend()

        df['RSI_5'].plot(ax=ax2, color='orange', label="RSI(5)")
        ax2.axhline(70, linestyle='--', color='red')
        ax2.axhline(30, linestyle='--', color='green')
        ax2.set_title("RSI(5)")
        ax2.grid()
        plt.tight_layout()

        chart_path = "amzn_rsi_sma_chart.png"
        plt.savefig(chart_path)
        plt.close()

        send_email_with_chart(
            "📉 AMZN Swing Entry Signal - RSI(5) < 30",
            f"RSI(5) is {rsi:.2f} and price (${price:.2f}) is below SMA(50) (${sma_50:.2f}).",
            chart_path,
            price
        )
    else:
        print("No alert conditions met.")


# === RUN ===
check_amzn()
