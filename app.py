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
# =========================================================
# FOLDERS
# =========================================================

Path("daily-attendance").mkdir(exist_ok=True)
Path("leave-management").mkdir(exist_ok=True)

MONTHS = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

for month in MONTHS:
    Path(
        f"daily-attendance/{month}"
    ).mkdir(
        parents=True,
        exist_ok=True
    )

employee_file = "employee.csv"


# =========================================================
# INIT EMPLOYEE FILE
# =========================================================

if not os.path.exists(employee_file):
    pd.DataFrame({"Name": []}).to_csv(
        employee_file,
        index=False
    )


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

    df.columns = (
        df.columns
        .str.strip()
    )

    if "Name" not in df.columns:
        df["Name"] = ""

    return df


def get_files(folder):
    return [
        f for f in os.listdir(folder)
        if f.endswith(".csv")
    ]


def load_attendance(file_path):

    df = pd.read_csv(file_path)

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

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

    st.markdown(
        '<div class="title">ATTENDANCE DASHBOARD</div>',
        unsafe_allow_html=True
    )

    employees = load_employees()
    att_files = get_files("daily-attendance")
    leave_files = get_files("leave-management")

    c1, c2, c3 = st.columns(3)

    c1.markdown(
        f"""
        <div class='card'>
            <h2>{len(employees)}</h2>
            <p>Employees</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c2.markdown(
        f"""
        <div class='card'>
            <h2>{len(att_files)}</h2>
            <p>Attendance Files</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c3.markdown(
        f"""
        <div class='card'>
            <h2>{len(leave_files)}</h2>
            <p>Leave Files</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    employees.index = range(
        1,
        len(employees) + 1
    )

    employees.index.name = "S/N"

    st.subheader("Employees")

    st.dataframe(
        employees,
        use_container_width=True
    )


# =========================================================
# ATTENDANCE REPORTS
# =========================================================

elif menu == "Attendance Reports":

    st.markdown(
        '<div class="title">ATTENDANCE REPORTS</div>',
        unsafe_allow_html=True
    )

    selected_month = st.selectbox(
        "Select Month",
        MONTHS,
        index=datetime.today().month - 1
    )

    attendance_folder = os.path.join(
        "daily-attendance",
        selected_month
    )

    files = get_files(
        attendance_folder
    )

        file = st.selectbox(
            "Select File",
            files
        )

        path = os.path.join(
            attendance_folder,
            file
        )

        df = load_attendance(path)

        required = [
            "Name",
            "Time in",
            "Time out"
        ]

        if any(
            c not in df.columns
            for c in required
        ):
            st.error(
                "Missing required columns"
            )
            st.stop()

        st.subheader(
            "📋 Attendance List"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

        # =====================================================
        # TIME CONVERSIONS
        # =====================================================

        df["Time in"] = pd.to_datetime(
            df["Time in"],
            errors="coerce"
        )

        df["Time out"] = pd.to_datetime(
            df["Time out"],
            errors="coerce"
        )

        # =====================================================
        # DATE
        # =====================================================

        if "Date" in df.columns:

            df["Date"] = pd.to_datetime(
                df["Date"],
                errors="coerce"
            )

            report_date = (
                df["Date"]
                .dropna()
                .iloc[0]
                .date()
            )

        else:
            report_date = (
                datetime.today()
                .date()
            )

        
        # =====================================================
        # SHIFT
        # =====================================================

        AFTERNOON_NIGHT_SHIFT_START = time(12, 0, 0)

        df["Shift"] = np.where(
            df["Time in"].dt.time >= AFTERNOON_NIGHT_SHIFT_START,
            "Afternoon/Night Shift",
            "Day Shift"
        )
        

        # =====================================================
        # LATE STAFF
        # =====================================================

        late = df[
            (
                df["Shift"]
                == "Day Shift"
            )
            &
            (
                df["Time in"]
                .dt.time
                > time(8, 30)
            )
        ]

        # =====================================================
        # OVERTIME
        # =====================================================

        overtime = df[
        (
            df["Shift"]
            == "Day Shift"
        )
        &
        (
            df["Time out"]
            .dt.time
            > time(18, 0)
        )
        ]

        # =====================================================
        # LEAVE FILES
        # =====================================================

        staff_on_leave = set()

        leave_files = get_files(
            "leave-management"
        )

        for lf in leave_files:

            leave_df = pd.read_csv(
                os.path.join(
                    "leave-management",
                    lf
                )
            )

            if {
                "Name",
                "Start Date",
                "End Date",
                "Status"
            }.issubset(
                leave_df.columns
            ):

                leave_df["Start Date"] = (
                    pd.to_datetime(
                        leave_df["Start Date"]
                    ).dt.date
                )

                leave_df["End Date"] = (
                    pd.to_datetime(
                        leave_df["End Date"]
                    ).dt.date
                )

                approved = leave_df[
                    (
                        leave_df["Status"]
                        .str.lower()
                        .str.strip()
                        == "approved"
                    )
                    &
                    (
                        leave_df["Start Date"]
                        <= report_date
                    )
                    &
                    (
                        leave_df["End Date"]
                        >= report_date
                    )
                ]

                staff_on_leave.update(
                    approved["Name"]
                    .astype(str)
                )
        # =====================================================
        # ABSENTEES
        # ONLY STAFF WITHOUT TIME IN = ABSENT
        # =====================================================

        employees_df = load_employees()

        # Clean employee names
        employees_df["Name"] = (
            employees_df["Name"]
            .astype(str)
            .str.strip()
        )

        # Clean attendance names
        df["Name"] = (
            df["Name"]
            .astype(str)
            .str.strip()
        )

        # Ensure Time in is datetime
        df["Time in"] = pd.to_datetime(
            df["Time in"],
            errors="coerce"
        )

        # =====================================================
        # STAFF ON APPROVED LEAVE
        # =====================================================

        staff_on_leave = set(
            pd.Series(
                list(staff_on_leave)
            )
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # =====================================================
        # STAFF WITH VALID TIME IN = PRESENT
        # =====================================================

        present_staff = set(
            df[
                df["Time in"].notna()
            ]["Name"]
            .astype(str)
            .str.strip()
            .str.lower()
            .unique()
        )

        # =====================================================
        # ALL EMPLOYEES
        # =====================================================

        all_staff = set(
            employees_df["Name"]
            .astype(str)
            .str.strip()
            .str.lower()
            .unique()
        )

        # =====================================================
        # ABSENTEES
        # NO TIME IN = ABSENT
        # EXCLUDING APPROVED LEAVE
        # =====================================================

        absent_names = (
            all_staff
            - present_staff
            - staff_on_leave
        )

        # =====================================================
        # DISPLAY ABSENTEES
        # =====================================================

        absentees = employees_df[
            employees_df["Name"]
            .str.strip()
            .str.lower()
            .isin(absent_names)
        ][["Name"]].drop_duplicates()

        absentees.reset_index(
            drop=True,
            inplace=True
        )

        # =====================================================
        # SUMMARY
        # =====================================================

        st.subheader("Summary")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Late",
            len(late)
        )

        c2.metric(
            "Absent",
            len(absentees)
        )

        c3.metric(
            "Overtime",
            len(overtime)
        )

        c4.metric(
            "Afternoon/Night Shift",
            len(
                df[
                    df["Shift"]
                    == "Afternoon/Night Shift"
                ]
            )
        )

        # =====================================================
        # TABLES
        # =====================================================

        st.subheader(
            "Latecomers"
        )

        st.dataframe(
            late,
            use_container_width=True
        )

        st.subheader(
            "Afternoon/Night Shift"
        )

        st.dataframe(
            df[
                df["Shift"]
                == "Afternoon/Night Shift"
            ],
            use_container_width=True
        )

        st.subheader(
            "Absentees"
        )

        st.dataframe(
            absentees,
            use_container_width=True
        )

        st.subheader(
            "Overtime"
        )

        st.dataframe(
            overtime,
            use_container_width=True
        )


# =========================================================
# LEAVE MANAGEMENT
# =========================================================

elif menu == "Leave Management":

    st.markdown(
        '<div class="title">LEAVE MANAGEMENT</div>',
        unsafe_allow_html=True
    )

    files = get_files(
        "leave-management"
    )

    if files:

        file = st.selectbox(
            "Select File",
            files
        )

        df = pd.read_csv(
            os.path.join(
                "leave-management",
                file
            )
        )

        st.dataframe(
            df,
            use_container_width=True
        )

    else:
        st.warning(
            "No leave data found"
        )


# =========================================================
# HR ANALYTICS
# =========================================================

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

    # =====================================================
    # LOAD ATTENDANCE FILES
    # =====================================================

    att_files = []

for month in MONTHS:
    month_folder = os.path.join(
    "daily-attendance",
    month
    )

    att_files.extend(
        get_files(month_folder)
    )

    if not att_files:
        st.warning(
            "No attendance data available"
        )

    else:

        all_data = []

        for file in att_files:

            path = os.path.join(
                "daily-attendance",
                file
            )

            try:

                df = load_attendance(
                    path
                )

                # Ensure required columns exist
                if (
                    "Name"
                    not in df.columns
                    or
                    "Time in"
                    not in df.columns
                ):
                    continue

                # Clean employee names
                df["Name"] = (
                    df["Name"]
                    .astype(str)
                    .str.strip()
                )

                # Remove empty names
                df = df[
                    df["Name"]
                    .notna()
                ]

                # Convert Time in
                df["Time in"] = (
                    pd.to_datetime(
                        df["Time in"],
                        errors="coerce"
                    )
                )

                # FIXED: Proper Date handling (this is what was breaking May data)
                if "Date" in df.columns:

                    df["Date"] = pd.to_datetime(
                        df["Date"],
                        errors="coerce",
                        dayfirst=True
                    )

                else:

                    # fallback: try to extract from file name or use Time in date
                    df["Date"] = pd.to_datetime(
                        df["Time in"],
                        errors="coerce"
                    ).dt.date

                all_data.append(df)

            except Exception as e:

                st.warning(
                    f"Could not read {file}: {e}"
                )

        # =====================================================
        # CHECK DATA EXISTS
        # =====================================================

        if len(all_data) == 0:

            st.error(
                "No valid attendance data found"
            )

        else:

            df_all = pd.concat(
                all_data,
                ignore_index=True
            )

            # Remove invalid records
            df_all = df_all.dropna(
                subset=[
                    "Name",
                    "Time in",
                    "Date"
                ]
            )

            if df_all.empty:

                st.error(
                    "Attendance data loaded but Time in column is invalid."
                )

                st.stop()

            # ENSURE DATE IS DATETIME (CRITICAL FIX)
            df_all["Date"] = pd.to_datetime(
                df_all["Date"],
                errors="coerce"
            )

            df_all = df_all.dropna(subset=["Date"])

            # =====================================================
            # MONTH COLUMN
            # =====================================================

            df_all["Month"] = (
                df_all["Date"]
                .dt.to_period("M")
                .astype(str)
            )

            # =====================================================
            # MONTH FILTER
            # =====================================================

            available_months = sorted(
                df_all["Month"].dropna().unique(),
                reverse=True
            )

            selected_month = st.selectbox(
                "Select Month",
                ["All"] + available_months
            )

            if selected_month != "All":
                df_all = df_all[df_all["Month"] == selected_month]

            # =====================================================
            # LATE CALCULATION
            # =====================================================

            LATE_TIME = time(
                8,
                30
            )

            df_all["Late"] = (
                df_all["Time in"]
                .dt.time
                > LATE_TIME
            )

            # =====================================================
            # MONTHLY SUMMARY
            # =====================================================

            monthly_summary = (
                df_all
                .groupby("Name")
                .agg(
                    Total_Days=(
                        "Name",
                        "count"
                    ),
                    Late_Count=(
                        "Late",
                        "sum"
                    ),
                    On_Time_Days=(
                        "Late",
                        lambda x: (
                            ~x
                        ).sum()
                    )
                )
                .reset_index()
            )

            monthly_summary[
                "Punctuality (%)"
            ] = (
                monthly_summary[
                    "On_Time_Days"
                ]
                /
                monthly_summary[
                    "Total_Days"
                ]
                * 100
            ).round(2)

            monthly_summary = (
                monthly_summary
                .sort_values(
                    by="Punctuality (%)",
                    ascending=False
                )
            )

            # =====================================================
            # DASHBOARD METRICS
            # =====================================================

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Employees Tracked",
                len(
                    monthly_summary
                )
            )

            c2.metric(
                "Total Late Records",
                int(
                    monthly_summary[
                        "Late_Count"
                    ].sum()
                )
            )

            c3.metric(
                "Late > 5 Times",
                len(
                    monthly_summary[
                        monthly_summary[
                            "Late_Count"
                        ] > 5
                    ]
                )
            )

            # =====================================================
            # PERFORMANCE TABLE
            # =====================================================

            st.subheader(
                "📅 Monthly Performance Ranking"
            )

            st.dataframe(
                monthly_summary,
                use_container_width=True
            )

            # =====================================================
            # TOP PERFORMERS
            # =====================================================

            fig = px.bar(
                monthly_summary.head(10),
                x="Name",
                y="Punctuality (%)",
                title="Top Monthly Performers",
                color="Punctuality (%)",
                color_continuous_scale="Blues"
            )

            st.plotly_chart(fig, use_container_width=True)

            # =====================================================
            # STAFF LATE > 5 TIMES
            # =====================================================

            late_staff = (
                monthly_summary[
                    monthly_summary[
                        "Late_Count"
                    ] > 5
                ]
            )

            st.subheader(
                "⚠ Employees Late More Than 5 Times"
            )

            if late_staff.empty:

                st.success(
                    "No employee has been late more than 5 times."
                )

            else:

                st.dataframe(
                    late_staff[
                        [
                            "Name",
                            "Late_Count",
                            "Punctuality (%)"
                        ]
                    ],
                    use_container_width=True
                )

                fig = px.bar(
                    late_staff,
                    x="Name",
                    y="Late_Count",
                    title="Late More Than 5 Times",
                    color="Late_Count",
                    color_continuous_scale="Reds"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )
