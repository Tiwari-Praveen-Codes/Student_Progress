import os
import json
import sqlite3
from datetime import date, datetime
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

import db
import sync_engine
import mysql_manager

st.set_page_config(
    page_title="Student Academic Progression",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto"
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide default Streamlit header padding */
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1120 0%, #111827 100%);
    border-right: 1px solid #1f2937;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {
    color: #f3f4f6;
}

/* ── Modern Sidebar Navigation Menu ── */
[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 5px;
    padding: 0;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label {
    background: rgba(255, 255, 255, 0.03);
    padding: 9px 14px;
    border-radius: 8px;
    margin-bottom: 2px;
    cursor: pointer;
    transition: all 0.18s ease-in-out;
    border: 1px solid transparent;
    display: flex;
    align-items: center;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateX(2px);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked),
[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
    background: #2563eb !important;
    border-color: #3b82f6 !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
}
[data-testid="stSidebar"] div[role="radiogroup"] > label p {
    color: #e5e7eb !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
    color: #ffffff !important;
    font-weight: 600 !important;
}
/* Hide default radio circle for a pure menu-tab appearance */
[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
    display: none !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] div[data-testid="stMarkdownContainer"] {
    margin-left: -10px;
}

[data-testid="stSidebar"] .stButton > button {
    background: #2563eb; color: white !important; border: none;
    border-radius: 8px; width: 100%; font-weight: 600;
    transition: background .2s;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #1d4ed8; }
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background: #374151 !important;
}
[data-testid="stSidebar"] .stMetric label { color: #9ca3af !important; font-size: .78rem; }
[data-testid="stSidebar"] .stMetric [data-testid="metric-value"] { color: #f9fafb !important; }

/* ── KPI Cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9);
    border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6;
    padding: 14px 18px; border-radius: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,.06);
    transition: box-shadow .2s;
}
[data-testid="metric-container"]:hover { box-shadow: 0 6px 16px rgba(59,130,246,.12); }

/* ── Tabs ── */
[data-baseweb="tab-list"] { gap: 6px; border-bottom: 2px solid #e2e8f0; }
[data-baseweb="tab"] {
    border-radius: 8px 8px 0 0; padding: 8px 16px;
    font-weight: 500; font-size: .88rem; color: #64748b;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #eff6ff; color: #1d4ed8 !important;
    border-bottom: 2px solid #3b82f6;
}

/* ── Cards ── */
.card {
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
}
.card-blue  { border-left: 4px solid #3b82f6; }
.card-green { border-left: 4px solid #10b981; }
.card-amber { border-left: 4px solid #f59e0b; }
.card-red   { border-left: 4px solid #ef4444; }
.card-violet{ border-left: 4px solid #8b5cf6; }

/* ── Drop-Year Alert ── */
.drop-alert {
    background: #fef2f2; border-left: 5px solid #ef4444;
    color: #991b1b; padding: 14px 18px; border-radius: 8px;
    margin: 8px 0 16px; font-size: .92rem;
}
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: .75rem; font-weight: 700; margin-left: 8px;
    background: #ef4444; color: white;
}

/* ── NF Proof Cards ── */
.nf-card {
    border-radius: 10px; padding: 16px 20px; margin-bottom: 12px;
    font-size: .9rem; line-height: 1.65;
}
.nf-1 { background: #eff6ff; border-left: 4px solid #3b82f6; }
.nf-2 { background: #f0fdf4; border-left: 4px solid #10b981; }
.nf-3 { background: #faf5ff; border-left: 4px solid #8b5cf6; }

/* ── Table Selector ── */
.table-pill {
    display: inline-block; background: #dbeafe; color: #1e40af;
    padding: 3px 10px; border-radius: 12px; font-size: .78rem;
    font-weight: 600; margin: 2px 3px;
}
.fk-arrow { color: #6b7280; font-size: .85rem; }

/* ── Section Header ── */
.sec-header {
    font-size: 1.05rem; font-weight: 700; color: #0f172a;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 2px solid #e2e8f0;
}

/* ==============================================================================
   RESPONSIVE DESIGN: MOBILE (ANDROID / iOS), TABLETS (iPAD), PC & MAC
   ============================================================================== */

/* 1. iOS Safari Auto-Zoom Prevention */
@media screen and (-webkit-min-device-pixel-ratio: 0) {
    input, select, textarea {
        font-size: 16px !important;
    }
}

/* 2. macOS & Modern Webkit Native Scrollbars */
::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(156, 163, 175, 0.4);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(107, 114, 128, 0.7);
}

/* 3. Smooth Touch Scrolling on iOS & Android */
div[data-testid="stDataFrame"], div[data-testid="stTable"] {
    -webkit-overflow-scrolling: touch;
    overflow-x: auto;
}

/* 4. Touch Target Accessibility (Min 44px for thumb tap) */
button, [role="button"], div[role="radiogroup"] > label {
    min-height: 42px;
    touch-action: manipulation;
}

/* 5. Tablets (iPad, Android Tablets: 768px to 1024px) */
@media screen and (max-width: 1024px) {
    .block-container {
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 10px !important;
    }
    /* 3-column wrap for metrics on tablet */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 30% !important;
        min-width: 140px !important;
    }
    .card {
        padding: 16px 18px;
    }
}

/* 6. Smartphones (Android & iPhone: < 768px) */
@media screen and (max-width: 767px) {
    .block-container {
        padding-top: 1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    /* 2-column wrap for metrics on phones */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 45% !important;
        min-width: 130px !important;
        margin-bottom: 8px;
    }
    /* Sidebar full width on mobile drawer */
    [data-testid="stSidebar"] {
        width: 100% !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 12px 14px;
        min-height: 46px;
    }
    /* Title and typography scaling */
    h1 { font-size: 1.55rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
    
    .drop-alert {
        padding: 10px 12px;
        font-size: 0.84rem;
    }
    .nf-card {
        padding: 12px 14px;
        font-size: 0.85rem;
    }
    /* Plotly touch resizing */
    .js-plotly-plot {
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)



# ─── HELPERS ──────────────────────────────────────────────────────────────────
def rdf(df: pd.DataFrame, **kw):
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)

DEPTS = [
    "Computer Science & Engineering",
    "Information Science & Engineering",
    "Electronics & Communication",
    "Mechanical Engineering",
    "Civil Engineering",
    "Data Science & AI",
]
STATUS_OPTS = ["Active", "Graduated", "On Hold", "Discontinued"]


def plotly_progression(sems_df, drops_df=None):
    """Returns a Plotly figure for SGPA/CGPA progression with drop-year shading."""
    fig = go.Figure()
    sems = sems_df.sort_values("semester_no")

    fig.add_trace(go.Scatter(
        x=sems["semester_no"], y=sems["sgpa"],
        name="SGPA", mode="lines+markers",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=8, color="#3b82f6", line=dict(width=2, color="white")),
        hovertemplate="Sem %{x}<br>SGPA: %{y:.2f}<extra></extra>"
    ))
    cgpa_valid = sems.dropna(subset=["cgpa"])
    if not cgpa_valid.empty:
        fig.add_trace(go.Scatter(
            x=cgpa_valid["semester_no"], y=cgpa_valid["cgpa"],
            name="CGPA", mode="lines+markers",
            line=dict(color="#10b981", width=3, dash="dot"),
            marker=dict(size=8, color="#10b981", line=dict(width=2, color="white")),
            hovertemplate="Sem %{x}<br>CGPA: %{y:.2f}<extra></extra>"
        ))

    # Mark Gap-status semesters
    gaps = sems[sems["status"] == "Gap"]
    if not gaps.empty:
        fig.add_trace(go.Scatter(
            x=gaps["semester_no"], y=gaps["sgpa"],
            name="Gap Semester", mode="markers",
            marker=dict(symbol="x", size=14, color="#ef4444"),
        ))

    fig.update_layout(
        xaxis=dict(title="Semester", dtick=1, gridcolor="#f1f5f9"),
        yaxis=dict(title="Grade Point", range=[0, 10.5], gridcolor="#f1f5f9"),
        legend=dict(orientation="h", y=1.1, x=0),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=30),
        hovermode="x unified",
        height=320,
    )
    return fig


def plotly_grade_bar(marks_df):
    """Bar chart of subject-wise grades for a student."""
    if marks_df.empty:
        return None
    fig = px.bar(
        marks_df, x="subject_code", y=["theory_marks", "lab_marks"],
        barmode="group",
        color_discrete_map={"theory_marks": "#3b82f6", "lab_marks": "#10b981"},
        labels={"value": "Marks", "subject_code": "Subject", "variable": "Component"},
        height=300,
    )
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=30),
        legend=dict(orientation="h", y=1.1),
    )
    return fig


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px;">
      <div style="font-size:2.4rem;">🎓</div>
      <div style="font-size:1.05rem; font-weight:700; color:#f1f5f9; margin-top:4px;">
        Academic Progression
      </div>
      <div style="font-size:0.72rem; color:#94a3b8; margin-top:2px;">
        DBMS Mini-Project · SQLite 3NF
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Direct Sidebar Navigation Panel
    st.markdown("<div style='font-size:0.75rem; color:#9ca3af; font-weight:700; letter-spacing:0.06em; margin-bottom:8px;'>NAVIGATION</div>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        [
            "📊 Dashboard & Analytics",
            "👨‍🎓 Student Management",
            "🏫 School Records",
            "📈 Semesters & Marks",
            "📚 Subjects Catalog",
            "🏆 Portfolio & Achievements",
            "⚠️ Drop Years",
            "☁️ Google Sheets Sync",
            "🐬 MySQL & Cloud Sync",
            "📐 3NF Schema & Viva",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("<div style='font-size:.78rem;color:#94a3b8;font-weight:600;letter-spacing:.05em'>DEMO CONTROLS</div>", unsafe_allow_html=True)

    if st.button("🌱 Load Unique Real Students Data"):
        import generate_real_students
        generate_real_students.seed_unique_real_dataset()
        st.success("Seeded 105 completely unique real students with @viva-technology.org emails and synced!")
        st.rerun()
    if st.button("🗑️ Reset Database", type="secondary"):
        with db.get_conn() as conn:
            for t in ["achievements", "drop_years", "semester_results", "semesters",
                      "subjects", "school_records", "students", "sync_queue"]:
                conn.execute(f"DELETE FROM {t};")
            conn.commit()
        st.warning("Database cleared.")
        st.rerun()

    st.markdown("---")
    sync_stat = sync_engine.get_sync_status()
    if sync_stat["configured"]:
        st.markdown("🟢 **Sheets Connected**")
    else:
        st.markdown("🟡 **Sheets: Setup needed**")
    st.metric("Sync Queue", f"{sync_stat['pending_operations']} pending")
    if sync_stat["pending_operations"] > 0:
        if st.button("⬆ Sync Now", key="sb_sync"):
            ok, msg, _ = sync_engine.process_sync_queue()
            st.success(msg) if ok else st.error(msg)
            st.rerun()

    st.markdown("<br><div style='font-size:.7rem;color:#475569;text-align:center'>v2.1 · Google Sheets Sync · Plotly Charts</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE ROUTER
# ─────────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD & ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard & Analytics":
    st.markdown("## 📊 Dashboard & Analytics")
    st.caption("Live metrics, student search, SGPA/CGPA progression, and drop-year indicators.")

    students_df = db.get_all_students()
    all_sems    = db.df_query("SELECT * FROM semesters")
    all_ach     = db.df_query("SELECT * FROM achievements")
    all_drops   = db.df_query("SELECT * FROM drop_years")

    # ── KPI Row ──
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("👤 Total Students",  len(students_df))
    k2.metric("✅ Active",          int(len(students_df[students_df.current_status == "Active"])) if not students_df.empty else 0)
    k3.metric("📖 Semesters",       len(all_sems))
    avg_cgpa = round(all_sems["cgpa"].dropna().mean(), 2) if not all_sems.empty and not all_sems["cgpa"].dropna().empty else 0.0
    k4.metric("🎯 Avg CGPA",        f"{avg_cgpa:.2f}" if avg_cgpa else "N/A")
    k5.metric("⚠️ Drop Years",      len(all_drops))
    k6.metric("🏆 Achievements",    len(all_ach))

    st.markdown("---")

    # ── Search & Student Selector ──
    col_search, col_filter = st.columns([3, 1])
    search_q   = col_search.text_input("🔍 Search student (Name / Roll No / Department)", key="dash_q")
    dept_filter = col_filter.selectbox("Dept filter", ["All"] + DEPTS, label_visibility="collapsed")

    filt = students_df.copy()
    if not filt.empty:
        if search_q:
            m = (filt.roll_no.str.contains(search_q, case=False, na=False) |
                 filt.full_name.str.contains(search_q, case=False, na=False) |
                 filt.department.str.contains(search_q, case=False, na=False))
            filt = filt[m]
        if dept_filter != "All":
            filt = filt[filt.department == dept_filter]

    with st.expander(f"📋 Student Directory ({len(filt)} shown)", expanded=False):
        rdf(filt)

    if filt.empty:
        st.info("No students found. Use the sidebar to load sample data.")
        st.stop()

    # ── Institutional Visual Analytics ──
    if HAS_PLOTLY and len(students_df) > 0:
        st.markdown("### 📊 Institutional Cohort & Performance Analytics")
        
        # Row 1: Department Distribution & CGPA Histogram
        g1, g2 = st.columns(2)
        with g1:
            dept_counts = students_df["department"].value_counts().reset_index()
            dept_counts.columns = ["Department", "Student Count"]
            fig_dept = px.pie(
                dept_counts, names="Department", values="Student Count",
                hole=0.45, title="🏛️ Enrollment by Department",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_dept.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
            st.plotly_chart(fig_dept, use_container_width=True)

        with g2:
            if not all_sems.empty and "cgpa" in all_sems.columns:
                valid_cgpa = all_sems["cgpa"].dropna()
                fig_cgpa = px.histogram(
                    valid_cgpa, nbins=15, title="🎯 Cumulative Grade Point Average (CGPA) Distribution",
                    labels={"value": "CGPA"}, color_discrete_sequence=["#3b82f6"]
                )
                fig_cgpa.add_vline(x=float(avg_cgpa), line_dash="dash", line_color="#ef4444",
                                   annotation_text=f"Avg: {avg_cgpa:.2f}", annotation_position="top left")
                fig_cgpa.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                       margin=dict(l=10, r=10, t=40, b=30), height=300,
                                       xaxis_title="CGPA Range", yaxis_title="Number of Semesters")
                st.plotly_chart(fig_cgpa, use_container_width=True)

        # Row 2: Admission Cohorts & Drop-Year Distribution
        g3, g4 = st.columns(2)
        with g3:
            adm_counts = students_df["admission_year"].value_counts().sort_index().reset_index()
            adm_counts.columns = ["Admission Year", "Students"]
            fig_adm = px.bar(
                adm_counts, x="Admission Year", y="Students", text="Students",
                title="📅 Admission Cohort Distribution",
                color="Students", color_continuous_scale="Blues"
            )
            fig_adm.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                  margin=dict(l=10, r=10, t=40, b=30), height=280, showlegend=False)
            st.plotly_chart(fig_adm, use_container_width=True)

        with g4:
            if not all_drops.empty and "reason" in all_drops.columns:
                drop_summary = all_drops["reason"].value_counts().reset_index()
                drop_summary.columns = ["Reason", "Cases"]
                fig_drops = px.pie(
                    drop_summary, names="Reason", values="Cases",
                    hole=0.4, title="⚠️ Academic Gap / Drop-Year Reasons",
                    color_discrete_sequence=px.colors.sequential.Reds_r
                )
                fig_drops.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=280)
                st.plotly_chart(fig_drops, use_container_width=True)
            else:
                st.info("No drop years recorded.")

        # Row 3: Theory vs Lab Marks Correlation Analysis
        all_results_df = db.df_query("""
            SELECT r.theory_marks, r.lab_marks, sub.subject_code, sub.subject_name
            FROM semester_results r
            JOIN subjects sub ON sub.subject_id = r.subject_id
            WHERE r.theory_marks IS NOT NULL AND r.lab_marks IS NOT NULL
            LIMIT 400
        """)
        if not all_results_df.empty:
            with st.expander("🔬 Theory vs Laboratory Performance Correlation", expanded=False):
                fig_scatter = px.scatter(
                    all_results_df, x="theory_marks", y="lab_marks", color="subject_code",
                    title="Theory Marks (out of 100) vs Laboratory Marks (out of 50)",
                    labels={"theory_marks": "Theory Marks (Max 100)", "lab_marks": "Lab Marks (Max 50)", "subject_code": "Course"},
                    hover_data=["subject_name"], height=350
                )
                fig_scatter.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=10, r=10, t=40, b=30))
                st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    # ── Student Progression Profile ──
    st.markdown("### 📈 Student Progression Profile")
    chosen = st.selectbox(
        "Select student",
        filt.student_id.tolist(),
        format_func=lambda s: (
            f"{filt.loc[filt.student_id==s,'roll_no'].iloc[0]}  —  "
            f"{filt.loc[filt.student_id==s,'full_name'].iloc[0]}"
        ),
        key="dash_sel",
    )
    st_row = filt[filt.student_id == chosen].iloc[0]

    # Info strip
    i1, i2, i3, i4 = st.columns(4)
    i1.markdown(f"**Roll:** `{st_row.roll_no}`")
    i2.markdown(f"**Name:** {st_row.full_name}")
    i3.markdown(f"**Dept:** {st_row.department}")
    i4.markdown(f"**Year:** {int(st_row.admission_year)} · *{st_row.current_status}*")

    # ── Drop-Year Indicator ──
    drops = db.df_query(
        "SELECT start_year,end_year,reason,approved_by FROM drop_years WHERE student_id=? ORDER BY start_year",
        (int(chosen),)
    )
    if not drops.empty:
        for _, dr in drops.iterrows():
            span = int(dr.end_year) - int(dr.start_year)
            st.markdown(f"""
            <div class="drop-alert">
              ⚠️ <strong>ACADEMIC GAP / DROP-YEAR DETECTED</strong>
              <span class="badge">Drop Year</span><br>
              <b>{int(dr.start_year)} → {int(dr.end_year)}</b>
              &nbsp;({span} year gap) &nbsp;|&nbsp;
              <b>Reason:</b> {dr.reason or 'Not specified'} &nbsp;|&nbsp;
              <b>Approved by:</b> {dr.approved_by or 'Institutional Council'}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Continuous academic progression — no drop years recorded.")

    # ── Progression Graph + Marks Bar ──
    sems = db.df_query(
        "SELECT semester_no, academic_year, sgpa, cgpa, status FROM semesters WHERE student_id=? ORDER BY semester_no",
        (int(chosen),)
    )
    marks = db.df_query(
        """SELECT se.semester_no, sub.subject_code, sub.subject_name, sub.subject_type,
                  r.theory_marks, r.lab_marks, r.total_marks, r.credits, r.grade_point, r.grade
           FROM semester_results r
           JOIN semesters se ON se.semester_id=r.semester_id
           JOIN subjects sub ON sub.subject_id=r.subject_id
           WHERE se.student_id=? ORDER BY se.semester_no, sub.subject_code""",
        (int(chosen),)
    )

    if not sems.empty:
        gc1, gc2 = st.columns([3, 2])
        with gc1:
            st.markdown("#### SGPA & CGPA Trend")
            if HAS_PLOTLY:
                fig = plotly_progression(sems, drops)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.line_chart(sems.set_index("semester_no")[["sgpa", "cgpa"]])

        with gc2:
            st.markdown("#### Semester Summary")
            rdf(sems)

        # ── Marks Bar ──
        if not marks.empty and HAS_PLOTLY:
            st.markdown("#### Subject Marks Breakdown (Theory vs Lab) — All Semesters")
            sem_opts = ["All Semesters"] + [f"Semester {n}" for n in sems.semester_no.tolist()]
            sel_sem = st.selectbox("Filter semester", sem_opts, key="marks_sem_filter")
            mf = marks if sel_sem == "All Semesters" else marks[marks.semester_no == int(sel_sem.split()[-1])]
            bar_fig = plotly_grade_bar(mf)
            if bar_fig:
                st.plotly_chart(bar_fig, use_container_width=True)

        # ── Full marks table in expander ──
        with st.expander("📄 Full Marks Table", expanded=False):
            rdf(marks)
    else:
        st.info("No semester data yet. Add records in Semesters & Marks.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — STUDENT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "👨‍🎓 Student Management":
    st.markdown("## 👨‍🎓 Student Management")

    action = st.radio("Action", ["📋 View All", "➕ Add Student", "✏️ Edit / Delete"], horizontal=True)
    students_all = db.get_all_students()

    if action == "📋 View All":
        st.markdown(f"**{len(students_all)} students registered.**")
        rdf(students_all)

    elif action == "➕ Add Student":
        st.markdown("#### Register New Student")
        with st.form("add_s", clear_on_submit=True):
            c1, c2 = st.columns(2)
            roll  = c1.text_input("Roll Number *", placeholder="21CS001")
            name  = c2.text_input("Full Name *",   placeholder="Rahul Sharma")
            email = c1.text_input("Email",          placeholder="user@viva-technology.org")
            phone = c2.text_input("Phone",          placeholder="9876543210")
            dept  = c1.selectbox("Department *", DEPTS)
            year  = c2.number_input("Admission Year *", 1990, 2100, 2024)
            status= c1.selectbox("Status *", STATUS_OPTS)
            if st.form_submit_button("✅ Register Student", type="primary"):
                if not roll.strip() or not name.strip():
                    st.error("Roll Number and Full Name are required.")
                elif len(roll.strip()) < 3:
                    st.error("Roll Number must be ≥ 3 characters.")
                else:
                    try:
                        sid = db.add_student(roll.strip(), name.strip(), email.strip() or None,
                                             phone.strip() or None, dept, int(year), status)
                        st.success(f"Student registered! (ID {sid})")
                        st.rerun()
                    except sqlite3.IntegrityError as e:
                        st.error(f"Error: {e}")

    else:  # Edit/Delete
        if students_all.empty:
            st.info("No students yet.")
        else:
            edit_sid = st.selectbox(
                "Select student",
                students_all.student_id.tolist(),
                format_func=lambda x: f"{students_all.loc[students_all.student_id==x,'roll_no'].iloc[0]} — {students_all.loc[students_all.student_id==x,'full_name'].iloc[0]}",
            )
            sd = students_all[students_all.student_id == edit_sid].iloc[0]
            with st.form("edit_s"):
                e1, e2 = st.columns(2)
                e_roll  = e1.text_input("Roll Number", sd.roll_no)
                e_name  = e2.text_input("Full Name",   sd.full_name)
                e_email = e1.text_input("Email",        sd.email or "")
                e_phone = e2.text_input("Phone",        sd.phone or "")
                d_idx   = DEPTS.index(sd.department) if sd.department in DEPTS else 0
                e_dept  = e1.selectbox("Department", DEPTS, index=d_idx)
                e_year  = e2.number_input("Admission Year", 1990, 2100, int(sd.admission_year))
                s_idx   = STATUS_OPTS.index(sd.current_status) if sd.current_status in STATUS_OPTS else 0
                e_stat  = e1.selectbox("Status", STATUS_OPTS, index=s_idx)
                if st.form_submit_button("💾 Save Changes", type="primary"):
                    try:
                        db.update_student(int(edit_sid), e_roll.strip(), e_name.strip(),
                                          e_email.strip() or None, e_phone.strip() or None,
                                          e_dept, int(e_year), e_stat)
                        st.success("Updated!")
                        st.rerun()
                    except sqlite3.IntegrityError as e:
                        st.error(str(e))

            with st.expander("🗑️ Delete this student (irreversible)"):
                st.warning(f"Deleting **{sd.full_name}** removes all dependent records via ON DELETE CASCADE.")
                if st.checkbox(f"Confirm delete '{sd.roll_no}'"):
                    if st.button("Delete permanently", type="primary"):
                        db.delete_student(int(edit_sid))
                        st.success("Deleted.")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SCHOOL RECORDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏫 School Records":
    st.markdown("## 🏫 School & Prior Academic Records")
    all_students = db.get_all_students()
    if all_students.empty:
        st.info("Register students first.")
        st.stop()

    fc, vc = st.columns([1, 2])
    with fc:
        with st.expander("➕ Add / Update Record", expanded=True):
            with st.form("sch_f", clear_on_submit=True):
                sch_sid = st.selectbox("Student", all_students.student_id.tolist(),
                    format_func=lambda x: f"{all_students.loc[all_students.student_id==x,'roll_no'].iloc[0]} — {all_students.loc[all_students.student_id==x,'full_name'].iloc[0]}")
                sch_lvl  = st.selectbox("Level", ["10th", "12th"])
                sch_brd  = st.text_input("Board",  placeholder="CBSE / ICSE / State Board")
                sch_inst = st.text_input("Institution", placeholder="DPS Bangalore")
                sch_yr   = st.number_input("Passing Year", 1990, 2100, 2021)
                sch_pct  = st.number_input("Percentage (%)", 0.0, 100.0, 85.0, step=0.1)
                if st.form_submit_button("💾 Save"):
                    if not sch_brd.strip():
                        st.error("Board is required.")
                    else:
                        db.save_school_record(int(sch_sid), sch_lvl, sch_brd, int(sch_yr), float(sch_pct), sch_inst)
                        st.success("Saved!")
                        st.rerun()

    with vc:
        sch_df = db.df_query("""
            SELECT r.record_id, s.roll_no, s.full_name, r.level, r.board,
                   r.passing_year, r.percentage, r.institution_name
            FROM school_records r JOIN students s ON s.student_id=r.student_id
            ORDER BY s.roll_no, r.level
        """)
        rdf(sch_df)

        if not sch_df.empty:
            with st.expander("🗑️ Delete a record"):
                del_rid = st.selectbox("Record", sch_df.record_id.tolist(),
                    format_func=lambda x: f"ID {x}: {sch_df.loc[sch_df.record_id==x,'roll_no'].iloc[0]} ({sch_df.loc[sch_df.record_id==x,'level'].iloc[0]})")
                if st.button("Delete Record"):
                    db.delete_school_record(int(del_rid))
                    st.success("Deleted."); st.rerun()

        # ── Bar chart: percentage by student & level ──
        if not sch_df.empty and HAS_PLOTLY:
            fig2 = px.bar(sch_df, x="full_name", y="percentage", color="level", barmode="group",
                          title="Prior Academic Percentages",
                          color_discrete_map={"10th": "#3b82f6", "12th": "#10b981"},
                          labels={"full_name": "Student", "percentage": "%"},
                          height=280)
            fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                               margin=dict(l=10, r=10, t=40, b=30),
                               legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — SEMESTERS & MARKS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Semesters & Marks":
    st.markdown("## 📈 Semesters & Detailed Marks")
    all_students = db.get_all_students()
    if all_students.empty:
        st.info("Register students first.")
        st.stop()

    sub1, sub2 = st.tabs(["📅 Semester Terms", "🔬 Theory & Lab Marks"])

    with sub1:
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            with st.expander("➕ Add / Update Semester", expanded=True):
                with st.form("sem_f", clear_on_submit=True):
                    s_sid  = st.selectbox("Student", all_students.student_id.tolist(),
                        format_func=lambda x: f"{all_students.loc[all_students.student_id==x,'roll_no'].iloc[0]} — {all_students.loc[all_students.student_id==x,'full_name'].iloc[0]}")
                    s_num  = st.number_input("Semester (1–12)", 1, 12, 1)
                    s_yr   = st.text_input("Academic Year", "2024-25")
                    s_sgpa = st.number_input("SGPA", 0.0, 10.0, 8.0, step=0.01)
                    s_cgpa = st.number_input("CGPA (0 = auto)", 0.0, 10.0, 0.0, step=0.01)
                    s_stat = st.selectbox("Status", ["Completed", "In Progress", "Gap"])
                    if st.form_submit_button("💾 Save"):
                        sid2 = db.save_semester(int(s_sid), int(s_num), s_yr, float(s_sgpa),
                                               float(s_cgpa) if s_cgpa > 0 else None, s_stat)
                        st.success(f"Semester saved (ID {sid2})")
                        st.rerun()

        with sc2:
            sem_df = db.df_query("""
                SELECT se.semester_id, s.roll_no, s.full_name, se.semester_no,
                       se.academic_year, se.sgpa, se.cgpa, se.status
                FROM semesters se JOIN students s ON s.student_id=se.student_id
                ORDER BY s.roll_no, se.semester_no
            """)
            rdf(sem_df)
            if not sem_df.empty:
                with st.expander("🗑️ Delete a semester"):
                    dsid = st.selectbox("Semester", sem_df.semester_id.tolist(),
                        format_func=lambda x: f"ID {x}: {sem_df.loc[sem_df.semester_id==x,'roll_no'].iloc[0]} Sem {sem_df.loc[sem_df.semester_id==x,'semester_no'].iloc[0]}")
                    if st.button("Delete (cascades marks)"):
                        db.delete_semester(int(dsid)); st.success("Deleted."); st.rerun()

    with sub2:
        st.info("💡 Theory and Lab marks are stored **independently** in `semester_results` — a 3NF design that avoids data redundancy.")
        sem_list  = db.df_query("""
            SELECT se.semester_id, s.roll_no, s.full_name, se.semester_no, se.academic_year
            FROM semesters se JOIN students s ON s.student_id=se.student_id
            ORDER BY s.roll_no, se.semester_no
        """)
        subs_all  = db.df_query("SELECT * FROM subjects ORDER BY subject_code")

        if sem_list.empty or subs_all.empty:
            st.warning("Create at least one semester and one subject first.")
        else:
            mc1, mc2 = st.columns([1, 2])
            with mc1:
                with st.expander("➕ Log Marks", expanded=True):
                    with st.form("marks_f", clear_on_submit=True):
                        m_sem = st.selectbox("Semester", sem_list.semester_id.tolist(),
                            format_func=lambda x: f"Sem {sem_list.loc[sem_list.semester_id==x,'semester_no'].iloc[0]} · {sem_list.loc[sem_list.semester_id==x,'roll_no'].iloc[0]}")
                        m_sub = st.selectbox("Subject", subs_all.subject_id.tolist(),
                            format_func=lambda x: f"{subs_all.loc[subs_all.subject_id==x,'subject_code'].iloc[0]} — {subs_all.loc[subs_all.subject_id==x,'subject_name'].iloc[0]}")
                        sub_meta = subs_all[subs_all.subject_id == m_sub].iloc[0]
                        st.caption(f"**{sub_meta.subject_type}** | {sub_meta.credits} credits | Theory max: {sub_meta.max_theory_marks} | Lab max: {sub_meta.max_lab_marks}")
                        m_th  = st.number_input("Theory Marks", 0.0, 100.0, 75.0, disabled=(sub_meta.subject_type == "Lab"))
                        m_lab = st.number_input("Lab Marks",    0.0, 100.0, 45.0, disabled=(sub_meta.subject_type == "Theory"))
                        m_cr  = st.number_input("Credits", 0.0, 10.0, float(sub_meta.credits))
                        m_att = st.number_input("Attendance %", 0.0, 100.0, 90.0)
                        m_gr  = st.text_input("Grade override (blank = auto)")
                        if st.form_submit_button("💾 Save"):
                            t = m_th if sub_meta.subject_type in ("Theory", "Theory+Lab") else None
                            l = m_lab if sub_meta.subject_type in ("Lab",   "Theory+Lab") else None
                            rid = db.save_semester_result(int(m_sem), int(m_sub), t, l, float(m_cr),
                                                          m_gr.strip() or None, float(m_att))
                            st.success(f"Result {rid} saved. SGPA recalculated."); st.rerun()

            with mc2:
                res_df = db.df_query("""
                    SELECT r.result_id, s.roll_no, se.semester_no,
                           sub.subject_code, sub.subject_name, sub.subject_type,
                           r.theory_marks, r.lab_marks, r.total_marks,
                           r.credits, r.grade_point, r.grade
                    FROM semester_results r
                    JOIN semesters se ON se.semester_id=r.semester_id
                    JOIN students s ON s.student_id=se.student_id
                    JOIN subjects sub ON sub.subject_id=r.subject_id
                    ORDER BY s.roll_no, se.semester_no, sub.subject_code
                """)
                rdf(res_df)
                if not res_df.empty:
                    with st.expander("🗑️ Delete a result"):
                        drid = st.selectbox("Result", res_df.result_id.tolist(),
                            format_func=lambda x: f"{res_df.loc[res_df.result_id==x,'roll_no'].iloc[0]} — {res_df.loc[res_df.result_id==x,'subject_code'].iloc[0]}")
                        if st.button("Delete"):
                            db.delete_semester_result(int(drid)); st.success("Deleted."); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — SUBJECTS CATALOG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📚 Subjects Catalog":
    st.markdown("## 📚 Subjects Catalog")
    st.caption("Master course repository — normalized to eliminate redundancy (3NF: subject properties stored once).")
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        with st.expander("➕ Add / Update Course", expanded=True):
            with st.form("sub_f", clear_on_submit=True):
                sc_code = st.text_input("Course Code *", placeholder="CS301").upper()
                sc_name = st.text_input("Course Name *", placeholder="Database Systems")
                sc_type = st.selectbox("Type *", ["Theory", "Lab", "Theory+Lab"])
                sc_cr   = st.number_input("Credits", 1.0, 10.0, 4.0)
                sc_dept = st.text_input("Department", DEPTS[0])
                sc_mth  = st.number_input("Max Theory Marks", 0.0, 100.0, 100.0)
                sc_mlab = st.number_input("Max Lab Marks",    0.0, 100.0, 50.0)
                if st.form_submit_button("💾 Save"):
                    if not sc_code or not sc_name:
                        st.error("Code and Name required.")
                    else:
                        db.save_subject(sc_code, sc_name, sc_type, sc_cr, sc_dept, sc_mth, sc_mlab)
                        st.success("Saved!"); st.rerun()
    with sc2:
        subs_df = db.df_query("SELECT * FROM subjects ORDER BY subject_code")
        rdf(subs_df)
        if not subs_df.empty:
            with st.expander("🗑️ Delete Subject (RESTRICT if in use)"):
                dsub = st.selectbox("Subject", subs_df.subject_id.tolist(),
                    format_func=lambda x: f"{subs_df.loc[subs_df.subject_id==x,'subject_code'].iloc[0]} — {subs_df.loc[subs_df.subject_id==x,'subject_name'].iloc[0]}")
                if st.button("Delete Subject"):
                    ok, msg = db.delete_subject(int(dsub))
                    st.success(msg) if ok else st.error(msg)
                    if ok: st.rerun()

        # Credits distribution donut
        if not subs_df.empty and HAS_PLOTLY:
            fig3 = px.pie(subs_df, values="credits", names="subject_code",
                          title="Credit Distribution by Course",
                          hole=0.45, height=280)
            fig3.update_layout(margin=dict(l=10, r=10, t=40, b=10),
                               legend=dict(orientation="v"))
            st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — PORTFOLIO & ACHIEVEMENTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏆 Portfolio & Achievements":
    st.markdown("## 🏆 Portfolio & Achievements")
    all_students = db.get_all_students()
    all_cats     = db.df_query("SELECT * FROM achievement_categories ORDER BY category_name")
    if all_students.empty:
        st.info("Register students first."); st.stop()

    with st.expander("➕ Add Achievement", expanded=False):
        with st.form("ach_f", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            a_sid  = ac1.selectbox("Student", all_students.student_id.tolist(),
                format_func=lambda x: f"{all_students.loc[all_students.student_id==x,'roll_no'].iloc[0]} — {all_students.loc[all_students.student_id==x,'full_name'].iloc[0]}")
            a_cat  = ac2.selectbox("Category", all_cats.category_id.tolist(),
                format_func=lambda x: all_cats.loc[all_cats.category_id==x,'category_name'].iloc[0])
            a_ttl  = ac1.text_input("Title *", placeholder="Smart India Hackathon Winner")
            a_org  = ac2.text_input("Organizer", placeholder="Ministry of Education")
            a_sco  = ac1.selectbox("Scope", ["Internal", "External"])
            a_typ  = ac2.selectbox("Type", ["Technical", "Co-curricular", "Extra-curricular", "Seminar"])
            a_dt   = ac1.date_input("Date", value=date.today())
            a_awd  = ac2.text_input("Award Level", placeholder="1st Prize / Participant")
            a_desc = st.text_area("Description")
            if st.form_submit_button("✅ Add"):
                if not a_ttl.strip():
                    st.error("Title required.")
                else:
                    aid = db.save_achievement(int(a_sid), int(a_cat), a_ttl, a_org, a_sco, a_typ, str(a_dt), a_desc, a_awd)
                    st.success(f"Added (ID {aid})!"); st.rerun()

    # ── Filters & Directory ──
    st.markdown("#### Portfolio Filter")
    f1, f2, f3 = st.columns(3)
    fa_cat  = f1.selectbox("Category",  ["All"] + all_cats.category_name.tolist())
    fa_sco  = f2.selectbox("Scope",     ["All", "Internal", "External"])
    fa_typ  = f3.selectbox("Type",      ["All", "Technical", "Co-curricular", "Extra-curricular", "Seminar"])

    all_ach = db.df_query("""
        SELECT a.achievement_id, s.roll_no, s.full_name, c.category_name,
               a.title, a.organizer, a.event_scope, a.activity_type,
               a.award_level, a.achievement_date, a.description
        FROM achievements a
        JOIN students s ON s.student_id=a.student_id
        JOIN achievement_categories c ON c.category_id=a.category_id
        ORDER BY a.achievement_date DESC
    """)
    filtered_ach = all_ach.copy()
    if fa_cat != "All": filtered_ach = filtered_ach[filtered_ach.category_name == fa_cat]
    if fa_sco != "All": filtered_ach = filtered_ach[filtered_ach.event_scope == fa_sco]
    if fa_typ != "All": filtered_ach = filtered_ach[filtered_ach.activity_type == fa_typ]
    rdf(filtered_ach)

    if not all_ach.empty:
        c_dl, c_del = st.columns([2, 1])
        c_dl.download_button("📥 Export CSV", filtered_ach.to_csv(index=False).encode(),
                             "portfolio.csv", "text/csv")
        with c_del.expander("🗑️ Delete"):
            daid = st.selectbox("Achievement", filtered_ach.achievement_id.tolist() if not filtered_ach.empty else [],
                format_func=lambda x: f"ID {x}: {filtered_ach.loc[filtered_ach.achievement_id==x,'title'].iloc[0][:30]}" if not filtered_ach.empty else "")
            if st.button("Delete") and daid:
                db.delete_achievement(int(daid)); st.success("Deleted."); st.rerun()

    # ── Category breakdown donut ──
    if not all_ach.empty and HAS_PLOTLY:
        cat_counts = all_ach.groupby("category_name").size().reset_index(name="count")
        fig_cat = px.pie(cat_counts, values="count", names="category_name",
                         title="Achievements by Category", hole=0.4, height=250)
        fig_cat.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_cat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — DROP YEARS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚠️ Drop Years":
    st.markdown("## ⚠️ Academic Gap / Drop Year Records")
    all_students = db.get_all_students()
    if all_students.empty:
        st.info("Register students first."); st.stop()

    dc1, dc2 = st.columns([1, 2])
    with dc1:
        with st.expander("➕ Record Gap Year", expanded=True):
            with st.form("drop_f", clear_on_submit=True):
                d_sid = st.selectbox("Student", all_students.student_id.tolist(),
                    format_func=lambda x: f"{all_students.loc[all_students.student_id==x,'roll_no'].iloc[0]} — {all_students.loc[all_students.student_id==x,'full_name'].iloc[0]}")
                d_st  = st.number_input("Start Year", 1990, 2100, 2023)
                d_en  = st.number_input("End Year",   int(d_st), 2100, int(d_st)+1)
                d_rsn = st.text_area("Reason", placeholder="Medical leave, family exigency…")
                d_apr = st.text_input("Approved by", placeholder="Dean of Academics")
                if st.form_submit_button("💾 Save"):
                    if d_en < d_st:
                        st.error("End year must be ≥ Start year.")
                    else:
                        did = db.save_drop_year(int(d_sid), int(d_st), int(d_en), d_rsn, d_apr)
                        st.success(f"Gap year saved (ID {did})!"); st.rerun()

    with dc2:
        drops_df = db.df_query("""
            SELECT d.drop_id, s.roll_no, s.full_name, d.start_year, d.end_year,
                   (d.end_year-d.start_year) AS gap_yrs, d.reason, d.approved_by
            FROM drop_years d JOIN students s ON s.student_id=d.student_id
            ORDER BY d.start_year DESC
        """)
        rdf(drops_df)
        if not drops_df.empty:
            with st.expander("🗑️ Delete a record"):
                ddid = st.selectbox("Record", drops_df.drop_id.tolist(),
                    format_func=lambda x: f"ID {x}: {drops_df.loc[drops_df.drop_id==x,'roll_no'].iloc[0]} ({drops_df.loc[drops_df.drop_id==x,'start_year'].iloc[0]}–{drops_df.loc[drops_df.drop_id==x,'end_year'].iloc[0]})")
                if st.button("Delete"):
                    db.delete_drop_year(int(ddid)); st.success("Deleted."); st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — GOOGLE SHEETS SYNC
# ══════════════════════════════════════════════════════════════════════════════
elif page == "☁️ Google Sheets Sync":
    st.markdown("## ☁️ Google Sheets Synchronization")
    st.caption("Queue-driven, one-way sync: every database INSERT / UPDATE / DELETE is captured in `sync_queue` and pushed to Google Sheets.")

    status = sync_engine.get_sync_status()
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Status",       "🟢 Connected" if status["configured"] else "🟡 Offline")
    d2.metric("Queue Backlog", f"{status['pending_operations']}")
    d3.metric("Total Events",  status["total_operations"])
    d4.metric("Last Sync",     status["last_full_sync"] or "Never")

    st.markdown("---")
    sc1, sc2 = st.columns([1, 1])

    with sc1:
        st.markdown("#### ⚙️ Settings")
        curr_id = sync_engine.get_configured_sheet_id()
        new_id  = st.text_input("Google Spreadsheet ID", value=curr_id,
                                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        auto_on = st.toggle("Auto-sync on every DB change", value=status["auto_sync"])
        if st.button("Save Settings"):
            sync_engine.set_configured_sheet_id(new_id)
            sync_engine.set_auto_sync_enabled(auto_on)
            st.success("Saved!"); st.rerun()

        st.markdown("#### 🚀 Controls")
        b1, b2 = st.columns(2)
        if b1.button("Process Queue", type="primary"):
            ok, msg, cnt = sync_engine.process_sync_queue()
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()
        if b2.button("Full Refresh"):
            ok, msg, cnt = sync_engine.full_refresh_sync()
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()

        st.markdown("#### 🧪 Local Verification Test")
        st.caption("Tests INSERT → UPDATE → DELETE queue capture with payload snapshots.")
        if st.button("Run Verification Test"):
            res = sync_engine.run_mock_sync_simulation()
            st.success(res["message"])
            st.rerun()

    with sc2:
        st.markdown("#### 📋 Setup Guide")
        steps = [
            ("1. Create Cloud Project", "Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project."),
            ("2. Enable APIs", "Enable **Google Sheets API** and **Google Drive API**."),
            ("3. Service Account", "Go to **IAM & Admin → Service Accounts → Create → JSON Key**. Save as `service_account.json` in this folder."),
            ("4. Share Spreadsheet", f"Create a Google Sheet and share it as **Editor** with the service account email below."),
            ("5. Set Sheet ID", "Paste the spreadsheet ID (from the URL) in the Settings panel on the left."),
        ]
        for title, detail in steps:
            with st.expander(title):
                st.markdown(detail)
                if title == "4. Share Spreadsheet" and status["client_email"]:
                    st.code(status["client_email"])

    st.markdown("---")
    st.markdown("#### 📜 Sync Queue Audit Log")
    q_log = db.df_query("""
        SELECT queue_id, table_name, record_id, operation, created_at,
               synced, synced_at, error,
               SUBSTR(payload_snapshot,1,50) AS snapshot_preview
        FROM sync_queue ORDER BY queue_id DESC LIMIT 30
    """)
    rdf(q_log)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — 3NF SCHEMA & VIVA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📐 3NF Schema & Viva":
    st.markdown("## 📐 Relational Schema, 3NF Normalization & Viva Guide")
    st.caption("Interactive reference for project defense, viva questions, and relational design proofs.")

    # ── NF Proof Cards ──
    st.markdown("### 🏆 Normalization Proofs")
    nf_c1, nf_c2, nf_c3 = st.columns(3)
    with nf_c1:
        st.markdown("""
        <div class="nf-card nf-1">
          <b>1️⃣ First Normal Form (1NF)</b><br><br>
          ✔ Every attribute value is <b>atomic</b> — no comma-separated marks, no arrays.<br>
          ✔ Each row is uniquely identified by a defined <b>Primary Key</b>
          (<code>student_id</code>, <code>semester_id</code>, etc.).<br>
          ✔ No repeating groups: marks for each subject are stored in a separate row, not as columns.
        </div>
        """, unsafe_allow_html=True)
    with nf_c2:
        st.markdown("""
        <div class="nf-card nf-2">
          <b>2️⃣ Second Normal Form (2NF)</b><br><br>
          ✔ Schema satisfies 1NF.<br>
          ✔ No <b>partial dependencies</b>: in <code>semester_results</code>,
          the composite key is <code>(semester_id, subject_id)</code> — marks, credits, grade
          all depend on the <em>full</em> key, not just one part.<br>
          ✔ Single-column PKs eliminate partial dependency naturally.
        </div>
        """, unsafe_allow_html=True)
    with nf_c3:
        st.markdown("""
        <div class="nf-card nf-3">
          <b>3️⃣ Third Normal Form (3NF)</b><br><br>
          ✔ Schema satisfies 2NF.<br>
          ✔ No <b>transitive dependencies</b>: Course name / credits are stored
          <em>once</em> in <code>subjects</code> — not repeated in every student's result row.<br>
          ✔ Achievement categories isolated in <code>achievement_categories</code>,
          eliminating update and deletion anomalies.
        </div>
        """, unsafe_allow_html=True)

    # ── Entity Relationship Diagram (Text) ──
    st.markdown("---")
    st.markdown("### 🗄️ Entity Relationship Overview")
    st.markdown("""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:20px 24px;font-family:monospace;font-size:.82rem;line-height:2">
    <b>students</b> (student_id PK, roll_no UK, full_name, email UK, phone, department, admission_year, current_status)
    <br>
    &nbsp;&nbsp;│── <b>school_records</b> (record_id PK, student_id FK→CASCADE, level, board, passing_year, percentage)
    <br>
    &nbsp;&nbsp;│── <b>semesters</b> (semester_id PK, student_id FK→CASCADE, semester_no, academic_year, sgpa, cgpa, status)
    <br>
    &nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└── <b>semester_results</b> (result_id PK, semester_id FK→CASCADE, subject_id FK→RESTRICT,
    <br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#3b82f6">theory_marks</span>, <span style="color:#10b981">lab_marks</span>, total_marks, credits, grade_point, grade)
    <br>
    &nbsp;&nbsp;│── <b>drop_years</b> (drop_id PK, student_id FK→CASCADE, start_year, end_year, reason, approved_by)
    <br>
    &nbsp;&nbsp;└── <b>achievements</b> (achievement_id PK, student_id FK→CASCADE, category_id FK→RESTRICT, title, …)
    <br><br>
    <b>subjects</b> (subject_id PK, subject_code UK, subject_name, subject_type, credits, max_theory_marks, max_lab_marks)
    <br>
    <b>achievement_categories</b> (category_id PK, category_name UK, description)
    <br>
    <b>sync_queue</b> (queue_id PK, table_name, record_id, operation, payload_snapshot, synced, synced_at, error)
    </div>
    """, unsafe_allow_html=True)

    # ── Constraint Dropdowns ──
    st.markdown("---")
    st.markdown("### 🔒 Constraints & Integrity Rules")
    with st.expander("🔑 Primary & Candidate (UNIQUE) Keys"):
        st.markdown("""
| Table | Primary Key | Unique / Candidate Keys |
|:---|:---|:---|
| `students` | `student_id` | `roll_no`, `email` |
| `school_records` | `record_id` | `(student_id, level)` |
| `semesters` | `semester_id` | `(student_id, semester_no)` |
| `subjects` | `subject_id` | `subject_code` |
| `semester_results` | `result_id` | `(semester_id, subject_id)` |
| `drop_years` | `drop_id` | `(student_id, start_year)` |
| `achievement_categories` | `category_id` | `category_name` |
""")

    with st.expander("✅ CHECK Constraints (Value Validation)"):
        st.markdown("""
| Attribute | Rule |
|:---|:---|
| `students.admission_year` | `BETWEEN 1990 AND 2100` |
| `students.current_status` | `IN ('Active','Graduated','On Hold','Discontinued')` |
| `school_records.percentage` | `BETWEEN 0.0 AND 100.0` |
| `semesters.sgpa` | `BETWEEN 0.0 AND 10.0` |
| `semesters.cgpa` | `IS NULL OR BETWEEN 0.0 AND 10.0` |
| `semester_results.theory_marks` | `IS NULL OR BETWEEN 0.0 AND 100.0` |
| `semester_results.lab_marks` | `IS NULL OR BETWEEN 0.0 AND 100.0` |
| `drop_years.end_year` | `>= start_year` |
| `achievements.event_scope` | `IS NULL OR IN ('Internal','External')` |
""")

    with st.expander("🔗 Foreign Key Actions (Referential Integrity)"):
        st.markdown("""
| Child Table | FK Column | Parent | On Delete |
|:---|:---|:---|:---|
| `school_records` | `student_id` | `students` | **CASCADE** — child deleted with parent |
| `semesters` | `student_id` | `students` | **CASCADE** |
| `semester_results` | `semester_id` | `semesters` | **CASCADE** |
| `semester_results` | `subject_id` | `subjects` | **RESTRICT** — prevents orphan marks |
| `drop_years` | `student_id` | `students` | **CASCADE** |
| `achievements` | `student_id` | `students` | **CASCADE** |
| `achievements` | `category_id` | `achievement_categories` | **RESTRICT** |
""")

    with st.expander("💡 Why 3NF? — Anomaly Prevention Examples"):
        st.markdown("""
**Without normalization (bad design):**
```
semester_results(student_roll, student_name, dept, semester_no, subject_name, credits, theory_marks, lab_marks)
```
Problems:
- **Insertion Anomaly:** Cannot add a new course without having a student enrolled.
- **Update Anomaly:** Changing `credits` for CS301 requires updating every student row — risk of inconsistency.
- **Deletion Anomaly:** Deleting a student's record could wipe out the course catalog.

**With 3NF (our design):**
- `subjects` stores course details **once**.
- `semester_results` only stores the **relationship** (which student attempted which course) and the **outcome** (marks, grade).
- Updating CS301's credits = 1 row changed in `subjects`. Zero risk of inconsistency.
""")

    # ── Key SQL Queries ──
    st.markdown("---")
    st.markdown("### 💻 Key SQL Queries")
    q_opts = st.selectbox("Select Query to View", [
        "1. Student Progression (SGPA/CGPA over time)",
        "2. Credit-Weighted SGPA Formula",
        "3. Full Performance Transcript (Multi-table JOIN)",
        "4. Drop-Year Detection",
        "5. Portfolio by Category",
    ])
    queries = {
        "1. Student Progression (SGPA/CGPA over time)": """SELECT semester_no, academic_year, sgpa, cgpa, status
FROM semesters
WHERE student_id = ?
ORDER BY semester_no;""",
        "2. Credit-Weighted SGPA Formula": """SELECT
    ROUND(SUM(r.credits * r.grade_point) / SUM(r.credits), 2) AS calculated_sgpa
FROM semester_results r
WHERE r.semester_id = ?;
-- SGPA = Σ(Credits × Grade Point) / Σ(Credits)""",
        "3. Full Performance Transcript (Multi-table JOIN)": """SELECT s.roll_no, s.full_name,
       se.semester_no, se.academic_year,
       sub.subject_code, sub.subject_name, sub.subject_type,
       r.theory_marks, r.lab_marks, r.total_marks, r.grade
FROM students s
JOIN semesters se ON se.student_id = s.student_id
JOIN semester_results r ON r.semester_id = se.semester_id
JOIN subjects sub ON sub.subject_id = r.subject_id
WHERE s.roll_no = '21CS001'
ORDER BY se.semester_no, sub.subject_code;""",
        "4. Drop-Year Detection": """SELECT s.roll_no, s.full_name,
       d.start_year, d.end_year,
       (d.end_year - d.start_year) AS gap_duration_years,
       d.reason
FROM drop_years d
JOIN students s ON s.student_id = d.student_id
ORDER BY d.start_year;""",
        "5. Portfolio by Category": """SELECT s.full_name, c.category_name,
       a.title, a.event_scope, a.award_level, a.achievement_date
FROM achievements a
JOIN students s ON s.student_id = a.student_id
JOIN achievement_categories c ON c.category_id = a.category_id
WHERE s.student_id = ?
ORDER BY a.achievement_date DESC;""",
    }
    st.code(queries[q_opts], language="sql")

    # ── Live Table Overview ──
    st.markdown("---")
    st.markdown("### 📊 Live Database Table Sizes")
    db_tables = db.df_query("""
        SELECT name AS table_name,
               (SELECT COUNT(*) FROM pragma_table_info(m.name)) AS columns
        FROM sqlite_master m
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    # Add row counts
    rows = []
    for _, r in db_tables.iterrows():
        try:
            cnt = db.fetch_one(f"SELECT COUNT(*) c FROM {r['table_name']}")
            rows.append(cnt["c"])
        except Exception:
            rows.append(0)
    db_tables["rows"] = rows

    if HAS_PLOTLY:
        fig_tables = px.bar(db_tables, x="table_name", y="rows",
                            color="rows", color_continuous_scale="Blues",
                            title="Row Count per Table",
                            labels={"table_name": "Table", "rows": "Rows"},
                            height=280)
        fig_tables.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                 margin=dict(l=10, r=10, t=40, b=30),
                                 showlegend=False)
        st.plotly_chart(fig_tables, use_container_width=True)
    rdf(db_tables)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 10 — MYSQL DATABASE & CLOUD SYNC
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🐬 MySQL & Cloud Sync":
    st.markdown("## 🐬 MySQL Database & Google Sheets Cloud Bridge")
    st.caption("Connect your local MySQL Server 8.0, initialize the 3NF schema, migrate data, and synchronize to Google Sheets.")

    cfg = mysql_manager.load_mysql_config()

    m_col1, m_col2 = st.columns([1, 1])

    with m_col1:
        st.markdown("### 🔌 1. MySQL Server Credentials")
        with st.form("mysql_cred_form"):
            f_host = st.text_input("Host", value=cfg.get("host", "localhost"))
            f_port = st.number_input("Port", value=int(cfg.get("port", 3306)), step=1)
            f_user = st.text_input("Username", value=cfg.get("user", "root"))
            f_pass = st.text_input("Password", value=cfg.get("password", ""), type="password", placeholder="Enter your MySQL root password")
            f_db   = st.text_input("Database Name", value=cfg.get("database", "student_progression_db"))

            btn_test = st.form_submit_button("🧪 Test Connection & Save Config", type="primary")
            if btn_test:
                ok, msg = mysql_manager.test_mysql_connection(f_host, f_port, f_user, f_pass)
                if ok:
                    mysql_manager.save_mysql_config({
                        "host": f_host, "port": int(f_port), "user": f_user, "password": f_pass, "database": f_db
                    })
                    st.success(f"✅ {msg}")
                    st.info("Config saved to `mysql_config.json`.")
                else:
                    st.error(f"❌ {msg}")

        st.markdown("---")
        st.markdown("### 🛠️ 2. Database Schema & Data Migration")
        btn_init = st.button("🏗️ Initialize 3NF Database & Tables in MySQL", help="Executes schema_mysql.sql to create student_progression_db and all 10 tables.")
        if btn_init:
            ok, msg = mysql_manager.init_mysql_database(f_host, f_port, f_user, f_pass)
            if ok:
                st.success(f"🎉 {msg}")
            else:
                st.error(f"❌ {msg}")

        btn_mig = st.button("🔄 Migrate All Data from SQLite to MySQL", help="Copies all students, semesters, theory/lab marks, and drop years from SQLite into MySQL.")
        if btn_mig:
            ok, msg = mysql_manager.migrate_sqlite_to_mysql(f_host, f_port, f_user, f_pass, f_db)
            if ok:
                st.success(f"🚀 {msg}")
            else:
                st.error(f"❌ {msg}")

    with m_col2:
        st.markdown("### ☁️ 3. Connect Google Sheets with MySQL")
        st.markdown("Choose your preferred method to sync MySQL tables to Google Sheets:")

        tab_m_wh, tab_m_sa, tab_m_jdbc = st.tabs([
            "⚡ 1-Minute Webhook (No Google Cloud Required)",
            "🔑 Service Account JSON (`gspread`)",
            "🌐 Apps Script JDBC"
        ])

        with tab_m_wh:
            st.markdown("""
            **Fastest Method — Zero Google Cloud setup required:**
            1. Open a blank [Google Sheet](https://sheets.new).
            2. Click **Extensions** > **Apps Script**.
            3. Paste the code below and click **Deploy > New deployment**:
               - Select type: **Web app**
               - Execute as: **Me**
               - Who has access: **Anyone**
            4. Copy the **Web App URL** and paste it below.
            """)
            st.code("""function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var tables = data.tables;
    for (var tbl in tables) {
      var ws = ss.getSheetByName(tbl);
      if (!ws) { ws = ss.insertSheet(tbl); }
      ws.clear();
      var rows = tables[tbl];
      if (rows && rows.length > 0) {
        ws.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
      }
    }
    return ContentService.createTextOutput("SUCCESS");
  } catch(err) {
    return ContentService.createTextOutput("ERROR: " + err.message);
  }
}""", language="javascript")
            wh_url = st.text_input("Apps Script Web App URL", value=cfg.get("webhook_url", ""), placeholder="https://script.google.com/macros/s/.../exec", key="mysql_wh_url")
            if st.button("🚀 Sync MySQL to Google Sheet via Webhook", type="primary"):
                if not wh_url.strip():
                    st.error("Please paste your Web App URL above.")
                else:
                    with st.spinner("Pushing all 8 MySQL 3NF tables to your Google Sheet..."):
                        ok, msg, rows = mysql_manager.sync_mysql_via_webhook(
                            f_host, f_port, f_user, f_pass, f_db, wh_url.strip()
                        )
                        if ok:
                            st.success(f"🎉 {msg}")
                        else:
                            st.error(f"❌ {msg}")

            if st.button("🧪 Live Viva Demo: Insert Test Student & Sync Now"):
                if not wh_url.strip():
                    st.error("Please provide your Web App URL.")
                else:
                    try:
                        import pymysql
                        conn = pymysql.connect(host=f_host, port=int(f_port), user=f_user, password=f_pass, database=f_db, autocommit=True)
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM students WHERE roll_no = '21CS999';")
                            cur.execute("""
                                INSERT INTO students (roll_no, full_name, email, phone, department, admission_year, current_status)
                                VALUES ('21CS999', '✨ Live Viva Verification Student', 'viva_test@college.edu', '9999888877', 'Computer Science & Engineering', 2024, 'Active');
                            """)
                        conn.close()
                        ok, msg, rows = mysql_manager.sync_mysql_via_webhook(f_host, f_port, f_user, f_pass, f_db, wh_url.strip())
                        if ok:
                            st.success("✅ Live test student '21CS999 - ✨ Live Viva Verification Student' inserted into MySQL and synced to Google Sheets! Switch to your Google Sheet tab 'students' to see it.")
                        else:
                            st.error(msg)
                    except Exception as e:
                        st.error(f"Test error: {e}")

        with tab_m_sa:
            st.markdown("""
            **Google Cloud Service Account Method (`gspread`):**
            Requires a `service_account.json` file in your project folder.
            """)
            s_sheet_id = st.text_input("Google Spreadsheet ID", value=sync_engine.get_configured_sheet_id(), key="mysql_sheet_id")
            if st.button("Push MySQL Data via Service Account", key="btn_sa_sync"):
                if not s_sheet_id.strip():
                    st.error("Spreadsheet ID is required.")
                else:
                    with st.spinner("Connecting to MySQL and streaming tables to Google Sheets..."):
                        ok, msg, count = mysql_manager.sync_mysql_to_google_sheets(
                            f_host, f_port, f_user, f_pass, f_db, s_sheet_id.strip()
                        )
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)

        with tab_m_jdbc:
            st.markdown("""
            **Direct Connection from Google Sheets using Google Apps Script (JDBC):**
            Google Sheets includes a native `Jdbc` service to connect directly to MySQL databases.
            """)

            st.code(f"""function importFromMySQL() {{
  var conn = Jdbc.getConnection(
    "jdbc:mysql://<PUBLIC_IP_OR_TUNNEL>:3306/{f_db}",
    "{f_user}",
    "YOUR_PASSWORD"
  );
  var stmt = conn.createStatement();
  var rs = stmt.executeQuery("SELECT * FROM students");
  
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.clear();
  
  // Write Headers
  var meta = rs.getMetaData();
  var cols = meta.getColumnCount();
  var headers = [];
  for (var i = 1; i <= cols; i++) headers.push(meta.getColumnName(i));
  sheet.appendRow(headers);
  
  // Write Data
  while (rs.next()) {{
    var row = [];
    for (var i = 1; i <= cols; i++) row.push(rs.getString(i));
    sheet.appendRow(row);
  }}
  rs.close(); stmt.close(); conn.close();
}}""", language="javascript")
            st.caption("Note: Google's cloud servers require a publicly accessible IP or tunnel (e.g. ngrok: `ngrok tcp 3306`) to reach a local computer. That's why Method A (Python local bridge) is the standard and easiest.")

    st.markdown("---")
    st.markdown("### 💻 Interactive MySQL SQL Console")
    st.caption("Execute custom SQL queries directly against the connected MySQL database `student_progression_db`.")
    user_sql = st.text_area(
        "SQL Query",
        value="SELECT s.roll_no, s.full_name, s.department, se.semester_no, se.sgpa, se.cgpa\nFROM students s\nJOIN semesters se ON se.student_id = s.student_id\nORDER BY s.roll_no, se.semester_no;",
        height=120
    )
    if st.button("▶️ Execute MySQL Query", type="primary"):
        if not user_sql.strip():
            st.error("Query cannot be empty.")
        else:
            try:
                import pymysql
                mconn = pymysql.connect(host=f_host, port=int(f_port), user=f_user, password=f_pass, database=f_db)
                if user_sql.strip().upper().startswith("SELECT") or user_sql.strip().upper().startswith("SHOW") or user_sql.strip().upper().startswith("DESCRIBE"):
                    res_df = pd.read_sql(user_sql, mconn)
                    st.success(f"Query returned {len(res_df)} rows.")
                    rdf(res_df)
                else:
                    with mconn.cursor() as cur:
                        affected = cur.execute(user_sql)
                        mconn.commit()
                    st.success(f"Query executed successfully! Affected rows: {affected}")
                mconn.close()
            except Exception as e:
                st.error(f"SQL Error: {str(e)}")
