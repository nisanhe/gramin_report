# Garmin Running Analytics Pipeline 🏃‍♂️📊

An automated data engineering pipeline that fetches running metrics from Garmin Connect, calculates advanced training loads (ACWR), and dispatches a weekly performance report via email.

## 📁 Architecture
- **Data Source:** Garmin Connect Cloud API.
- **Orchestration:** GitHub Actions (Scheduled CRON).
- **Database:** Flat-file CSV (`data/garmin_runs.csv`) versioned within the repository.
- **Compute:** Python 3.9 (Pandas, Numpy, GarminConnect).

## 🚀 Key Metrics Tracked
* **ACWR (Acute:Chronic Workload Ratio):** Monitors injury risk by comparing 7-day vs. 28-day strain.
* **Efficiency Score:** Distance covered per heartbeat.
* **Biometrics:** Stride length, Cadence, and Heart Rate zones.
* **Elevation:** Total weekly climb and descent.

## 🛠 Setup & Automation
The pipeline is triggered every Sunday at 06:00 UTC via GitHub Actions.
It performs a "Delta Sync"—only fetching activities since the last recorded entry to optimize performance.
