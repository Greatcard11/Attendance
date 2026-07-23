import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from datetime import datetime, time
import os

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Analytics System",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── THEME ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main .block-container { background-color: #ffffff; padding-top: 1.5rem; }
section[data-testid="stSidebar"] { background-color: #111111 !important; }
section[data-testid="stSidebar"] * { color: #f0f0f0 !important; }
section[data-testid="stSidebar"] .stRadio label { color: #f0f0f0 !important; font-size: 0.95rem; }
section[data-testid="stSidebar"] hr { border-color: #333 !important; }
.stButton > button { background-color: #ff6b00; color: white; border: none; border-radius: 6px; }
.stButton > button:hover { background-color: #e05a00; }
.kpi-card { background: #fff; border: 1px solid #f0f0f0; border-left: 4px solid #ff6b00;
    border-radius: 8px; padding: 1.2rem 1.4rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.kpi-card .kpi-value { font-size: 2rem; font-weight: 700; color: #ff6b00; line-height: 1.1; }
.kpi-card .kpi-label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: #888; margin-top: 0.25rem; }
.section-header { font-size: 1.1rem; font-weight: 600; color: #111;
    border-bottom: 2px solid #ff6b00; padding-bottom: 0.3rem; margin: 1.5rem 0 0.75rem; }
.info-box { background: #fff8f3; border: 1px solid #ffd6b3; border-radius: 6px;
    padding: 0.75rem 1rem; color: #8a3300; font-size: 0.9rem; }
.warn-box { background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;
    padding: 0.75rem 1rem; color: #664d03; font-size: 0.9rem; }
.page-title { font-size: 1.6rem; font-weight: 700; color: #111; margin-bottom: 0.25rem; }
.page-subtitle { color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── DIRECTORIES ────────────────────────────────────────────────────────────
BASE_DIR  = Path(".")
DAILY_DIR = BASE_DIR / "daily-attendance"
LEAVE_DIR = BASE_DIR / "leave-management"
EMP_CSV   = BASE_DIR / "employee.csv"
DAILY_DIR.mkdir(exist_ok=True)
LEAVE_DIR.mkdir(exist_ok=True)

MONTH_ORDER = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

# ════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS  (all defined before any page code)
# ════════════════════════════════════════════════════════════════════════════

def kpi(label, value, col):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>""", unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

def load_employees():
    if EMP_CSV.exists():
        df = pd.read_csv(EMP_CSV)
        df.columns = df.columns.str.strip()
        name_col = next((c for c in df.columns if c.lower() == "name"), None)
        if name_col:
            df = df.rename(columns={name_col: "Name"})
            df["Name"] = df["Name"].str.strip()
            df = df.drop_duplicates(subset="Name")
            return df
    return pd.DataFrame(columns=["Name"])

def normalize_attendance(df):
    """Normalize column names → Name / Time_in / Time_out / Date."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rename_map   = {}
    used_targets = set()

    def try_map(col, target):
        if target not in used_targets:
            rename_map[col] = target
            used_targets.add(target)

    for col in df.columns:
        low = col.lower().replace(" ", "_").replace("-", "_")
        if "name" in low and "Name" not in used_targets:
            try_map(col, "Name")
        elif ("time_out" in low or low in ("timeout","out_time","check_out","checkout")) and "Time_out" not in used_targets:
            try_map(col, "Time_out")
        elif ("time_in" in low or low in ("timein","in_time","check_in","checkin")) and "Time_in" not in used_targets:
            try_map(col, "Time_in")
        elif "date" in low and "Date" not in used_targets:
            try_map(col, "Date")

    df = df.rename(columns=rename_map)

    if "Name" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Name"})
    cols = list(df.columns)
    if "Time_in"  not in cols and len(cols) > 1: df = df.rename(columns={cols[1]: "Time_in"});  cols = list(df.columns)
    if "Time_out" not in cols and len(cols) > 2: df = df.rename(columns={cols[2]: "Time_out"}); cols = list(df.columns)
    if "Date"     not in cols and len(cols) > 3: df = df.rename(columns={cols[3]: "Date"})

    df["Name"] = df["Name"].astype(str).str.strip()
    df = df[~df["Name"].str.lower().isin(["nan","none","","name"])]
    df = df.dropna(subset=["Name"])

    if "Date"     in df.columns: df["Date"]       = pd.to_datetime(df["Date"],     errors="coerce")
    if "Time_in"  in df.columns: df["Time_in_dt"] = pd.to_datetime(df["Time_in"].astype(str).str.strip(),  errors="coerce")
    if "Time_out" in df.columns: df["Time_out_dt"]= pd.to_datetime(df["Time_out"].astype(str).str.strip(), errors="coerce")
    return df

def get_approved_leaves():
    approved = set()
    for f in LEAVE_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(f)
            df.columns = df.columns.str.strip()
            name_col   = next((c for c in df.columns if "name"   in c.lower()), None)
            date_col   = next((c for c in df.columns if "date"   in c.lower()), None)
            status_col = next((c for c in df.columns if "status" in c.lower()), None)
            if not name_col or not date_col: continue
            for _, row in df.iterrows():
                status = str(row.get(status_col,"approved")).strip().lower() if status_col else "approved"
                if status == "approved":
                    name = str(row[name_col]).strip().lower()
                    date = pd.to_datetime(row[date_col], errors="coerce")
                    if pd.notna(date):
                        approved.add((name, date.date()))
        except Exception:
            pass
    return approved

def is_rainy_day(filename):
    return "rainy day" in filename.lower()

def fmt_date(d):
    """Format a date/Timestamp as dd/mm/yy."""
    try:
        return pd.Timestamp(d).strftime("%d/%m/%y")
    except Exception:
        return str(d)

def fmt_df_dates(df, cols):
    """Return a copy of df with specified date columns formatted as dd/mm/yy strings."""
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda d: fmt_date(d) if pd.notna(d) else "")
    return df

def get_all_attendance_files():
    files = []
    for sub in sorted(DAILY_DIR.iterdir()):
        if sub.is_dir():
            files.extend(sorted(sub.glob("*.csv")))
    if not files:
        files = sorted(DAILY_DIR.glob("*.csv"))
    return files

def get_month_folders():
    return sorted(
        [d.name for d in DAILY_DIR.iterdir() if d.is_dir()],
        key=lambda m: MONTH_ORDER.index(m) if m in MONTH_ORDER else 99
    )

def show_toggle(df, x_col, y_col, title, key,
                color_scale=None, orient="h", text_fmt=None):
    """Render a Table | Bar Chart toggle for any dataframe."""
    if df is None or df.empty:
        st.info("No data to display.")
        return
    view = st.radio("View as", ["📋 Table", "📊 Bar Chart"],
                    horizontal=True, key=key)
    if view == "📋 Table":
        disp = df.reset_index(drop=True).copy()
        disp.index += 1
        st.dataframe(disp, use_container_width=True)
    else:
        scale = color_scale or [[0,"#ff6b00"],[0.5,"#ffaa55"],[1,"#22c55e"]]
        if orient == "h":
            plot_df = df.sort_values(y_col, ascending=True)
            fig = px.bar(plot_df, x=y_col, y=x_col, orientation="h",
                         color=y_col, color_continuous_scale=scale,
                         text=y_col, labels={y_col: title, x_col: "Employee"})
        else:
            plot_df = df.sort_values(y_col, ascending=False)
            fig = px.bar(plot_df, x=x_col, y=y_col,
                         color=y_col, color_continuous_scale=scale,
                         text=y_col, labels={y_col: title, x_col: "Employee"})
        if text_fmt:
            fig.update_traces(texttemplate=text_fmt, textposition="outside")
        else:
            fig.update_traces(textposition="outside")
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            coloraxis_showscale=False,
            height=max(320, len(df) * 34),
            margin=dict(l=0, r=30, t=10, b=60)
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👥 HR System")
    st.markdown("---")
    page = st.radio("Navigation",
                    ["Dashboard","Attendance Reports","Leave Management","HR Analytics"],
                    label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<small style='color:#555'>Cardstel Solutions Limited</small>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown('<div class="page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Overview of employee and attendance data</div>', unsafe_allow_html=True)

    emp_df     = load_employees()
    att_files  = get_all_attendance_files()
    leave_files= list(LEAVE_DIR.glob("*.csv"))

    c1, c2, c3 = st.columns(3)
    kpi("Total Employees",        len(emp_df),       c1)
    kpi("Total Attendance Files", len(att_files),    c2)
    kpi("Total Leave Files",      len(leave_files),  c3)

    section("Employee Master List")
    if emp_df.empty:
        st.markdown('<div class="info-box">No employee data found. Add <b>employee.csv</b> to the root folder.</div>', unsafe_allow_html=True)
    else:
        display = emp_df.copy().reset_index(drop=True)
        display.index += 1
        display.index.name = "S/N"
        st.dataframe(display, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# ATTENDANCE REPORTS
# ════════════════════════════════════════════════════════════════════════════
elif page == "Attendance Reports":
    st.markdown('<div class="page-title">Attendance Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Analyse daily attendance records</div>', unsafe_allow_html=True)

    month_folders = get_month_folders()
    if not month_folders:
        att_files = sorted(DAILY_DIR.glob("*.csv"), key=lambda f: f.name)
        if not att_files:
            st.markdown('<div class="info-box">No attendance files found. Create month subfolders inside <b>daily-attendance/</b>.</div>', unsafe_allow_html=True)
            st.stop()
        chosen_folder = DAILY_DIR
        file_names = [f.name for f in att_files]
    else:
        chosen_month  = st.selectbox("Select Month", month_folders)
        chosen_folder = DAILY_DIR / chosen_month
        att_files     = sorted(chosen_folder.glob("*.csv"), key=lambda f: f.name)
        if not att_files:
            st.markdown(f'<div class="info-box">No CSV files in <b>daily-attendance/{chosen_month}/</b>.</div>', unsafe_allow_html=True)
            st.stop()
        file_names = [f.name for f in att_files]

    selected_file = st.selectbox("Select Attendance File", file_names)
    chosen = chosen_folder / selected_file

    try:
        raw = pd.read_csv(chosen)
    except Exception as e:
        st.error(f"Could not read file: {e}"); st.stop()

    df = normalize_attendance(raw)
    if "Name" not in df.columns or "Time_in" not in df.columns:
        st.error(f"Missing required columns. Found: {list(raw.columns)}"); st.stop()

    emp_df   = load_employees()
    approved = get_approved_leaves()
    att_date = df["Date"].dropna().iloc[0].date() if "Date" in df.columns and not df["Date"].dropna().empty else None

    cutoff_shift = pd.Timestamp("1900-01-01 13:00:00")
    cutoff_late  = pd.Timestamp("1900-01-01 08:30:00")
    cutoff_ot    = pd.Timestamp("1900-01-01 19:00:00")

    def to_time_only(ts):
        if pd.isna(ts): return pd.NaT
        return pd.Timestamp(f"1900-01-01 {ts.strftime('%H:%M:%S')}")

    df["_tin"]  = df["Time_in_dt"].apply(to_time_only)  if "Time_in_dt"  in df.columns else pd.NaT
    df["_tout"] = df["Time_out_dt"].apply(to_time_only) if "Time_out_dt" in df.columns else pd.NaT

    df["Shift"] = df["_tin"].apply(
        lambda t: "Day Shift" if pd.notna(t) and t < cutoff_shift
                  else ("Afternoon/Night" if pd.notna(t) else "Unknown")
    )

    day_shift = df[df["Shift"] == "Day Shift"].copy()
    aft_shift = df[df["Shift"] == "Afternoon/Night"].copy()
    late_df   = day_shift[day_shift["_tin"] > cutoff_late].copy()
    ot_df     = day_shift[day_shift["_tout"] > cutoff_ot].copy()

    present_names = set(df["Name"].str.lower().dropna())
    def on_leave(n): return (n, att_date) in approved if att_date else False
    absent_list = [n for n in emp_df["Name"].tolist()
                   if n.lower() not in present_names and not on_leave(n.lower())] if not emp_df.empty else []
    absent_df = pd.DataFrame({"Name": absent_list})

    c1, c2, c3, c4 = st.columns(4)
    kpi("Late",               len(late_df),    c1)
    kpi("Absent",             len(absent_df),  c2)
    kpi("Overtime",           len(ot_df),      c3)
    kpi("Afternoon/Night",    len(aft_shift),  c4)

    disp_cols = [c for c in ["Name","Time_in","Time_out","Date","Shift"] if c in df.columns]

    section("Attendance List")
    st.dataframe(fmt_df_dates(df[disp_cols].reset_index(drop=True), ["Date"]), use_container_width=True)

    section("Late Staff (Day Shift — after 08:30)")
    if late_df.empty: st.info("No late staff recorded.")
    else: st.dataframe(fmt_df_dates(late_df[disp_cols].reset_index(drop=True), ["Date"]), use_container_width=True)

    section("Afternoon / Night Shift Staff")
    if aft_shift.empty: st.info("No afternoon/night shift staff.")
    else: st.dataframe(fmt_df_dates(aft_shift[disp_cols].reset_index(drop=True), ["Date"]), use_container_width=True)

    section("Absentees")
    if absent_df.empty: st.success("No absentees recorded.")
    else: st.dataframe(absent_df.reset_index(drop=True), use_container_width=True)

    section("Overtime Staff (Time Out after 19:00)")
    if ot_df.empty: st.info("No overtime staff recorded.")
    else: st.dataframe(fmt_df_dates(ot_df[disp_cols].reset_index(drop=True), ["Date"]), use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# LEAVE MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════
elif page == "Leave Management":
    st.markdown('<div class="page-title">Leave Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">View leave records and approval status</div>', unsafe_allow_html=True)

    leave_files = sorted(LEAVE_DIR.glob("*.csv"), key=lambda f: f.name)
    if not leave_files:
        st.markdown('<div class="info-box">No leave files found in <b>leave-management/</b>.</div>', unsafe_allow_html=True)
        st.stop()

    selected = st.selectbox("Select Leave File", [f.name for f in leave_files])
    try:
        ldf = pd.read_csv(LEAVE_DIR / selected)
        ldf.columns = ldf.columns.str.strip()
        section(f"Leave Records — {selected}")
        st.dataframe(ldf.reset_index(drop=True), use_container_width=True)
    except Exception as e:
        st.error(f"Could not read file: {e}")

# ════════════════════════════════════════════════════════════════════════════
# HR ANALYTICS
# ════════════════════════════════════════════════════════════════════════════
elif page == "HR Analytics":
    st.markdown('<div class="page-title">HR Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Saturday absentee monitoring · Late staff penalties · Performance scoring</div>', unsafe_allow_html=True)

    emp_df   = load_employees()
    approved = get_approved_leaves()
    all_emp  = emp_df["Name"].str.strip().tolist() if not emp_df.empty else []

    all_files   = get_all_attendance_files()
    valid_files = [f for f in all_files if not is_rainy_day(f.name)]
    rainy_count = len(all_files) - len(valid_files)

    if not valid_files:
        st.markdown('<div class="info-box">No valid attendance files found.</div>', unsafe_allow_html=True)
        st.stop()
    if rainy_count:
        st.markdown(f'<div class="info-box">ℹ️ {rainy_count} rainy-day file(s) excluded.</div>', unsafe_allow_html=True)

    # ── Parse every valid file ───────────────────────────────────────────────
    parsed_files = []
    for f in valid_files:
        try:
            raw  = pd.read_csv(f)
            df_n = normalize_attendance(raw)
            if "Date" not in df_n.columns or df_n["Date"].dropna().empty: continue
            att_date = df_n["Date"].dropna().iloc[0].date()
            parsed_files.append((f, att_date, df_n))
        except Exception:
            continue

    if not parsed_files:
        st.markdown('<div class="info-box">Could not parse any attendance files.</div>', unsafe_allow_html=True)
        st.stop()

    available_months = get_month_folders()  # already sorted by calendar order

    # ── Period selector ──────────────────────────────────────────────────────
    col_p, col_m = st.columns([1, 2])
    with col_p:
        period_type = st.selectbox("📅 View Period", ["Monthly","Quarterly","All"])

    if period_type == "Monthly":
        with col_m:
            chosen_month = st.selectbox("Select Month", available_months)
        selected_months = [chosen_month]
        period_label    = chosen_month

    elif period_type == "Quarterly":
        with col_m:
            chosen_month = st.selectbox("Select Quarter Start Month (covers next 3 months)", available_months)
        if chosen_month in MONTH_ORDER:
            idx = MONTH_ORDER.index(chosen_month)
            q_names = [MONTH_ORDER[i % 12] for i in range(idx, idx + 3)]
        else:
            q_names = [chosen_month]
        selected_months = [m for m in q_names if m in available_months]
        period_label    = f"Q: {' · '.join(selected_months)}"

    else:
        with col_m:
            st.markdown("<small style='color:#888'>All available months included</small>", unsafe_allow_html=True)
        selected_months = available_months
        period_label    = "All Periods"

    st.markdown(f"**Analysing:** `{period_label}`")
    st.markdown("---")

    def file_month(fp): return fp.parent.name

    period_files = [(f, d, df_n) for f, d, df_n in parsed_files
                    if file_month(f) in selected_months]

    if not period_files:
        st.markdown('<div class="info-box">No attendance data for selected period.</div>', unsafe_allow_html=True)
        st.stop()

    all_dates      = sorted({d for _, d, _ in period_files})
    all_saturdays  = sorted({d for _, d, _ in period_files
                              if pd.Timestamp(d).day_name() == "Saturday"})

    # ── Build daily and Saturday records ────────────────────────────────────
    # daily_records[emp][date]  = "present" | "absent" | "leave"
    # late_records[emp]         = list of dates the emp was late
    daily_records = {n: {} for n in all_emp}
    sat_records   = {n: {} for n in all_emp}
    late_records  = {n: [] for n in all_emp}   # weekdays only (no Saturdays)

    CUTOFF_LATE = pd.Timestamp("1900-01-01 08:30:00")
    CUTOFF_SHIFT= pd.Timestamp("1900-01-01 13:00:00")

    def to_t(ts):
        if pd.isna(ts): return pd.NaT
        try: return pd.Timestamp(f"1900-01-01 {ts.strftime('%H:%M:%S')}")
        except: return pd.NaT

    for f, att_date, df_n in period_files:
        present_lower = set(df_n["Name"].str.lower().dropna().str.strip())
        is_saturday   = pd.Timestamp(att_date).day_name() == "Saturday"

        # Build late set for this file (weekdays only, Day Shift only)
        late_lower = set()
        if not is_saturday and "Time_in_dt" in df_n.columns:
            for _, row in df_n.iterrows():
                t = to_t(row.get("Time_in_dt", pd.NaT))
                if pd.notna(t) and t < CUTOFF_SHIFT and t > CUTOFF_LATE:
                    late_lower.add(str(row["Name"]).strip().lower())

        for emp_name in all_emp:
            emp_lower = emp_name.lower()
            if emp_lower in present_lower:
                status = "present"
            elif (emp_lower, att_date) in approved:
                status = "leave"
            else:
                status = "absent"

            daily_records[emp_name][att_date] = status
            if is_saturday:
                sat_records[emp_name][att_date] = status
            elif emp_lower in late_lower:
                late_records[emp_name].append(att_date)

    # ════════════════════════════════════════════════════════════════════════
    # SATURDAY SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    sat_rows = []
    for emp in all_emp:
        rec = sat_records.get(emp, {})
        s_count   = len(all_saturdays)
        s_present = sum(1 for d in all_saturdays if rec.get(d) == "present")
        s_leave   = sum(1 for d in all_saturdays if rec.get(d) == "leave")
        s_absent  = sum(1 for d in all_saturdays if rec.get(d) == "absent")
        s_rate    = round(s_present / s_count * 100, 1) if s_count else 0.0
        # Score: each Saturday absence = -10 pts; max is always 100
        s_score   = max(0, min(100, 100 - s_absent * 10))
        # Penalty: each Saturday absence counts as 1 penalty day
        sat_rows.append({"Name": emp, "Sat_Count": s_count, "Sat_Present": s_present,
                         "Sat_Leave": s_leave, "Sat_Absent": s_absent,
                         "Sat_Rate_%": s_rate, "Sat_Score": s_score,
                         "Sat_Penalty_Days": s_absent})
    sat_summary = pd.DataFrame(sat_rows)

    # ════════════════════════════════════════════════════════════════════════
    # DAILY ABSENCE SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    daily_rows = []
    for emp in all_emp:
        rec         = daily_records.get(emp, {})
        total_days  = len(all_dates)
        t_present   = sum(1 for d in all_dates if rec.get(d) == "present")
        t_leave     = sum(1 for d in all_dates if rec.get(d) == "leave")
        t_absent    = sum(1 for d in all_dates if rec.get(d) == "absent")
        att_rate    = round(t_present / total_days * 100, 1) if total_days else 0.0
        d_score     = max(0, 100 - t_absent * 5)
        # Absence penalty: from 6th absence onward (each = 1 penalty day)
        abs_penalty = max(0, t_absent - 5)
        daily_rows.append({"Name": emp, "Working_Days": total_days,
                           "Present": t_present, "On_Leave": t_leave,
                           "Absent": t_absent, "Att_Rate_%": att_rate,
                           "Day_Score": d_score, "Absence_Penalty_Days": abs_penalty})
    daily_summary = pd.DataFrame(daily_rows)

    # ════════════════════════════════════════════════════════════════════════
    # LATE SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    late_rows = []
    for emp in all_emp:
        dates = late_records.get(emp, [])
        count = len(dates)
        # Penalty: from 6th lateness onward (each = 0.5 penalty day)
        late_penalty = round(max(0, count - 5) * 0.5, 1)
        late_rows.append({"Name": emp, "Late_Count": count,
                          "Late_Penalty_Days": late_penalty})
    late_summary = pd.DataFrame(late_rows)

    # ════════════════════════════════════════════════════════════════════════
    # COMBINED PERFORMANCE SCORE
    # Sat score 50% + Day score 30% + Late deduction 20%
    # ════════════════════════════════════════════════════════════════════════
    perf = sat_summary[["Name","Sat_Score","Sat_Absent","Sat_Rate_%"]].merge(
        daily_summary[["Name","Day_Score","Absent","Att_Rate_%","Absence_Penalty_Days"]], on="Name"
    ).merge(
        late_summary[["Name","Late_Count","Late_Penalty_Days"]], on="Name"
    )
    perf["Late_Score"]        = (100 - perf["Late_Count"] * 4).clip(0, 100)
    perf["Performance_Score"] = (
        perf["Sat_Score"]  * 0.50 +
        perf["Day_Score"]  * 0.30 +
        perf["Late_Score"] * 0.20
    ).clip(0, 100).round(1)
    perf["Total_Penalty_Days"] = (
        perf["Absence_Penalty_Days"] +
        perf["Sat_Absent"] +          # each Saturday absence = 1 penalty day
        perf["Late_Penalty_Days"]     # each lateness from 6th = 0.5 day
    ).round(1)
    perf["Grade"] = perf["Performance_Score"].apply(
        lambda s: "🟢 Excellent" if s >= 90 else
                  ("🟡 Good"    if s >= 75 else
                  ("🟠 Fair"    if s >= 60 else "🔴 Poor"))
    )

    # ════════════════════════════════════════════════════════════════════════
    # KPI CARDS
    # ════════════════════════════════════════════════════════════════════════
    avg_score        = round(perf["Performance_Score"].mean(), 1) if not perf.empty else 0
    total_sat_absent = int(sat_summary["Sat_Absent"].sum())
    staff_5plus_abs  = int((daily_summary["Absent"] >= 5).sum())
    staff_5plus_late = int((late_summary["Late_Count"] >= 5).sum())
    total_penalty    = round(perf["Total_Penalty_Days"].sum(), 1)

    c1, c2, c3 = st.columns(3)
    kpi("Employees Tracked",        len(all_emp),      c1)
    kpi("Saturdays in Period",      len(all_saturdays),c2)
    kpi("Avg Performance Score",    f"{avg_score}",    c3)
    c4, c5, c6 = st.columns(3)
    kpi("Total Saturday Absences",  total_sat_absent,  c4)
    kpi("Staff with 5+ Day Absences", staff_5plus_abs, c5)
    kpi("Total Penalty Days (All)", f"{total_penalty}", c6)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — PERFORMANCE SCORES
    # ════════════════════════════════════════════════════════════════════════
    section("📊 Overall Performance Scores")
    perf_disp = perf[["Name","Performance_Score","Grade","Sat_Absent","Sat_Rate_%",
                       "Absent","Att_Rate_%","Late_Count","Total_Penalty_Days"]].sort_values(
        "Performance_Score", ascending=False).reset_index(drop=True)
    perf_disp.index += 1; perf_disp.index.name = "Rank"

    show_toggle(perf_disp.reset_index(drop=True),
                x_col="Name", y_col="Performance_Score",
                title="Performance Score",
                key="tog_perf",
                color_scale=[[0,"#cc2200"],[0.4,"#ff6b00"],[0.7,"#ffaa55"],[1,"#22c55e"]])

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — SATURDAY ATTENDANCE RANKING
    # ════════════════════════════════════════════════════════════════════════
    section("📅 Saturday Attendance Ranking")
    sat_rank = sat_summary.sort_values(["Sat_Rate_%","Sat_Absent"],
                                        ascending=[False,True]).reset_index(drop=True)
    sat_rank.index += 1; sat_rank.index.name = "Rank"

    show_toggle(sat_rank[["Name","Sat_Count","Sat_Present","Sat_Leave",
                           "Sat_Absent","Sat_Rate_%","Sat_Score","Sat_Penalty_Days"]].reset_index(drop=True),
                x_col="Name", y_col="Sat_Rate_%",
                title="Saturday Attendance Rate (%)",
                key="tog_sat_rate",
                color_scale=[[0,"#ff6b00"],[0.5,"#ffaa55"],[1,"#22c55e"]],
                text_fmt="%{text}%")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SATURDAY ABSENTEES BY DATE (drill-down)
    # ════════════════════════════════════════════════════════════════════════
    section("🗓️ Saturday Absentees by Date")
    if not all_saturdays:
        st.info("No Saturdays in the selected period.")
    else:
        sat_options     = {fmt_date(d): d for d in all_saturdays}
        chosen_sat_lbl  = st.selectbox("Select a Saturday", list(sat_options.keys()), key="sat_drill")
        chosen_sat_date = sat_options[chosen_sat_lbl]

        absent_sat  = [e for e in all_emp if sat_records.get(e,{}).get(chosen_sat_date) == "absent"]
        leave_sat   = [e for e in all_emp if sat_records.get(e,{}).get(chosen_sat_date) == "leave"]
        present_sat = [e for e in all_emp if sat_records.get(e,{}).get(chosen_sat_date) == "present"]

        ca, cb, cc = st.columns(3)
        ca.metric("✅ Present",   len(present_sat))
        cb.metric("🏖️ On Leave", len(leave_sat))
        cc.metric("❌ Absent",    len(absent_sat))

        if absent_sat:
            adf = pd.DataFrame({"Name": absent_sat}).reset_index(drop=True)
            adf.index += 1; adf.index.name = "S/N"
            st.dataframe(adf, use_container_width=True)
        else:
            st.success("No absentees on this Saturday.")

        if leave_sat:
            with st.expander("Staff on approved leave this Saturday"):
                ldf2 = pd.DataFrame({"Name": leave_sat}).reset_index(drop=True)
                ldf2.index += 1
                st.dataframe(ldf2, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — ALL SATURDAY ABSENTEES (any absence)
    # ════════════════════════════════════════════════════════════════════════
    section("⚠️ Saturday Absentee Summary (all absences · 1 absence = 1 penalty day)")
    sat_any = sat_summary[sat_summary["Sat_Absent"] >= 1].sort_values(
        "Sat_Absent", ascending=False).reset_index(drop=True)

    if sat_any.empty:
        st.success("No Saturday absences in this period.")
    else:
        show_toggle(sat_any[["Name","Sat_Absent","Sat_Rate_%","Sat_Penalty_Days"]],
                    x_col="Name", y_col="Sat_Absent",
                    title="Saturday Absences",
                    key="tog_sat_absent",
                    color_scale=[[0,"#ffdd99"],[0.5,"#ff6b00"],[1,"#cc2200"]],
                    orient="v")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5 — STAFF WITH 5+ DAILY ABSENCES + PENALTY DAYS
    # Penalty starts from the 6th absence (each excess absence = 1 penalty day)
    # ════════════════════════════════════════════════════════════════════════
    section("🚨 Staff Absent 5+ Times — Penalty Calculation")
    st.markdown(
        '<div class="warn-box">📌 Penalty rule: first 5 absences are tolerated. '
        'From the <b>6th absence onward</b>, each additional day = <b>1 penalty day</b>.</div>',
        unsafe_allow_html=True)

    abs5 = daily_summary[daily_summary["Absent"] >= 5].sort_values(
        "Absent", ascending=False).reset_index(drop=True)
    abs5.index += 1; abs5.index.name = "S/N"

    if abs5.empty:
        st.success(f"No staff with 5+ absences in {period_label}.")
    else:
        show_toggle(abs5[["Name","Working_Days","Present","On_Leave","Absent",
                           "Att_Rate_%","Absence_Penalty_Days"]].rename(
                    columns={"Working_Days":"Working Days","On_Leave":"On Leave",
                             "Att_Rate_%":"Attendance (%)","Absence_Penalty_Days":"Penalty Days"}),
                    x_col="Name", y_col="Absence_Penalty_Days" if "Absence_Penalty_Days" in abs5.columns else "Penalty Days",
                    title="Penalty Days",
                    key="tog_abs_penalty",
                    color_scale=[[0,"#ffaa55"],[1,"#8b0000"]],
                    orient="v")
        total_abs_pen = int(abs5["Absence_Penalty_Days"].sum())
        st.markdown(
            f'<div class="info-box">⚠️ <b>{len(abs5)}</b> staff flagged. '
            f'Total absence penalty days: <b>{total_abs_pen}</b>.</div>',
            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6 — STAFF LATE 5+ TIMES + PENALTY DAYS
    # Penalty: from 6th lateness onward, each = 0.5 penalty day
    # Saturday is excluded from late tracking
    # ════════════════════════════════════════════════════════════════════════
    section("⏰ Staff Late 5+ Times — Penalty Calculation")
    st.markdown(
        '<div class="warn-box">📌 Penalty rule: first 5 late arrivals are tolerated. '
        'From the <b>6th lateness onward</b>, each = <b>0.5 penalty day</b>. '
        'Saturdays are <b>excluded</b> from late tracking.</div>',
        unsafe_allow_html=True)

    late5 = late_summary[late_summary["Late_Count"] >= 5].sort_values(
        "Late_Count", ascending=False).reset_index(drop=True)
    late5.index += 1; late5.index.name = "S/N"

    if late5.empty:
        st.success(f"No staff with 5+ late arrivals in {period_label}.")
    else:
        show_toggle(late5.rename(columns={"Late_Count":"Times Late",
                                           "Late_Penalty_Days":"Penalty Days"}),
                    x_col="Name", y_col="Late_Penalty_Days" if "Late_Penalty_Days" in late5.columns else "Penalty Days",
                    title="Late Penalty Days",
                    key="tog_late_penalty",
                    color_scale=[[0,"#ffe0b3"],[1,"#cc5500"]],
                    orient="v")
        total_late_pen = round(late5["Late_Penalty_Days"].sum(), 1)
        st.markdown(
            f'<div class="info-box">⚠️ <b>{len(late5)}</b> staff flagged for excessive lateness. '
            f'Total late penalty days: <b>{total_late_pen}</b>.</div>',
            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7 — CONSOLIDATED PENALTY SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    section("📋 Consolidated Penalty Summary")
    pen_summary = perf[perf["Total_Penalty_Days"] > 0][
        ["Name","Sat_Absent","Absent","Late_Count",
         "Absence_Penalty_Days","Late_Penalty_Days","Total_Penalty_Days","Grade"]
    ].copy().rename(columns={
        "Sat_Absent":           "Sat Absences",
        "Absent":               "Day Absences",
        "Late_Count":           "Times Late",
        "Absence_Penalty_Days": "Absence Pen. Days",
        "Late_Penalty_Days":    "Late Pen. Days",
        "Total_Penalty_Days":   "TOTAL Pen. Days"
    }).sort_values("TOTAL Pen. Days", ascending=False).reset_index(drop=True)
    pen_summary.index += 1; pen_summary.index.name = "S/N"

    if pen_summary.empty:
        st.success("No penalty days recorded for any staff in this period.")
    else:
        st.dataframe(pen_summary, use_container_width=True)
        st.markdown(
            f'<div class="info-box">📊 Combined penalty total across all staff: '
            f'<b>{total_penalty}</b> days.</div>',
            unsafe_allow_html=True)
