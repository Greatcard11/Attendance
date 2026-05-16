import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime, time
import plotly.express as px


# CONFIGURATION

st.set_page_config(
    page_title="HR Attendance System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# FOLDERS

Path("daily-attendance").mkdir(exist_ok=True)
Path("leave-management").mkdir(exist_ok=True)

employee_file = "employee.csv"

# INIT EMPLOYEE FILE

if not os.path.exists(employee_file):
    pd.DataFrame({"Name": []}).to_csv(employee_file, index=False)


# CSS

st.markdown("""
<style>
.stApp { background-color: white; }

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


# SIDEBAR NAVIGATION

st.sidebar.title("HR SYSTEM")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Attendance Reports", "Leave Management", "HR Analytics"]
)

# SAFE LOADERS

def load_employees():
    df = pd.read_csv(employee_file)
    df.columns = df.columns.str.strip()
    if "Name" not in df.columns:
        df["Name"] = ""
    return df


def save_employee(name):
    df = load_employees()
    df = pd.concat([df, pd.DataFrame({"Name": [name]})], ignore_index=True)
    df.to_csv(employee_file, index=False)


def get_files(folder):
    return [f for f in os.listdir(folder) if f.endswith(".csv")]


# ATTENDANCE LOADER 


def load_attendance(file_path):
    df = pd.read_csv(file_path)

    # CLEAN + LOWERCASE ALL COLUMNS
    df.columns = df.columns.str.strip().str.lower()

    # STANDARDIZE COLUMN NAMES
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

# DASHBOARD

if menu == "Dashboard":

    st.markdown('<div class="title">HR DASHBOARD</div>', unsafe_allow_html=True)

    employees = load_employees()

    att_files = get_files("daily-attendance")
    leave_files = get_files("leave-management")

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='card'><h2>{len(employees)}</h2><p>Employees</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h2>{len(att_files)}</h2><p>Attendance Files</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h2>{len(leave_files)}</h2><p>Leave Files</p></div>", unsafe_allow_html=True)


    employees = load_employees()

    # Reset index and start from 1
    employees.index = range(1, len(employees) + 1)
    employees.index.name = "S/N"

    st.subheader("Employees")
    st.dataframe(employees, use_container_width=True)


# ATTENDANCE REPORTS

elif menu == "Attendance Reports":

    st.markdown('<div class="title">ATTENDANCE REPORTS</div>', unsafe_allow_html=True)

    files = get_files("daily-attendance")

    if not files:
        st.warning("No attendance files found")
    else:

        file = st.selectbox("Select File", files)
        path = os.path.join("daily-attendance", file)

        df = load_attendance(path)

        # FINAL SAFETY CHECK
        required = ["Name", "Time in", "Time out"]
        missing = [c for c in required if c not in df.columns]

        if missing:
            st.error(f"Missing columns: {missing}")
            st.stop()

        # SAFE TIME CONVERSION
        df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")
        df["Time out"] = pd.to_datetime(df["Time out"], errors="coerce")

        employees = set(load_employees()["Name"].astype(str))
        attended = set(df["Name"].astype(str))

        late = df[df["Time in"].dt.time > time(8, 30)]
        overtime = df[df["Time out"].dt.time > time(19, 0)]
        absentees = pd.DataFrame({"Name": list(employees - attended)})

        st.subheader("Summary")

        c1, c2, c3 = st.columns(3)
        c1.metric("Late", len(late))
        c2.metric("Absent", len(absentees))
        c3.metric("Overtime", len(overtime))

        st.subheader("Latecomers")
        st.dataframe(late)

        st.subheader("Absentees")
        st.dataframe(absentees)

        st.subheader("Overtime")
        st.dataframe(overtime)

# LEAVE MANAGEMENT

elif menu == "Leave Management":

    st.markdown('<div class="title">LEAVE MANAGEMENT</div>', unsafe_allow_html=True)

    files = get_files("leave-management")

    if files:
        file = st.selectbox("Select File", files)
        df = pd.read_csv(os.path.join("leave-management", file))
        st.dataframe(df)
    else:
        st.warning("No leave data found")

# HR ANALYTICS

elif menu == "HR Analytics":

    st.markdown('<div class="title">HR ANALYTICS</div>', unsafe_allow_html=True)

    employees = load_employees()

    st.metric("Total Employees", len(employees))
    emp_counts = employees["Name"].value_counts().reset_index()
    emp_counts.columns = ["Name", "Count"]

    fig = px.bar(
    emp_counts,
    x="Name",
    y="Count",
    title="Employee Distribution"
    )
    
    st.plotly_chart(fig, use_container_width=True)

# TOP 10 MOST PUNCTUAL EMPLOYEES

att_files = get_files("daily-attendance")

if not att_files:
    st.warning("No attendance data available for analytics")
else:
    all_data = []

    # Load and combine all attendance files
    for file in att_files:
        path = os.path.join("daily-attendance", file)
        df = load_attendance(path)

        if "Name" in df.columns and "Time in" in df.columns:
            df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")
            all_data.append(df)

    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)

        # Define punctuality (on or before 8:30 AM)
        punctual_df = df_all[df_all["Time in"].dt.time <= time(8, 30)]

        # Count punctual days per employee
        punctual_counts = (
            punctual_df["Name"]
            .value_counts()
            .reset_index()
        )

        punctual_counts.columns = ["Name", "Punctual Days"]

        # Get top 10
        top_10 = punctual_counts.head(10)

        st.subheader("🏆 Top 10 Most Punctual Employees")
        st.dataframe(top_10, use_container_width=True)

        # Optional: Visualization
        fig = px.bar(
            top_10,
            x="Name",
            y="Punctual Days",
            title="Top 10 Most Punctual Employees"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No valid attendance data found")


# ADVANCED PUNCTUALITY ANALYTICS


att_files = get_files("daily-attendance")

if not att_files:
    st.warning("No attendance data available for analytics")
else:
    all_data = []

    for file in att_files:
        path = os.path.join("daily-attendance", file)
        df = load_attendance(path)

        if "Name" in df.columns and "Time in" in df.columns:
            df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")

            # Extract date if not already present
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            else:
                df["Date"] = pd.to_datetime("today")

            all_data.append(df)

    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)

        # Remove invalid rows
        df_all = df_all.dropna(subset=["Name", "Time in"])

        # =========================
        # DEFINE RULES
        # =========================
        ON_TIME = time(8, 30)
        LATE_LIMIT = time(9, 0)

        # Categorize attendance
        df_all["Status"] = np.where(
            df_all["Time in"].dt.time <= ON_TIME, "On Time",
            np.where(df_all["Time in"].dt.time <= LATE_LIMIT, "Late", "Very Late")
        )

        # =========================
        # SCORE SYSTEM
        # =========================
        score_map = {
            "On Time": 1,
            "Late": -0.5,
            "Very Late": -1
        }

        df_all["Score"] = df_all["Status"].map(score_map)

        # =========================
        # EMPLOYEE SUMMARY
        # =========================
        summary = df_all.groupby("Name").agg(
            Total_Days=("Name", "count"),
            On_Time_Days=("Status", lambda x: (x == "On Time").sum()),
            Late_Days=("Status", lambda x: (x == "Late").sum()),
            Very_Late_Days=("Status", lambda x: (x == "Very Late").sum()),
            Total_Score=("Score", "sum")
        ).reset_index()

        # Punctuality %
        summary["Punctuality (%)"] = (
            summary["On_Time_Days"] / summary["Total_Days"] * 100
        ).round(2)

        # Rank by Score (penalized ranking)
        summary = summary.sort_values(by="Total_Score", ascending=False)

        # =========================
        # TOP 10 LEADERBOARD
        # =========================
        st.subheader("🏆 Overall Leaderboard (Top 10)")
        st.dataframe(summary.head(10), use_container_width=True)

        # Chart
        fig = px.bar(
            summary.head(10),
            x="Name",
            y="Total_Score",
            title="Top 10 Employees by Punctuality Score"
        )
        st.plotly_chart(fig, use_container_width=True)

        # =========================
        # MONTHLY LEADERBOARD
        # =========================
        df_all["Month"] = df_all["Date"].dt.to_period("M").astype(str)

        selected_month = st.selectbox(
            "Select Month for Ranking",
            sorted(df_all["Month"].dropna().unique())
        )

        monthly_df = df_all[df_all["Month"] == selected_month]

        monthly_summary = monthly_df.groupby("Name").agg(
            Total_Days=("Name", "count"),
            On_Time_Days=("Status", lambda x: (x == "On Time").sum()),
            Total_Score=("Score", "sum")
        ).reset_index()

        monthly_summary["Punctuality (%)"] = (
            monthly_summary["On_Time_Days"] / monthly_summary["Total_Days"] * 100
        ).round(2)

        monthly_summary = monthly_summary.sort_values(
            by="Total_Score", ascending=False
        )

        st.subheader(f"📅 Monthly Leaderboard ({selected_month})")
        st.dataframe(monthly_summary.head(10), use_container_width=True)

    else:
        st.warning("No valid attendance data found")
