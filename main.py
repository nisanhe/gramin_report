{
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "provenance": [],
      "mount_file_id": "1j8poDzfdPdkPMRIYMx4XITBciEjIvF6b",
      "authorship_tag": "ABX9TyNoX9xOwuxtrjHvudqNLuw8",
      "include_colab_link": true
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    }
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "view-in-github",
        "colab_type": "text"
      },
      "source": [
        "<a href=\"https://colab.research.google.com/github/nisanhe/gramin_report/blob/main/main.py\" target=\"_parent\"><img src=\"https://colab.research.google.com/assets/colab-badge.svg\" alt=\"Open In Colab\"/></a>"
      ]
    },
    {
      "cell_type": "markdown",
      "source": [
        "# Pull Data from Garmin"
      ],
      "metadata": {
        "id": "YTjRaYokpD8t"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "\n",
        "import pandas as pd\n",
        "import numpy as np\n",
        "from datetime import datetime\n",
        "from garminconnect import Garmin\n",
        "from google.colab import userdata\n",
        "\n",
        "# --- הגדרות ---\n",
        "NEW_CSV_PATH = '/content/drive/MyDrive/Garmin_Project/garmin_master_2026_rebuilt.csv'\n",
        "START_DATE = \"2026-01-01\"\n",
        "\n",
        "def rebuild_2026_dataset():\n",
        "    try:\n",
        "        # 1. התחברות לגרמין\n",
        "        print(\"🔗 Connecting to Garmin...\")\n",
        "        client = Garmin(userdata.get('garmin_email'), userdata.get('garmin_pass'))\n",
        "        client.login()\n",
        "\n",
        "        # 2. שליפת כל הפעילויות מ-2026\n",
        "        print(f\"⏳ Fetching all activities since {START_DATE}...\")\n",
        "        activities = client.get_activities_by_date(START_DATE, datetime.now().date().isoformat())\n",
        "        print(f\"✅ Found {len(activities)} activities.\")\n",
        "\n",
        "        all_rows = []\n",
        "\n",
        "        for act in activities:\n",
        "            # חילוץ נתונים בסיסי\n",
        "            dist_m = act.get('distance', 0)\n",
        "            duration_sec = act.get('duration', 0)\n",
        "            dist_km = round(dist_m / 1000, 2)\n",
        "            duration_min = round(duration_sec / 60, 2)\n",
        "\n",
        "            # חישוב אורך צעד (ס\"מ)\n",
        "            stride_cm = act.get('avgStrideLength', 0)\n",
        "            cadence = act.get('avgCadence', 0)\n",
        "            if (stride_cm == 0 or stride_cm is None) and cadence > 0 and duration_min > 0:\n",
        "                total_steps = cadence * duration_min\n",
        "                stride_cm = (dist_km * 100000) / total_steps if total_steps > 0 else 0\n",
        "\n",
        "            # בניית השורה עם כל המדדים שביקשת\n",
        "            row = {\n",
        "                'activity_id': act.get('activityId'),\n",
        "                'date': act.get('startTimeLocal'),\n",
        "                'type': act.get('activityType', {}).get('typeKey'),\n",
        "                'distance_km': dist_km,\n",
        "                'duration_min': duration_min,\n",
        "                'pace_min_km': round(duration_min / dist_km, 2) if dist_km > 0 else 0,\n",
        "                'avg_hr': act.get('averageHR', 0),\n",
        "                'max_hr': act.get('maxHR', 0), # השדה שתיקנו\n",
        "                'cadence': round(cadence, 1),\n",
        "                'stride_length_cm': round(stride_cm, 1),\n",
        "                'vertical_oscillation': act.get('avgVerticalOscillation', 0),\n",
        "                'ground_contact_time': act.get('avgGroundContactTime', 0),\n",
        "                'elevation_gain': act.get('elevationGain', 0),\n",
        "                'elevation_loss': act.get('elevationLoss', 0),\n",
        "                'aerobic_te': act.get('aerobicTrainingEffect', 0),\n",
        "                'anaerobic_te': act.get('anaerobicTrainingEffect', 0),\n",
        "                'vo2_max': act.get('vO2MaxValue', 0),\n",
        "                'calories': act.get('calories', 0)\n",
        "            }\n",
        "            all_rows.append(row)\n",
        "\n",
        "        # 3. יצירת DataFrame וסידור לפי תאריך\n",
        "        df = pd.DataFrame(all_rows)\n",
        "        df['date'] = pd.to_datetime(df['date'])\n",
        "        df = df.sort_values('date').reset_index(drop=True)\n",
        "\n",
        "        # 4. חישוב מדדי עומס (Workload & ACWR)\n",
        "        print(\"📈 Calculating training metrics...\")\n",
        "        df['workload'] = df['distance_km'] * (df['avg_hr'] / 100)\n",
        "        df['acute'] = df['workload'].rolling(window=7, min_periods=1).mean()\n",
        "        df['chronic'] = df['workload'].rolling(window=28, min_periods=1).mean()\n",
        "        df['acwr'] = (df['acute'] / df['chronic']).replace([np.inf, -np.inf], 0).fillna(0)\n",
        "\n",
        "        # 5. שמירה לקובץ חדש\n",
        "        df.to_csv(NEW_CSV_PATH, index=False)\n",
        "        print(f\"🏁 DONE! New database saved to: {NEW_CSV_PATH}\")\n",
        "\n",
        "        return df\n",
        "\n",
        "    except Exception as e:\n",
        "        print(f\"❌ Error during rebuild: {e}\")\n",
        "\n",
        "# הרצה\n",
        "rebuilt_df = rebuild_2026_dataset()"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "aiC9Q7mnl2Mt",
        "outputId": "35ec1702-7051-445b-839b-c8aae571638f"
      },
      "execution_count": 24,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "🔗 Connecting to Garmin...\n",
            "⏳ Fetching all activities since 2026-01-01...\n",
            "✅ Found 60 activities.\n",
            "📈 Calculating training metrics...\n",
            "🏁 DONE! New database saved to: /content/drive/MyDrive/Garmin_Project/garmin_master_2026_rebuilt.csv\n"
          ]
        }
      ]
    },
    {
      "cell_type": "markdown",
      "source": [
        "# Summerize Data weekly comparison"
      ],
      "metadata": {
        "id": "bxWj9MYtpMGj"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "def get_weekly_comparison_v2(df):\n",
        "    today = datetime.now().date()\n",
        "    periods = [\n",
        "        (today - timedelta(days=6), today, \"This Week\"),\n",
        "        (today - timedelta(days=13), today - timedelta(days=7), \"Last Week\"),\n",
        "        (today - timedelta(days=20), today - timedelta(days=14), \"2 Weeks Ago\")\n",
        "    ]\n",
        "\n",
        "    comparison_data = []\n",
        "    for start, end, label in periods:\n",
        "        mask = (df['date'].dt.date >= start) & (df['date'].dt.date <= end)\n",
        "        week_df = df.loc[mask]\n",
        "\n",
        "        if not week_df.empty:\n",
        "            # חישוב המדדים לשבוע פעיל\n",
        "            stats = {\n",
        "                'label': label,\n",
        "                'num_runs': len(week_df), # מספר ריצות\n",
        "                'distance': week_df['distance_km'].sum(),\n",
        "                'longest_run': week_df['distance_km'].max(), # הריצה הכי ארוכה\n",
        "                'total_climb': week_df['elevation_gain'].sum(), # טיפוס מצטבר\n",
        "                'avg_pace': week_df['pace_min_km'].mean(),\n",
        "                'avg_hr': week_df['avg_hr'].mean(),\n",
        "                'stride': week_df['stride_length_cm'].mean(),\n",
        "                'acwr': week_df['acwr'].iloc[-1],\n",
        "                'efficiency': (week_df['distance_km'].sum() / (week_df['avg_hr'].mean() * (week_df['duration_min'].sum()/60))) if week_df['avg_hr'].mean() > 0 else 0\n",
        "            }\n",
        "        else:\n",
        "            stats = {k: 0 for k in [\n",
        "                'num_runs', 'distance', 'longest_run', 'total_climb',\n",
        "                'avg_pace', 'avg_hr', 'stride', 'acwr', 'efficiency'\n",
        "            ]}\n",
        "            stats['label'] = label\n",
        "\n",
        "        comparison_data.append(stats)\n",
        "\n",
        "    return comparison_data"
      ],
      "metadata": {
        "id": "VqWT_u1rp9kb"
      },
      "execution_count": 32,
      "outputs": []
    },
    {
      "cell_type": "markdown",
      "source": [
        "# Send email"
      ],
      "metadata": {
        "id": "LJ7JD3tFqHxS"
      }
    },
    {
      "cell_type": "code",
      "source": [
        "def send_performance_report_v5(comparison_data):\n",
        "    SENDER = userdata.get('sender')\n",
        "    RECEIVER = userdata.get('RECEIVER_EMAIL')\n",
        "    PASSWORD = userdata.get('gramin_report')\n",
        "\n",
        "    if not SENDER or not RECEIVER or not PASSWORD:\n",
        "        print(\"❌ Credentials missing.\")\n",
        "        return\n",
        "\n",
        "    c = comparison_data\n",
        "    acwr_val = c[0]['acwr']\n",
        "    acwr_color = \"#27ae60\" if 0.8 <= acwr_val <= 1.3 else \"#e67e22\" if acwr_val < 0.8 else \"#e74c3c\"\n",
        "\n",
        "    html_content = f\"\"\"\n",
        "    <div dir=\"ltr\" style=\"font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #e0e0e0; padding: 25px; border-radius: 15px; background-color: #ffffff;\">\n",
        "\n",
        "        <h2 style=\"color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; margin-bottom: 10px;\">Weekly Running Analytics</h2>\n",
        "        <p style=\"text-align: center; color: #7f8c8d; margin-top: 0;\">Report for {today.strftime('%B %d, %Y')}</p>\n",
        "\n",
        "        <div style=\"background-color: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 25px; border: 1px solid #eee;\">\n",
        "            <h3 style=\"margin-top: 0; color: #34495e; font-size: 16px; border-bottom: 1px solid #ddd; padding-bottom: 5px;\">🏆 Weekly Highlights</h3>\n",
        "            <table style=\"width: 100%;\">\n",
        "                <tr>\n",
        "                    <td style=\"width: 33%; text-align: center;\">\n",
        "                        <span style=\"font-size: 11px; color: #7f8c8d; display: block;\">Longest Run</span>\n",
        "                        <b style=\"font-size: 18px; color: #2980b9;\">{c[0]['longest_run']:.1f} km</b>\n",
        "                    </td>\n",
        "                    <td style=\"width: 33%; text-align: center; border-left: 1px solid #ddd; border-right: 1px solid #ddd;\">\n",
        "                        <span style=\"font-size: 11px; color: #7f8c8d; display: block;\">Total Climb</span>\n",
        "                        <b style=\"font-size: 18px; color: #2980b9;\">{int(c[0]['total_climb'])}m ⛰️</b>\n",
        "                    </td>\n",
        "                    <td style=\"width: 33%; text-align: center;\">\n",
        "                        <span style=\"font-size: 11px; color: #7f8c8d; display: block;\">Consistency</span>\n",
        "                        <b style=\"font-size: 18px; color: #2980b9;\">{c[0]['num_runs']} Runs</b>\n",
        "                    </td>\n",
        "                </tr>\n",
        "            </table>\n",
        "        </div>\n",
        "\n",
        "        <table style=\"width: 100%; border-collapse: collapse;\">\n",
        "            <thead>\n",
        "                <tr style=\"background-color: #3498db; color: white;\">\n",
        "                    <th style=\"padding: 10px; border: 1px solid #ddd; text-align: left; font-size: 13px;\">Metric</th>\n",
        "                    <th style=\"padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;\">This Week</th>\n",
        "                    <th style=\"padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;\">Last Week</th>\n",
        "                    <th style=\"padding: 10px; border: 1px solid #ddd; text-align: center; font-size: 13px;\">2 Weeks Ago</th>\n",
        "                </tr>\n",
        "            </thead>\n",
        "            <tbody>\n",
        "                <tr>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Total Distance (km)</b><br><small style=\"color:#95a5a6; font-size:10px;\">Weekly volume</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[0]['distance']:.1f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[1]['distance']:.1f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[2]['distance']:.1f}</td>\n",
        "                </tr>\n",
        "                <tr style=\"background-color: #fcfcfc;\">\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Avg Pace</b><br><small style=\"color:#95a5a6; font-size:10px;\">min/km</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[0]['avg_pace']:.2f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[1]['avg_pace']:.2f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[2]['avg_pace']:.2f}</td>\n",
        "                </tr>\n",
        "                <tr>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Avg Heart Rate</b><br><small style=\"color:#95a5a6; font-size:10px;\">Cardio effort</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{int(c[0]['avg_hr'])}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{int(c[1]['avg_hr'])}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{int(c[2]['avg_hr'])}</td>\n",
        "                </tr>\n",
        "                <tr style=\"background-color: #fcfcfc;\">\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Stride Length (cm)</b><br><small style=\"color:#95a5a6; font-size:10px;\">Fatigue indicator</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[0]['stride']:.1f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[1]['stride']:.1f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[2]['stride']:.1f}</td>\n",
        "                </tr>\n",
        "                <tr>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Efficiency Score</b><br><small style=\"color:#95a5a6; font-size:10px;\">Dist per heart beat</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[0]['efficiency']:.3f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[1]['efficiency']:.3f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[2]['efficiency']:.3f}</td>\n",
        "                </tr>\n",
        "                <tr style=\"background-color: #fcfcfc;\">\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Load Ratio (ACWR)</b><br><small style=\"color:#95a5a6; font-size:10px;\">Injury prevention</small></td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: {acwr_color};\">{acwr_val:.2f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[1]['acwr']:.2f}</td>\n",
        "                    <td style=\"padding: 8px; border: 1px solid #ddd; text-align: center;\">{c[2]['acwr']:.2f}</td>\n",
        "                </tr>\n",
        "            </tbody>\n",
        "        </table>\n",
        "\n",
        "        <div style=\"margin-top: 25px; padding: 15px; background-color: #f0f7fd; border-left: 5px solid #3498db; border-radius: 8px;\">\n",
        "            <p style=\"margin: 0; font-size: 14px; color: #2c3e50; line-height: 1.5;\">\n",
        "                <b>🏃 Coach's Analysis:</b><br>\n",
        "                { \"Caution: High workload. Focus on active recovery.\" if acwr_val > 1.3\n",
        "                  else \"Maintenance: Low load. Good time for a speed session.\" if acwr_val < 0.8\n",
        "                  else \"Optimal: Training load is perfectly balanced. Keep it up!\" }\n",
        "            </p>\n",
        "        </div>\n",
        "    </div>\n",
        "    \"\"\"\n",
        "\n",
        "    msg = MIMEMultipart()\n",
        "    msg['Subject'] = f\"Weekly Running Analysis | {today.strftime('%d/%m/%Y')}\"\n",
        "    msg['From'] = SENDER\n",
        "    msg['To'] = RECEIVER\n",
        "    msg.attach(MIMEText(html_content, 'html'))\n",
        "\n",
        "    try:\n",
        "        with smtplib.SMTP_SSL(\"smtp.gmail.com\", 465) as server:\n",
        "            server.login(SENDER, PASSWORD)\n",
        "            server.send_message(msg)\n",
        "        print(\"✅ Full Professional Report (V5) sent successfully!\")\n",
        "    except Exception as e:\n",
        "        print(f\"❌ Error: {e}\")\n",
        "\n",
        "# הפעלה\n",
        "comp_data = get_weekly_comparison_v2(rebuilt_df)\n",
        "send_performance_report_v5(comp_data)"
      ],
      "metadata": {
        "colab": {
          "base_uri": "https://localhost:8080/"
        },
        "id": "RBJJ_jJ2tfxT",
        "outputId": "3f39ac28-0b65-41e4-cd71-51b40517b8f2"
      },
      "execution_count": 34,
      "outputs": [
        {
          "output_type": "stream",
          "name": "stdout",
          "text": [
            "✅ Full Professional Report (V5) sent successfully!\n"
          ]
        }
      ]
    }
  ]
}