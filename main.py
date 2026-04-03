import pandas as pd
import numpy as np
import os
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from garminconnect import Garmin

# --- Configuration & Paths ---
CSV_PATH = 'data/garmin_runs.csv'
TOKEN_PATH = 'data/garmin_token.json'
START_DATE = "2026-01-01"
TODAY = datetime.now()

def get_garmin_client():
    """
    Handles authentication using session tokens to avoid 429 (Rate Limit) errors.
    If a token exists, it attempts to restore the session. Otherwise, it performs a fresh login.
    """
    email = os.environ.get('GARMIN_EMAIL')
    password = os.environ.get('GARMIN_PASS')
    
    # Ensure data directory exists for token storage
    os.makedirs('data', exist_ok=True)
    client = Garmin(email, password)
    
    # 1. Try to load existing session from disk
    if os.path.exists(TOKEN_PATH):
        try:
            print("🔑 Found existing token, attempting to restore session...")
            with open(TOKEN_PATH, 'r') as f:
                token_data = json.load(f)
            client.login(token_data)
            print("✅ Session restored successfully.")
            return client
        except Exception as e:
            print(f"⚠️ Session expired or invalid: {e}. Proceeding to fresh login...")

    # 2. Fresh login (High risk of 429 if called too frequently)
    print("🔗 Performing fresh login...")
    client.login()
    
    # 3. Save the new session token for future runs
    with open(TOKEN_PATH, 'w') as f:
        json.dump(client.session_data, f)
    print("💾 Token saved to disk for next session.")
    return client

def sync_data():
    """
    Synchronizes Garmin activities with the local CSV file.
    Calculates ACWR (Acute:Chronic Workload Ratio) for injury prevention monitoring.
    """
    try:
        # Load existing database
        if os.path.exists(CSV_PATH):
            print("📁 Loading existing database...")
            df_existing = pd.read_csv(CSV_PATH)
            df_existing['date'] = pd.to_datetime(df_existing['date'])
            last_date = df_existing['date'].max().date()
            fetch_start = (last_date + timedelta(days=1)).isoformat()
        else:
            print("🆕 No existing database found. Starting fresh.")
            df_existing = pd.DataFrame()
            fetch_start = START_DATE

        # Initialize Garmin Client
        client = get_garmin_client()
        
        # Fetch new activities
        print(f"⏳ Fetching activities from {fetch_start} to today...")
        activities = client.get_activities_by_date(fetch_start, TODAY.date().isoformat())
        
        if not activities:
            print("☕ No new activities found in Garmin Connect.")
            return df_existing

        new_rows = []
        for act in activities:
            dist_m = act.get('distance', 0)
            duration_sec = act.get('duration', 0)
            dist_km = round(dist_m / 1000, 2)
            duration_min = round(duration_sec / 60, 2)
            
            # Stride Calculation Logic
            stride_cm = act.get('avgStrideLength', 0)
            cadence = act.get('avgCadence', 0)
            if (not stride_cm or stride_cm == 0) and cadence > 0 and duration_min > 0:
                total_steps = cadence * duration_min
                stride_cm = (dist_km * 100000) / total_steps if total_steps > 0 else 0

            new_rows.append({
                'activity_id': act.get('activityId'),
                'date': act.get('startTimeLocal'),
                'type': act.get('activityType', {}).get('typeKey'),
                'distance_km': dist_km,
                'duration_min': duration_min,
                'pace_min_km': round(duration_min / dist_km, 2) if dist_km > 0 else 0,
                'avg_hr': act.get('averageHR', 0),
                'max_hr': act.get('maxHR', 0),
                'cadence': round(cadence, 1),
                'stride_length_cm': round(stride_cm, 1),
                'elevation_gain': act.get('elevationGain', 0),
            })

        new_df = pd.DataFrame(new_rows)
        new_df['date'] = pd.to_datetime(new_df['date'])
        
        # Merge datasets and remove duplicates
        full_df = pd.concat([df_existing, new_df]).drop_duplicates(subset=['activity_id'])
        full_df = full_df.sort_values('date').reset_index(drop=True)
        
        # Calculate Training Load (ACWR)
        print("📈 Recalculating training load metrics...")
        full_df['workload'] = full_df['distance_km'] * (full_df['avg_hr'] / 100)
        full_df['acute'] = full_df['workload'].rolling(window=7, min_periods=1).mean()
        full_df['chronic'] = full_df['workload'].rolling(window=28, min_periods=1).mean()
        full_df['acwr'] = (full_df['acute'] / full_df['chronic']).replace([np.inf, -np.inf], 0).fillna(0)

        # Save to CSV (This will be committed by GitHub Actions)
        full_df.to_csv(CSV_PATH, index=False)
        return full_df

    except Exception as e:
        print(f"❌ Error during sync: {e}")
        return None

def get_weekly_comparison_v2(df):
    """
    Generates a comparative summary of the last 3 weeks.
    """
    today_date = TODAY.date()
    periods = [
        (today_date - timedelta(days=6), today_date, "This Week"),
        (today_date - timedelta(days=13), today_date - timedelta(days=7), "Last Week"),
        (today_date - timedelta(days=20), today_date - timedelta(days=14), "2 Weeks Ago")
    ]

    comparison_data = []
    for start, end, label in periods:
        mask = (df['date'].dt.date >= start) & (df['date'].dt.date <= end)
        week_df = df.loc[mask]

        if not week_df.empty:
            stats = {
                'label': label,
                'num_runs': len(week_df),
                'distance': week_df['distance_km'].sum(),
                'longest_run': week_df['distance_km'].max(),
                'total_climb': week_df['elevation_gain'].sum(),
                'avg_pace': week_df['pace_min_km'].mean(),
                'avg_hr': week_df['avg_hr'].mean(),
                'stride': week_df['stride_length_cm'].mean(),
                'acwr': week_df['acwr'].iloc[-1],
                'efficiency': (week_df['distance_km'].sum() / (week_df['avg_hr'].mean() * (week_df['duration_min'].sum()/60))) if week_df['avg_hr'].mean() > 0 else 0
            }
        else:
            stats = {k: 0 for k in ['num_runs', 'distance', 'longest_run', 'total_climb', 'avg_pace', 'avg_hr', 'stride', 'acwr', 'efficiency']}
            stats['label'] = label
        
        comparison_data.append(stats)
    return comparison_data

def send_performance_report_v5(comparison_data):
    """
    Sends an HTML formatted report via SMTP.
    Requires SENDER_EMAIL, RECEIVER_EMAIL, and GRAMIN_REPORT (App Password) environment variables.
    """
    SENDER = os.environ.get('SENDER_EMAIL')
    RECEIVER = os.environ.get('RECEIVER_EMAIL')
    PASSWORD = os.environ.get('GRAMIN_REPORT')

    if not SENDER or not RECEIVER or not PASSWORD:
        print("❌ Email credentials missing in environment variables.")
        return

    c = comparison_data
    acwr_val = c[0]['acwr']
    # Color coding based on injury risk
    acwr_color = "#27ae60" if 0.8 <= acwr_val <= 1.3 else "#e67e22" if acwr_val < 0.8 else "#e74c3c"

    html_content = f"""
    <div dir="ltr" style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; padding: 25px; border-radius: 15px; background-color: #ffffff;">
        <h2 style="color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 10px;">Weekly Running Analytics</h2>
        <p style="text-align: center; color: #7f8c8d; margin-top: 0;">Report for {TODAY.strftime('%B %d, %Y')}</p>
        
        <div style="background-color: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 25px; border: 1px solid #eee;">
            <h3 style="margin-top: 0; color: #34495e; font-size: 16px; border-bottom: 1px solid #ddd; padding-bottom: 5px;">🏆 Weekly Highlights</h3>
            <table style="width: 100%;">
                <tr>
                    <td style="width: 33%; text-align: center;">
                        <span style="font-size: 11px; color: #7f8c8d; display: block;">Longest Run</span>
                        <b style="font-size: 18px; color: #2980b9;">{c[0]['longest_run']:.1f} km</b>
                    </td>
                    <td style="width: 33%; text-align: center; border-left: 1px solid #ddd; border-right: 1px solid #ddd;">
                        <span style="font-size: 11px; color: #7f8c8d; display: block;">Total Climb</span>
                        <b style="font-size: 18px; color: #2980b9;">{int(c[0]['total_climb'])}m ⛰️</b>
                    </td>
                    <td style="width: 33%; text-align: center;">
                        <span style="font-size: 11px; color: #7f8c8d; display: block;">Consistency</span>
                        <b style="font-size: 18px; color: #2980b9;">{c[0]['num_runs']} Runs</b>
                    </td>
                </tr>
            </table>
        </div>

        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background-color: #3498db; color: white;">
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 13px;">Metric</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;">This Week</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;">Last Week</th>
                    <th style="padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;">2 Weeks Ago</th>
                </tr>
            </thead>
            <tbody>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Total Distance (km)</b></td><td style="text-align: center;">{c[0]['distance']:.1f}</td><td style="text-align: center;">{c[1]['distance']:.1f}</td><td style="text-align: center;">{c[2]['distance']:.1f}</td></tr>
                <tr style="background-color: #fcfcfc;"><td style="padding: 8px; border: 1px solid #ddd;"><b>Avg Pace</b></td><td style="text-align: center;">{c[0]['avg_pace']:.2f}</td><td style="text-align: center;">{c[1]['avg_pace']:.2f}</td><td style="text-align: center;">{c[2]['avg_pace']:.2f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Avg Heart Rate</b></td><td style="text-align: center;">{int(c[0]['avg_hr'])}</td><td style="text-align: center;">{int(c[1]['avg_hr'])}</td><td style="text-align: center;">{int(c[2]['avg_hr'])}</td></tr>
                <tr style="background-color: #fcfcfc;"><td style="padding: 8px; border: 1px solid #ddd;"><b>Stride Length (cm)</b></td><td style="text-align: center;">{c[0]['stride']:.1f}</td><td style="text-align: center;">{c[1]['stride']:.1f}</td><td style="text-align: center;">{c[2]['stride']:.1f}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Efficiency Score</b></td><td style="text-align: center;">{c[0]['efficiency']:.3f}</td><td style="text-align: center;">{c[1]['efficiency']:.3f}</td><td style="text-align: center;">{c[2]['efficiency']:.3f}</td></tr>
                <tr style="background-color: #fcfcfc;"><td style="padding: 8px; border: 1px solid #ddd;"><b>Load Ratio (ACWR)</b></td><td style="text-align: center; font-weight: bold; color: {acwr_color};">{acwr_val:.2f}</td><td style="text-align: center;">{c[1]['acwr']:.2f}</td><td style="text-align: center;">{c[2]['acwr']:.2f}</td></tr>
            </tbody>
        </table>

        <div style="margin-top: 25px; padding: 15px; background-color: #f0f7fd; border-left: 5px solid #3498db; border-radius: 8px;">
            <p style="margin: 0; font-size: 14px; color: #2c3e50;">
                <b>🏃 Coach's Analysis:</b><br>
                { "Caution: High workload detected. Prioritize recovery and sleep." if acwr_val > 1.3 
                  else "Maintenance: Training load is low. Consider a tempo run." if acwr_val < 0.8 
                  else "Optimal: Training load is perfectly balanced. Keep it up!" }
            </p>
        </div>
    </div>
    """

    msg = MIMEMultipart()
    msg['Subject'] = f"Weekly Running Analysis | {TODAY.strftime('%d/%m/%Y')}"
    msg['From'] = SENDER
    msg['To'] = RECEIVER
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER, PASSWORD)
            server.send_message(msg)
        print("✅ Performance report sent to inbox.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # 1. Sync data and update CSV
    final_df = sync_data()
    
    # 2. Proceed if sync was successful
    if final_df is not None and not final_df.empty:
        print("📊 Data synchronized. Analyzing weekly trends...")
        weekly_stats = get_weekly_comparison_v2(final_df)
        send_performance_report_v5(weekly_stats)
    else:
        print("⚠️ Execution stopped: No data available to report.")
