import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime, time
import plotly.express as px

# ==========================================================
# CONFIG
# ==========================================================

st.set_page_config(
    page_title="HR Attendance System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================================
# FOLDERS
# ==========================================================

Path("daily-attendance").mkdir(exist_ok=True)
Path("leave-management").mkdir(exist_ok=True)

employee_file = "employee.csv"

# ==========================================================
# INIT EMPLOYEE FILE
# ==========================================================

if not os.path.exists(employee_file):
    pd.DataFrame({"Name": []}).to_csv(employee_file, index=False)

# ==========================================================
# STYLING
# ==========================================================

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

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.title("HR SYSTEM")

menu = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Attendance Reports", "Leave Management", "HR Analytics"]
)

# ==========================================================
# SAFE LOADERS
# ==========================================================

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


# ==========================================================
# 🔥 FIXED ATTENDANCE LOADER (IMPORTANT)
# ==========================================================

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

# ==========================================================
# DASHBOARD
# ==========================================================

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

# ==========================================================
# ATTENDANCE REPORTS
# ==========================================================

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


# ==========================================================
# LEAVE MANAGEMENT
# ==========================================================

elif menu == "Leave Management":

    st.markdown('<div class="title">LEAVE MANAGEMENT</div>', unsafe_allow_html=True)

    files = get_files("leave-management")

    if files:
        file = st.selectbox("Select File", files)
        df = pd.read_csv(os.path.join("leave-management", file))
        st.dataframe(df)
    else:
        st.warning("No leave data found")


# ==========================================================
# HR ANALYTICS
# ==========================================================

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
