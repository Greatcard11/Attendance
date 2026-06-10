import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime, time
import plotly.express as px

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Attendance System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# FOLDERS SETUP
# =========================================================

Path("daily-attendance").mkdir(exist_ok=True)
Path("leave-management").mkdir(exist_ok=True)

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

for month in MONTHS:
    Path(f"daily-attendance/{month}").mkdir(parents=True, exist_ok=True)

employee_file = "employee.csv"

if not os.path.exists(employee_file):
    pd.DataFrame({"Name": []}).to_csv(employee_file, index=False)
    # =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.stApp {
    background-color: white;
}

section[data-testid="stSidebar"] {
    background-color: black;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.title {
    color: #ff6b00;
    font-size: 34px;
    font-weight: bold;
}

.card {
    background: #ff6b00;
    padding: 15px;
    border-radius: 12px;
    color: white;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("NAVIGATION BAR")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Attendance Reports", "Leave Management", "HR Analytics"]
)

# =========================================================
# LOADERS
# =========================================================

def load_employees():
    df = pd.read_csv(employee_file)
    df.columns = df.columns.str.strip()

    if "Name" not in df.columns:
        df["Name"] = ""

    return df


def get_files(folder):
    if not os.path.exists(folder):
        return []

    return [
        f for f in os.listdir(folder)
        if isinstance(f, str) and f.endswith(".csv")
    ]


def load_attendance(file_path):
    df = pd.read_csv(file_path)

    df.columns = df.columns.str.strip().str.lower()

    df = df.rename(columns={
        "name": "Name",
        "time in": "Time in",
        "timein": "Time in",
        "clock in": "Time in",
        "time out": "Time out",
        "timeout": "Time out",
        "clock out": "Time out",
        "date (dd/mm/yy)": "Date"
    })

    return df
    # =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.markdown('<div class="title">ATTENDANCE DASHBOARD</div>', unsafe_allow_html=True)

    employees = load_employees()
    att_files = []
    leave_files = get_files("leave-management")

    for month in MONTHS:
        folder = f"daily-attendance/{month}"
        att_files.extend(get_files(folder))

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='card'><h2>{len(employees)}</h2><p>Employees</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h2>{len(att_files)}</h2><p>Attendance Files</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h2>{len(leave_files)}</h2><p>Leave Files</p></div>", unsafe_allow_html=True)

    st.subheader("Employees")
    st.dataframe(employees, use_container_width=True)


# =========================================================
# ATTENDANCE REPORTS
# =========================================================

elif menu == "Attendance Reports":

    st.markdown('<div class="title">ATTENDANCE REPORTS</div>', unsafe_allow_html=True)

    selected_month = st.selectbox("Select Month", MONTHS, index=datetime.today().month - 1)

    folder = f"daily-attendance/{selected_month}"
    files = get_files(folder)

    if not files:
        st.warning("No files found")
        st.stop()

    file = st.selectbox("Select File", files)

    path = os.path.join(folder, file)
    df = load_attendance(path)

    if not {"Name", "Time in", "Time out"}.issubset(df.columns):
        st.error("Missing required columns")
        st.stop()

    st.subheader("Attendance Data")
    st.dataframe(df, use_container_width=True)

    df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")
    df["Time out"] = pd.to_datetime(df["Time out"], errors="coerce")

    AFTERNOON_SHIFT = time(12, 0)

    df["Shift"] = np.where(
        df["Time in"].dt.time >= AFTERNOON_SHIFT,
        "Afternoon/Night",
        "Day"
    )

    late = df[df["Time in"].dt.time > time(8, 30)]
    overtime = df[df["Time out"].dt.time > time(18, 0)]

    st.subheader("Late Staff")
    st.dataframe(late, use_container_width=True)

    st.subheader("Overtime Staff")
    st.dataframe(overtime, use_container_width=True)


# =========================================================
# LEAVE MANAGEMENT
# =========================================================

elif menu == "Leave Management":

    st.markdown('<div class="title">LEAVE MANAGEMENT</div>', unsafe_allow_html=True)

    files = get_files("leave-management")

    if not files:
        st.warning("No leave data found")
        st.stop()

    file = st.selectbox("Select File", files)

    df = pd.read_csv(os.path.join("leave-management", file))

    st.dataframe(df, use_container_width=True)
    # =========================================================
# HR ANALYTICS
# =========================================================

elif menu == "HR Analytics":

    st.markdown('<div class="title">HR ANALYTICS</div>', unsafe_allow_html=True)

    employees = load_employees()
    st.metric("Total Employees", len(employees))

    att_files = []

    for month in MONTHS:
        folder = f"daily-attendance/{month}"

        if not os.path.exists(folder):
            continue

        for f in get_files(folder):
            att_files.append(os.path.join(folder, f))

    if not att_files:
        st.warning("No attendance data available")
        st.stop()

    all_data = []

    for path in att_files:

        try:
            df = load_attendance(path)

            if "Name" not in df.columns or "Time in" not in df.columns:
                continue

            df["Name"] = df["Name"].astype(str).str.strip()
            df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
            else:
                df["Date"] = df["Time in"].dt.date

            all_data.append(df)

        except:
            continue

    if not all_data:
        st.error("No valid data found")
        st.stop()

    df_all = pd.concat(all_data, ignore_index=True)

    df_all = df_all.dropna(subset=["Name", "Time in", "Date"])
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors="coerce")
    df_all = df_all.dropna(subset=["Date"])

    df_all["Month"] = df_all["Date"].dt.to_period("M").astype(str)

    selected = st.selectbox("Select Month", ["All"] + sorted(df_all["Month"].unique(), reverse=True))

    if selected != "All":
        df_all = df_all[df_all["Month"] == selected]

    df_all["Late"] = df_all["Time in"].dt.time > time(8, 30)

    summary = df_all.groupby("Name").agg(
        Total=("Name", "count"),
        Late=("Late", "sum"),
        OnTime=("Late", lambda x: (~x).sum())
    ).reset_index()

    summary["Punctuality (%)"] = (summary["OnTime"] / summary["Total"] * 100).round(2)

    summary = summary.sort_values("Punctuality (%)", ascending=False)

    st.dataframe(summary, use_container_width=True)

    fig = px.bar(summary.head(10), x="Name", y="Punctuality (%)")
    st.plotly_chart(fig, use_container_width=True)
