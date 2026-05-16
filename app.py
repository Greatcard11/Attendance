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
# FOLDERS
# =========================================================

Path("daily-attendance").mkdir(exist_ok=True)
Path("leave-management").mkdir(exist_ok=True)

employee_file = "employee.csv"


# =========================================================
# INIT EMPLOYEE FILE
# =========================================================

if not os.path.exists(employee_file):
    pd.DataFrame({"Name": []}).to_csv(employee_file, index=False)


# =========================================================
# CSS
# =========================================================

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


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("NAVIGATION BAR")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Attendance Reports",
        "Leave Management",
        "HR Analytics"
    ]
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
    return [f for f in os.listdir(folder) if f.endswith(".csv")]


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
# DASHBOARD (ONLY SUMMARY)
# =========================================================

if menu == "Dashboard":

    st.markdown('<div class="title">HR DASHBOARD</div>', unsafe_allow_html=True)

    employees = load_employees()
    att_files = get_files("daily-attendance")
    leave_files = get_files("leave-management")

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<div class='card'><h2>{len(employees)}</h2><p>Employees</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h2>{len(att_files)}</h2><p>Attendance Files</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><h2>{len(leave_files)}</h2><p>Leave Files</p></div></div>", unsafe_allow_html=True)

    employees.index = range(1, len(employees) + 1)
    employees.index.name = "S/N"

    st.subheader("Employees")
    st.dataframe(employees, use_container_width=True)

# =========================================================
# ATTENDANCE REPORTS (DAILY ANALYTICS ONLY)
# =========================================================

elif menu == "Attendance Reports":

    st.markdown('<div class="title">ATTENDANCE REPORTS</div>', unsafe_allow_html=True)

    files = get_files("daily-attendance")

    if not files:
        st.warning("No attendance files found")

    else:

        file = st.selectbox("Select File", files)
        path = os.path.join("daily-attendance", file)

        df = load_attendance(path)

        required = ["Name", "Time in", "Time out"]
        if any(c not in df.columns for c in required):
            st.error("Missing required columns")
            st.stop()

        # =====================================================
        # RAW ATTENDANCE FIRST
        # =====================================================

        st.subheader("📋 Attendance List")
        st.dataframe(df, use_container_width=True)

        # =====================================================
        # TIME CONVERSION
        # =====================================================

        df["Time in"] = pd.to_datetime(df["Time in"], errors="coerce")
        df["Time out"] = pd.to_datetime(df["Time out"], errors="coerce")

        # =====================================================
        # REPORT DATE FIX
        # =====================================================

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            report_date = df["Date"].dropna().iloc[0].date()
        else:
            report_date = datetime.today().date()

        # =====================================================
        # SHIFT LOGIC
        # =====================================================

        NIGHT_SHIFT_START = time(17, 0)

        df["Shift"] = np.where(
            df["Time in"].dt.time >= NIGHT_SHIFT_START,
            "Night Shift",
            "Day Shift"
        )

        # =====================================================
        # DAILY LATE
        # =====================================================

        late = df[
            (df["Shift"] == "Day Shift") &
            (df["Time in"].dt.time > time(8, 30))
        ]

        # =====================================================
        # OVERTIME
        # =====================================================

        overtime = df[
            ((df["Shift"] == "Day Shift") & (df["Time out"].dt.time > time(19, 0))) |
            ((df["Shift"] == "Night Shift") & (df["Time out"].dt.time > time(8, 0)))
        ]

        # =====================================================
        # LEAVE EXCLUSION
        # =====================================================

        staff_on_leave = set()
        leave_files = get_files("leave-management")

        for lf in leave_files:
            leave_df = pd.read_csv(os.path.join("leave-management", lf))

            if {"Name","Start Date","End Date","Status"}.issubset(leave_df.columns):

                leave_df["Start Date"] = pd.to_datetime(leave_df["Start Date"]).dt.date
                leave_df["End Date"] = pd.to_datetime(leave_df["End Date"]).dt.date

                approved = leave_df[
                    (leave_df["Status"].str.lower().str.strip() == "approved") &
                    (leave_df["Start Date"] <= report_date) &
                    (leave_df["End Date"] >= report_date)
                ]

                staff_on_leave.update(approved["Name"].astype(str))

        # =====================================================
        # ABSENTEES
        # =====================================================

        employees = set(load_employees()["Name"].astype(str))
        attended = set(df["Name"].astype(str))

        absentees = pd.DataFrame({
            "Name": list(employees - attended - staff_on_leave)
        })

        # =====================================================
        # SUMMARY
        # =====================================================

        st.subheader("Summary")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Late", len(late))
        c2.metric("Absent", len(absentees))
        c3.metric("Overtime", len(overtime))
        c4.metric("Night Shift", len(df[df["Shift"] == "Night Shift"]))

        st.subheader("Latecomers")
        st.dataframe(late, use_container_width=True)

        st.subheader("Night Shift Staff")
        st.dataframe(df[df["Shift"] == "Night Shift"], use_container_width=True)

        st.subheader("Absentees")
        st.dataframe(absentees, use_container_width=True)

        st.subheader("Overtime")
        st.dataframe(overtime, use_container_width=True)

# =========================================================
# LEAVE MANAGEMENT
# =========================================================

elif menu == "Leave Management":

    st.markdown('<div class="title">LEAVE MANAGEMENT</div>', unsafe_allow_html=True)

    files = get_files("leave-management")

    if files:
        file = st.selectbox("Select File", files)
        df = pd.read_csv(os.path.join("leave-management", file))
        st.dataframe(df)
    else:
        st.warning("No leave data found")



# HR ANALYTICS (MONTHLY ONLY)
# =======================================

elif menu == "HR Analytics":

    st.markdown(
        '<div class="title">HR ANALYTICS</div>',
        unsafe_allow_html=True
    )

    employees = load_employees()

    st.metric(
        "Total Employees",
        len(employees)
    )

    emp_counts = (
        employees["Name"]
        .value_counts()
        .reset_index()
    )

    emp_counts.columns = ["Name", "Count"]

    fig = px.bar(
        emp_counts,
        x="Name",
        y="Count",
        title="Employee Distribution"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =====================================================
    # MONTHLY ATTENDANCE ANALYTICS ONLY


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

                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                else:
                    df["Date"] = pd.to_datetime("today")

                all_data.append(df)

        if all_data:

            df_all = pd.concat(all_data, ignore_index=True)

            df_all = df_all.dropna(subset=["Name", "Time in"])

            # =====================================================
            # MONTHLY GROUPING ONLY
            # =====================================================

            df_all["Month"] = df_all["Date"].dt.to_period("M").astype(str)

            monthly_summary = df_all.groupby("Name").agg(
                Total_Days=("Name", "count"),
                On_Time_Days=("Time in", lambda x: (x.dt.time <= time(8, 30)).sum())
            ).reset_index()

            monthly_summary["Punctuality (%)"] = (
                monthly_summary["On_Time_Days"] /
                monthly_summary["Total_Days"] * 100
            ).round(2)

            monthly_summary = monthly_summary.sort_values(
                by="Punctuality (%)",
                ascending=False
            )

            st.subheader("📅 Monthly Performance Ranking")

            st.dataframe(monthly_summary, use_container_width=True)

            fig = px.bar(
                monthly_summary.head(10),
                x="Name",
                y="Punctuality (%)",
                title="Top Monthly Performers"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("No valid attendance data found")
