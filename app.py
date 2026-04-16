import streamlit as st
import pandas as pd
import sqlite3
import random
import qrcode
from PIL import Image  # BŪTINA ŠIAI KLAIDAI IŠTAISYTI
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib import colors

# --- 1. DATABASE SETUP ---
def create_db():
    with sqlite3.connect('danavis_system.db') as conn:
        c = conn.cursor()
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

# --- 2. PATAISYTA STICKER GENERATION FUNKCIJA ---
def generate_sticker(row):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A6))
    width, height = landscape(A6)
    
    # Dizainas
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
    
    # QR KODO GENERAVIMAS (PATAISYTAS)
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(row['full_code'])
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Svarbu: konvertuojame į PIL Image objektą, kad išvengtume AttributeError
    pil_image = qr_img.convert('RGB')
    
    # Įdedame QR kodą
    p.drawInlineImage(pil_image, width - 100, 30, width=80, height=80)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 3. UI SETUP ---
st.set_page_config(page_title="Danavis Logistics", layout="wide")
create_db()

operators = ["V.Palec", "J.Jonaitis", "P.Petraitis", "S.Beržas"]
customers = ["L-L", "L-R"]

def apply_custom_styling(row):
    styles = [''] * len(row)
    if row.get('Found_in_Excel') == True: 
        styles = ['background-color: #d4edda'] * len(row)
    elif row.get('is_manual') == 1: 
        styles = ['background-color: #d1ecf1'] * len(row)
    return styles

st.title("🌲 Danavis Engineering Logistics")

with sqlite3.connect('danavis_system.db') as conn:
    df_all = pd.read_sql_query("SELECT * FROM weighings ORDER BY id DESC", conn)

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 User")
    current_user = st.selectbox("Select Operator", operators)
    st.divider()
    st.header("🚚 New Arrival")
    plate_in = st.text_input("Truck License Plate")
    wb_in = st.text_input("Way Bill Number")
    c1, c2 = st.columns(2)
    cust_in = c1.selectbox("Customer", customers)
    sample_no_in = c2.text_input("Sample No.", value="01")
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
            st.rerun()

    st.divider()
    if st.button("🤖 Generate Simulation", use_container_width=True):
        pl_sim = f"SIM-{random.randint(1000, 9999)}"
        with sqlite3.connect('danavis_system.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO weighings (plate_number, waybill_number, sample_number, customer, gross, volume, sampling_method, operator_name, status, timestamp, is_manual) 
                              VALUES (?, 'SRM-SIM', '01', 'L-L', 42.15, 92, 'AB Truck', 'V.Palec', 'IN_PROGRESS', ?, 0)""",
                           (pl_sim, datetime.now().strftime("%Y-%m-%d %H:%M")))
            new_id = cursor.lastrowid
            cursor.execute("UPDATE weighings SET full_code=? WHERE id=?", (f"L-L-01-{datetime.now().strftime('%d-%m-%Y')}/{new_id}", new_id))
        st.rerun()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Terminal", "🛠️ Edit / Archive", "📈 Reports"])

with tab1:
    col_scales, col_print = st.columns([2, 1])
    with col_scales:
        st.subheader("🏗️ Active (On Scales)")
        active_df = df_all[df_all['status'] == 'IN_PROGRESS']
        for _, row in active_df.iterrows():
            with st.container(border=True):
                st.markdown(f"### 🚛 {row['plate_number']}")
                c1, c2 = st.columns(2)
                edit_g = c1.number_input("Weight IN", value=float(row['gross']), key=f"g_{row['id']}")
                edit_out = c2.number_input("Weight OUT", value=0.0, key=f"o_{row['id']}")
                if st.button("FINISH WEIGHING", key=f"btn_{row['id']}", use_container_width=True):
                    with sqlite3.connect('danavis_system.db') as conn:
                        conn.execute("UPDATE weighings SET gross=?, tare=?, net=?, status='COMPLETED' WHERE id=?", (edit_g, edit_out, abs(edit_g-edit_out), row['id']))
                    st.rerun()

    with col_print:
        st.subheader("🖨️ Print Label")
        hist_df = df_all[df_all['status'] == 'COMPLETED'].copy()
        if not hist_df.empty:
            hist_df['display_name'] = hist_df['plate_number'] + " (" + hist_df['full_code'] + ")"
            selected_truck = st.selectbox("Select truck:", hist_df['display_name'].tolist())
            if selected_truck:
                r = hist_df[hist_df['display_name'] == selected_truck].iloc[0]
                pdf_file = generate_sticker(r)
                st.download_button("📥 DOWNLOAD PDF LABEL", pdf_file, f"Label_{r['plate_number']}.pdf", "application/pdf", use_container_width=True)

    st.divider()
    if not hist_df.empty:
        st.dataframe(hist_df.drop(columns=['display_name']).style.apply(apply_custom_styling, axis=1), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("🛠️ Manual Edit")
    if not df_all.empty:
        sel_id = st.selectbox("Select ID", df_all['id'].tolist())
        curr = df_all[df_all['id'] == sel_id].iloc[0]
        with st.form("edit_form"):
            u_plate = st.text_input("Plate", curr['plate_number'])
            u_in = st.number_input("Weight In", float(curr['gross']))
            u_out = st.number_input("Weight Out", float(curr['tare']))
            if st.form_submit_button("Save Changes"):
                with sqlite3.connect('danavis_system.db') as conn:
                    conn.execute("UPDATE weighings SET plate_number=?, gross=?, tare=?, net=?, is_manual=1 WHERE id=?", (u_plate, u_in, u_out, abs(u_in-u_out), sel_id))
                st.rerun()

with tab3:
    st.title("📊 Report Management")
    if not df_all.empty:
        report_type = st.radio("Type:", ["Daily Report", "Weekly Report"], horizontal=True)
        df_reports = df_all.copy()
        df_reports['timestamp_dt'] = pd.to_datetime(df_reports['timestamp'], errors='coerce')

        if report_type == "Daily Report":
            report_date = st.date_input("Date", datetime.now())
            final_df = df_reports[(df_reports['status'] == 'COMPLETED') & (df_reports['timestamp_dt'].dt.date == report_date)].copy()
            st.dataframe(final_df.style.apply(apply_custom_styling, axis=1), use_container_width=True)
        else:
            w_col1, w_col2 = st.columns(2)
            week_date = w_col1.date_input("Select week:", datetime.now())
            uploaded_file = w_col2.file_uploader("📥 Import Excel", type=['xlsx'])
            weekly_data = df_reports[(df_reports['status'] == 'COMPLETED') & (df_reports['timestamp_dt'].dt.isocalendar().week == week_date.isocalendar()[1])].copy()
            if not weekly_data.empty:
                weekly_data['Found_in_Excel'] = False
                if uploaded_file:
                    try:
                        extra_df = pd.read_excel(uploaded_file)
                        if 'Full code' in extra_df.columns:
                            codes = extra_df['Full code'].astype(str).str.strip().unique()
                            weekly_data['Found_in_Excel'] = weekly_data['full_code'].astype(str).str.strip().isin(codes)
                    except Exception as e: st.error(f"Error: {e}")
                st.dataframe(weekly_data.style.apply(apply_custom_styling, axis=1), use_container_width=True, hide_index=True)
