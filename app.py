import streamlit as st
import pandas as pd
import sqlite3
import random
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib import colors

# --- 1. DATABASE SETUP ---
def create_db():
    # Naudojame context manager užtikrinti, kad jungtis užsidarytų
    with sqlite3.connect('danavis_system.db') as conn:
        c = conn.cursor()
        # Sukuriame lentelę su visais reikiamais stulpeliais iškart
        c.execute('''CREATE TABLE IF NOT EXISTS weighings 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      plate_number TEXT,
                      waybill_number TEXT,
                      sample_number TEXT,
                      customer TEXT,
                      full_code TEXT,
                      gross REAL DEFAULT 0, 
                      tare REAL DEFAULT 0, 
                      net REAL DEFAULT 0, 
                      volume REAL DEFAULT 0,
                      sampling_done TEXT DEFAULT 'No',
                      sampling_method TEXT,
                      operator_name TEXT,
                      status TEXT,
                      is_manual INTEGER DEFAULT 0,
                      timestamp DATETIME)''')
        
        # Patikriname ar yra specifiniai stulpeliai (jei DB buvo sukurta seniau)
        columns_to_add = {"customer": "TEXT", "full_code": "TEXT", "is_manual": "INTEGER DEFAULT 0"}
        c.execute("PRAGMA table_info(weighings)")
        existing = [info[1] for info in c.fetchall()]
        for col, col_type in columns_to_add.items():
            if col not in existing:
                c.execute(f"ALTER TABLE weighings ADD COLUMN {col} {col_type}")
        conn.commit()

def generate_full_code(customer, sample_no):
    now = datetime.now()
    week_no = now.isocalendar()[1]
    date_str = now.strftime("%d-%m-%Y")
    return f"{customer}-{week_no:02d}-{sample_no}-{date_str}"

# --- 2. STICKER GENERATION ---
def generate_sticker(row):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A6))
    width, height = landscape(A6)
    p.setFillColorRGB(0.0, 0.29, 0.6)
    p.rect(0, height - 40, width, 40, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(20, height - 25, "DANAVIS ENGINEERING - RECEIPT")
    p.setFillColor(colors.black)
    p.setFont("Helvetica", 10)
    p.drawString(20, height - 60, f"Truck: {row['plate_number']} | Customer: {row['customer']}")
    p.drawString(20, height - 75, f"Full Code: {row['full_code']}")
    p.line(20, height - 85, width - 20, height - 85)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(20, height - 105, f"CARGO NET: {row.get('net', 0):.3f} mt")
    p.drawString(20, height - 120, f"VOLUME: {row.get('volume', 0)} m3")
    p.setFont("Helvetica", 8)
    p.drawString(20, 15, f"Operator: {row['operator_name']} | Time: {row['timestamp']}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 3. UI SETUP ---
st.set_page_config(page_title="Danavis Logistics", layout="wide")

# Svarbu: paleidžiame DB kūrimą prieš bet kokią užklausą
create_db()

operators = ["V.Palec", "J.Jonaitis", "P.Petraitis", "S.Beržas"]
customers = ["L-L", "L-R"]

def apply_custom_styling(row):
    styles = [''] * len(row)
    if row.get('Found_in_Excel', False): 
        styles = ['background-color: #d4edda'] * len(row) # Green
    elif row.get('is_manual') == 1: 
        styles = ['background-color: #d1ecf1'] * len(row) # Blue
    return styles

st.title("🌲 Danavis Engineering Logistics")

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 User")
    current_user = st.selectbox("Select Operator", operators)
    st.divider()
    
    st.header("🚚 New Arrival")
    plate_in = st.text_input("Truck License Plate")
    wb_in = st.text_input("Way Bill Number")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cust_in = st.selectbox("Customer", customers)
    with col_c2:
        sample_no_in = st.text_input("Sample No.", value="01")
    
    gross_in = st.number_input("Weight IN (mt)", min_value=0.0, format="%.3f")
    vol_in = st.number_input("Volume (m3)", min_value=0)
    method_in = st.selectbox("Sampling Method", ["AB Truck", "Manual", "Automatic", "None"])

    if st.button("Register Entrance", use_container_width=True):
        if plate_in and wb_in:
            base_code = generate_full_code(cust_in, sample_no_in)
            with sqlite3.connect('danavis_system.db') as conn:
                cursor = conn.cursor()
                cursor.execute("""INSERT INTO weighings 
                    (plate_number, waybill_number, sample_number, customer, gross, volume, sampling_method, operator_name, status, timestamp, is_manual) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (plate_in, wb_in, sample_no_in, cust_in, gross_in, vol_in, method_in, current_user, 'IN_PROGRESS', datetime.now().strftime("%Y-%m-%d %H:%M")))
                new_id = cursor.lastrowid
                final_code = f"{base_code}/{new_id}"
                cursor.execute("UPDATE weighings SET full_code=? WHERE id=?", (final_code, new_id))
            st.success(f"Registered! Code: {final_code}")
            st.rerun()

    st.divider()
    if st.button("🤖 Generate Simulation", use_container_width=True):
        pl_sim = f"SIM-{random.randint(1000, 9999)}"
        cust_sim = random.choice(customers)
        samp_sim = f"{random.randint(1, 20):02d}"
        with sqlite3.connect('danavis_system.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO weighings 
                (plate_number, waybill_number, sample_number, customer, gross, volume, sampling_method, operator_name, status, timestamp, is_manual) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (pl_sim, "SRM-SIM", samp_sim, cust_sim, 42.150, 92, "AB Truck", "V.Palec", 'IN_PROGRESS', datetime.now().strftime("%Y-%m-%d %H:%M")))
            new_id = cursor.lastrowid
            cursor.execute("UPDATE weighings SET full_code=? WHERE id=?", (generate_full_code(cust_sim, samp_sim)+f"/{new_id}", new_id))
        st.rerun()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Terminal", "🛠️ Edit / Archive", "📈 Reports"])

# Užkrauname duomenis vieną kartą visiems tab'ams
with sqlite3.connect('danavis_system.db') as conn:
    df_all = pd.read_sql_query("SELECT * FROM weighings ORDER BY id DESC", conn)

with tab1:
    st.subheader("🏗️ Active (On Scales)")
    if not df_all.empty:
        active_df = df_all[df_all['status'] == 'IN_PROGRESS']
        if not active_df.empty:
            cols = st.columns(3)
            for idx, (_, row) in enumerate(active_df.iterrows()):
                with cols[idx % 3]:
                    is_man = row['is_manual'] == 1
                    container_title = f"🚛 {row['plate_number']}" + (" (EDITED)" if is_man else "")
                    with st.container(border=True):
                        st.markdown(f"### {container_title}")
                        st.caption(f"Code: {row['full_code']}")
                        edit_g = st.number_input("Weight IN", value=float(row['gross']), format="%.3f", key=f"g_{row['id']}")
                        edit_out = st.number_input("Weight OUT", value=0.0, format="%.3f", key=f"o_{row['id']}")
                        if st.button("FINISH WEIGHING", key=f"btn_{row['id']}", use_container_width=True):
                            neto = abs(edit_g - edit_out)
                            with sqlite3.connect('danavis_system.db') as conn:
                                conn.execute("UPDATE weighings SET gross=?, tare=?, net=?, status='COMPLETED', sampling_done='Yes' WHERE id=?", 
                                           (edit_g, edit_out, neto, row['id']))
                            st.rerun()
        else:
            st.info("No active weighings.")
    
    st.divider()
    st.subheader("📋 Recent Weighing Table")
    if not df_all.empty:
        hist_df = df_all[df_all['status'] == 'COMPLETED']
        if not hist_df.empty:
            st.caption("🔵 Blue highlight: Manually edited record")
            st.dataframe(hist_df.style.apply(apply_custom_styling, axis=1), use_container_width=True, hide_index=True)
            sel_print = st.selectbox("Select ID for Label", hist_df['id'].tolist())
            if sel_print:
                r = hist_df[hist_df['id'] == sel_print].iloc[0]
                st.download_button(f"Download {r['plate_number']} Label", generate_sticker(r), f"label_{r['id']}.pdf")

with tab2:
    st.subheader("🛠️ Manual Edit")
    if not df_all.empty:
        sel_id = st.selectbox("ID to Edit", df_all['id'].tolist(), key="edit_id_sel")
        curr = df_all[df_all['id'] == sel_id].iloc[0]
        with st.form("edit_form_final"):
            c1, c2 = st.columns(2)
            with c1:
                u_cust = st.selectbox("Customer", customers, index=customers.index(curr['customer']) if curr['customer'] in customers else 0)
                u_samp = st.text_input("Sample No", curr['sample_number'])
                u_plate = st.text_input("Plate", curr['plate_number'])
            with c2:
                u_in = st.number_input("Weight In", float(curr['gross']), format="%.3f")
                u_out = st.number_input("Weight Out", float(curr['tare']), format="%.3f")
                u_vol = st.number_input("Volume", int(curr['volume']))
            
            if st.form_submit_button("Save Changes"):
                new_code = f"{generate_full_code(u_cust, u_samp)}/{sel_id}"
                with sqlite3.connect('danavis_system.db') as conn:
                    conn.execute("""UPDATE weighings SET customer=?, sample_number=?, plate_number=?, gross=?, tare=?, net=?, volume=?, full_code=?, is_manual=1 WHERE id=?""",
                                 (u_cust, u_samp, u_plate, u_in, u_out, abs(u_in-u_out), u_vol, new_code, sel_id))
                st.success("Changes saved!")
                st.rerun()
 with tab3:
    st.title("📊 Report Management")
    if not df_all.empty:
        report_type = st.radio("Type:", ["Daily Report", "Weekly Report"], horizontal=True, key="rep_final_fixed")
        st.divider()

        df_reports = df_all.copy()
        # Sutvarkome datas, kad būtų galima filtruoti
        df_reports['timestamp_dt'] = pd.to_datetime(df_reports['timestamp'], errors='coerce')
        
        if report_type == "Daily Report":
            st.subheader("📅 Daily Summary")
            report_date = st.date_input("Date", datetime.now(), key="d_d_f_fixed")
            daily_filtered = df_reports[(df_reports['status'] == 'COMPLETED') & 
                                        (df_reports['timestamp_dt'].dt.date == report_date)].copy()
            
            if daily_filtered.empty:
                st.info("No records found for this day.")
            else:
                raw_c = daily_filtered['customer'].fillna("Undefined").unique().tolist()
                sel_c = st.selectbox("Filter by Customer:", ["All Customers"] + sorted([str(c) for c in raw_c]), key="d_c_f_fixed")
                
                final_df = daily_filtered if sel_c == "All Customers" else daily_filtered[daily_filtered['customer'] == sel_c]
                
                st.caption("🔵 Blue: Manual edit")
                st.dataframe(final_df.style.apply(apply_custom_styling, axis=1), use_container_width=True, hide_index=True)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_df.drop(columns=['timestamp_dt'], errors='ignore').to_excel(writer, index=False)
                st.download_button("📥 Download Excel", output.getvalue(), f"Daily_Report_{report_date}.xlsx", key="dl_d_fixed")

        else: # WEEKLY REPORT SU EXCEL IMPORTU
            st.subheader("📅 Weekly Summary & Verification")
            w_col1, w_col2 = st.columns(2)
            with w_col1:
                week_date = st.date_input("Select day in week:", datetime.now(), key="w_d_f_fixed")
                year, week, _ = week_date.isocalendar()
            with w_col2:
                # Štai sugrąžintas Excel įkėlimas
                uploaded_file = st.file_uploader("📥 Attach Excel to Verify Codes", type=['xlsx'], key="w_f_f_fixed")
            
            # Filtruojame savaitės duomenis
            weekly_data = df_reports[(df_reports['status'] == 'COMPLETED') & 
                                     (df_reports['timestamp_dt'].dt.isocalendar().week == week) & 
                                     (df_reports['timestamp_dt'].dt.isocalendar().year == year)].copy()
            
            if weekly_data.empty:
                st.warning("No data found for this week.")
            else:
                # Sugrąžiname palyginimo logiką
                weekly_data['Found_in_Excel'] = False
                
                if uploaded_file:
                    try:
                        extra = pd.read_excel(uploaded_file)
                        # Nuvalome tarpus nuo kodų, kad sutaptų 100%
                        weekly_data['full_code'] = weekly_data['full_code'].astype(str).str.strip()
                        
                        if 'Full code' in extra.columns:
                            extra['Full code'] = extra['Full code'].astype(str).str.strip()
                            # Pažymime tuos, kurie rasti Excel faile
                            weekly_data['Found_in_Excel'] = weekly_data['full_code'].isin(extra['Full code'].unique())
                            st.success("Excel file linked successfully! Green rows = Match found.")
                        else:
                            st.error("Uploaded Excel must have a column named 'Full code'")
                    except Exception as e:
                        st.error(f"Error reading Excel: {e}")
                
                st.caption("🟢 Green: Excel Match | 🔵 Blue: Manual edit")
                st.dataframe(weekly_data.style.apply(apply_custom_styling, axis=1), use_container_width=True, hide_index=True)
                
                wk_out = BytesIO()
                with pd.ExcelWriter(wk_out, engine='xlsxwriter') as writer:
                    # Išsaugome be pagalbinių stulpelių
                    weekly_data.drop(columns=['timestamp_dt', 'Found_in_Excel'], errors='ignore').to_excel(writer, index=False)
                st.download_button("📥 Download Weekly Excel", wk_out.getvalue(), f"Week_{week}.xlsx", key="dl_w_fixed")               
   
