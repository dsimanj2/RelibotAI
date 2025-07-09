from supabase import create_client, Client
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# --- Setup ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="ReliBotAI - Asset & Log Manager", layout="wide")
st.title("🛠️ Asset & Failure Log Manager")

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 📤 Upload Failure Logs")
    
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    confirm_upload = st.checkbox("✅ Confirm upload operation", key="confirm_upload")

if "uploaded_df" in st.session_state and not st.session_state.uploaded_df.empty:
    df = st.session_state.uploaded_df

    st.markdown("### 📥 Upload Data to Supabase")
    if st.button("🚀 Send to Supabase"):
        try:
            asset_id_map = {}
            for asset_name in df["asset_name"].unique():
                row = df[df["asset_name"] == asset_name].iloc[0]
                res = supabase.table("assets").insert({
                    "name": asset_name,
                    "category": row["category"],
                    "location": row["location"],
                    "deleted": False
                }).execute()
                if res.data:
                    asset_id_map[asset_name] = res.data[0]["id"]

            logs = []
            for _, row in df.iterrows():
                asset_id = asset_id_map.get(row["asset_name"])
                if asset_id:
                    logs.append({
                        "asset_id": asset_id,
                        "event_type": row["event_type"],
                        "event_time": pd.to_datetime(row["event_time"]).isoformat(),
                        "failure_mode": row["failure_mode"],
                        "description": row.get("description", ""),
                        "deleted": False
                    })

            if logs:
                supabase.table("logs").insert(logs).execute()
                st.success(f"✅ Uploaded {len(logs)} log entries to Supabase.")
            else:
                st.warning("⚠️ No log entries prepared.")
        except Exception as e:
            st.error(f"❌ Upload to Supabase failed: {e}")    


    if uploaded_file and confirm_upload:
        try:
            # Get raw file content
            file_content = uploaded_file.getvalue()

            if len(file_content) == 0:
                st.error("❌ Uploaded file is empty.")
            else:
                # 👇 Insert here to debug raw content
                st.write(file_content[:500])

                # Try reading the CSV
                df = pd.read_csv(uploaded_file, encoding="utf-8", sep=None, engine="python")

                if df.empty:
                    st.error("❌ CSV file has no rows or columns.")
                else:
                    df["event_time"] = pd.to_datetime(df["event_time"], format="mixed", errors="coerce")
                    df = df.dropna(subset=["event_time"])
                    st.session_state.uploaded_df = df
                    st.success(f"✅ Uploaded {len(df)} log entries.")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

st.sidebar.markdown("---")
st.sidebar.subheader("📤 Export Data")

if st.sidebar.button("⬇️ Export Logs & Stats to Excel"):
    try:
        with pd.ExcelWriter("reli_logs_export.xlsx", engine="xlsxwriter") as writer:
            df_logs.to_excel(writer, sheet_name="Failure Logs", index=False)
            if 'stats_df' in locals():
                stats_df.to_excel(writer, sheet_name="MTBF_MTTR", index=False)
        with open("reli_logs_export.xlsx", "rb") as f:
            st.sidebar.download_button(
                label="📥 Download Excel File",
                data=f,
                file_name="reli_logs_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.sidebar.error(f"❌ Excel Export failed: {e}")

# --- Clear DB (Soft Delete) with Confirmation ---
st.sidebar.markdown("---")
st.sidebar.subheader("🧹 Database Management")

confirm_clear = st.sidebar.checkbox("Confirm clear operation", key="confirm_clear")
if st.sidebar.button("🧹 Clear Supabase DB", key="clear_db_button"):
    if confirm_clear:
        try:
            # Soft delete (mark records)
            supabase.table("logs").update({"deleted": True}).neq("id", "").execute()
            supabase.table("assets").update({"deleted": True}).neq("id", "").execute()
            st.sidebar.success("✅ All records marked as deleted.")
        except Exception as e:
            st.sidebar.error(f"Failed to soft-delete: {e}")
    else:
        st.sidebar.warning("Please check 'Confirm clear operation' first.")

# --- Upload to Supabase ---
if uploaded_file and st.sidebar.button("⬆️ Upload to Supabase", key="upload_db"):
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["event_time"])
        df.fillna("", inplace=True)  # 🔧 Prevent JSON NaN error
        asset_id_map = {}

        for asset_name in df["asset_name"].unique():
            asset_row = df[df["asset_name"] == asset_name].iloc[0]
            response = supabase.table("assets").insert({
                "name": asset_name,
                "category": asset_row["category"],
                "location": asset_row["location"],
                "deleted": False
            }).execute()
            if response.data:
                asset_id_map[asset_name] = response.data[0]["id"]

        log_entries = []
        for _, row in df.iterrows():
            asset_id = asset_id_map.get(row["asset_name"])
            if asset_id:
                log_entries.append({
                    "asset_id": asset_id,
                    "event_type": row["event_type"],
                    "event_time": pd.to_datetime(row["event_time"], format="ISO8601", errors="coerce").isoformat(),
                    "failure_mode": row["failure_mode"],
                    "description": row["description"],
                    "deleted": False
                })
        if log_entries:
            df.fillna("", inplace=True)  # Replace NaNs with empty string
            supabase.table("logs").insert(log_entries).execute()
            st.success(f"✅ Uploaded {len(log_entries)} log entries.")
        else:
            st.warning("No logs uploaded.")
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")

# --- Export to Excel ---
if st.sidebar.button("⬇️ Export Logs to Excel", key="export_logs"):
    try:
        logs = supabase.table("logs").select("*").is_("deleted", False).execute()
        df_export = pd.DataFrame(logs.data)
        df_export.to_excel("logs_export.xlsx", index=False)
        with open("logs_export.xlsx", "rb") as f:
            st.sidebar.download_button("📥 Download Excel", f, file_name="logs_export.xlsx", key="download_excel")
    except Exception as e:
        st.error(f"❌ Export failed: {e}")

# --- Filters ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filter Logs")
selected_asset = st.sidebar.text_input("Asset Name (optional)", key="filter_asset")
start_date = st.sidebar.date_input("Start Date", key="filter_start")
end_date = st.sidebar.date_input("End Date", key="filter_end")

# --- Load & Filter Data ---
logs_data = supabase.table("logs").select("*").is_("deleted", False).execute()
assets_data = supabase.table("assets").select("*").is_("deleted", False).execute()
df_logs = pd.DataFrame(logs_data.data)
df_assets = pd.DataFrame(assets_data.data)

if not df_logs.empty:
    df_logs["event_time"] = pd.to_datetime(df_logs["event_time"], format="ISO8601", errors="coerce")
    df_logs.dropna(subset=["event_time"], inplace=True)
    if selected_asset:
        asset_ids = df_assets[df_assets["name"] == selected_asset]["id"].values
        if asset_ids.any():
            df_logs = df_logs[df_logs["asset_id"] == asset_ids[0]]
    df_logs = df_logs[
        (df_logs["event_time"].dt.date >= start_date) &
        (df_logs["event_time"].dt.date <= end_date)
    ]

# --- Display Tables ---
st.subheader("📋 Assets")
st.dataframe(df_assets)

st.subheader("📋 Failure Logs")
st.dataframe(df_logs)

st.write("🔍 Debug Logs:", df_logs.shape)
st.write(df_logs.head())
# --- Pareto Chart ---
st.subheader("📊 Pareto Chart of Failure Modes")
if not df_logs.empty:
    pareto_df = df_logs["failure_mode"].value_counts().reset_index()
    pareto_df.columns = ["Failure Mode", "Count"]
    chart = alt.Chart(pareto_df).mark_bar().encode(
        x=alt.X("Failure Mode", sort="-y"),
        y="Count"
    )
    st.altair_chart(chart, use_container_width=True)

# --- MTBF & MTTR ---
st.subheader("🧮 MTBF and MTTR per Asset")
def calculate_mtbf_mttr(df_logs):
    df_logs["event_time"] = pd.to_datetime(df_logs["event_time"], format="ISO8601", errors="coerce")
    df_logs.dropna(subset=["event_time"], inplace=True)
    results = []
    for asset_id in df_logs["asset_id"].unique():
        asset_logs = df_logs[df_logs["asset_id"] == asset_id].sort_values("event_time")
        failure_times = asset_logs[asset_logs["event_type"] == "failure"]["event_time"]
        repair_times = asset_logs[asset_logs["event_type"] == "repair"]["event_time"]

        if len(failure_times) >= 2:
            mtbf = (failure_times.diff().dropna().mean()).total_seconds() / 3600
        else:
            mtbf = None

        if len(repair_times) >= 1 and len(failure_times) == len(repair_times):
            mttr = (repair_times.values - failure_times.values).mean().astype("timedelta64[h]").item().total_seconds() / 3600
        else:
            mttr = None

        results.append({
            "Asset ID": asset_id,
            "MTBF (hrs)": round(mtbf, 2) if mtbf else "N/A",
            "MTTR (hrs)": round(mttr, 2) if mttr else "N/A"
        })
    return pd.DataFrame(results)

if not df_logs.empty:
    stats_df = calculate_mtbf_mttr(df_logs)
    st.dataframe(stats_df)

    # --- Export to PDF summary ---
    from fpdf import FPDF

    if st.sidebar.button("⬇️ Export PDF Summary"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "ReliBotAI Failure Summary Report", ln=True)

            pdf.set_font("Arial", size=10)
            pdf.ln(5)
            pdf.cell(0, 10, f"Total Failure Logs: {len(df_logs)}", ln=True)

            if not stats_df.empty:
                pdf.ln(5)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "MTBF & MTTR per Asset", ln=True)
                pdf.set_font("Arial", size=10)
                for _, row in stats_df.iterrows():
                    pdf.cell(0, 10,
                             f"Asset {row['Asset ID']} - MTBF: {row['MTBF (hrs)']}, MTTR: {row['MTTR (hrs)']}",
                             ln=True)

            pdf.output("reli_report.pdf")
            with open("reli_report.pdf", "rb") as f:
                st.sidebar.download_button("📄 Download PDF Report", f, file_name="reli_report.pdf")

        except Exception as e:
            st.sidebar.error(f"❌ PDF Export failed: {e}")
