import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random
import qrcode
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6
from reportlab.lib import colors

# --- 1. DATABASE SETUP ---
def create_db():
    conn = sqlite3.connect('danavis_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS weighings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  plate_number TEXT, 
                  gross REAL, 
                  tare REAL, 
                  net REAL, 
                  timestamp DATETIME)''')
    conn.commit()
    conn.close()

def add_test_record():
    conn = sqlite3.connect('danavis_system.db')
    c = conn.cursor()
    plate = f"{random.choice(['DAN', 'LOG', 'ENG'])}-{random.randint(100, 999)}"
    gross = random.randint(25000, 42000)
    tare = random.randint(12000, 16000)
    net = gross - tare
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO weighings (plate_number, gross, tare, net, timestamp) VALUES (?, ?, ?, ?, ?)",
              (plate, gross, tare, net, time_now))
    conn.commit()
    conn.close()

# --- 2. PDF GENERATION (DANAVIS DESIGN) ---
def generate_danavis_pdf(row):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A6)
    width, height = A6

    # Danavis Blue Header Box
    p.setFillColorRGB(0.0, 0.29, 0.6) # Tamsiai mėlyna (#004a99-ish)
    p.rect(0, height - 60, width, 60, fill=1)
    
    # Header Text
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 35, "DANAVIS ENGINEERING")
    p.setFont("Helvetica", 10)
    p.drawCentredString(width/2, height - 50, "Official Weighing Receipt")

    # Body Text
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(30, height - 90, f"Truck Plate: {row['plate_number']}")
    p.setFont("Helvetica", 9)
    p.drawString(30, height - 105, f"Date/Time: {row['timestamp']}")
    p.line(30, height - 115, width - 30, height - 115)

    # Weights
    p.drawString(30, height - 140, f"Gross Weight:")
    p.drawRightString(width - 30, height - 140, f"{row['gross']} kg")
    
    p.drawString(30, height - 155, f"Tare Weight:")
    p.drawRightString(width - 30, height - 155, f"{row['tare']} kg")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(30, height - 180, f"TOTAL NET:")
    p.drawRightString(width - 30, height - 180, f"{row['net']} kg")

    # QR Code
    qr_data = f"Danavis-ENG ID:{row['id']} | Plate:{row['plate_number']} | Net:{row['net']}kg"
    qr = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    from reportlab.lib.utils import ImageReader
    p.drawImage(ImageReader(qr_buffer), (width/2)-40, 20, width=80, height=80)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# --- 3. WEB INTERFACE (STREAMLIT + CSS) ---
st.set_page_config(page_title="Danavis Engineering Terminal", layout="wide")

# Custom CSS for Danavis Branding
st.markdown("""
    <style>
    /* Pagrindinis fonas */
    .main { background-color: #f8f9fa; }
    
    /* Antraštė */
    h1 { color: #004a99; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800; border-bottom: 2px solid #004a99; padding-bottom: 10px; }
    
    /* Metrikų kortelės */
    [data-testid="stMetricValue"] { color: #004a99; font-weight: bold; }
    .stMetric { background-color: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #004a99; }
    
    /* Mygtukai */
    .stButton>button { background-color: #004a99; color: white; border-radius: 2px; border: none; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #003366; border: none; color: white; }
    
    /* Sidebar */
    .css-1639116 { background-color: #f1f3f5; }
    </style>
    """, unsafe_allow_html=True)

create_db()

st.title("🌲 Danavis Engineering Logistics Terminal")
st.markdown("Automated weighing system for biomass and wood chips.")

# --- SIDEBAR & STATS ---
with st.sidebar:
    st.image("https://www.danavisengineering.com/wp-content/uploads/2021/04/danavis-logo.png", width=200) # Bandome užkrauti logo jei URL teisingas
    st.header("Control Panel")
    if st.button("➕ Add New Shipment"):
        add_test_record()
        st.success("Record created!")
        st.rerun()

# Load Data
conn = sqlite3.connect('danavis_system.db')
df = pd.read_sql_query("SELECT * FROM weighings ORDER BY timestamp DESC", conn)
conn.close()

if not df.empty:
    # KPI Stats
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Loadings", len(df))
    with m2: st.metric("Current Truck", df['plate_number'].iloc[0])
    with m3: st.metric("Last Net (kg)", f"{df['net'].iloc[0]}")

    st.divider()

    # Layout: Search and PDF Receipt
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        search = st.text_input("🔍 Search Plate Number", "")
        if search:
            df = df[df['plate_number'].str.contains(search, case=False)]
        
        st.subheader("📋 Shipment History")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("🖨️ Receipt Center")
        selected_id = st.selectbox("Select Shipment ID", df['id'].tolist())
        if selected_id:
            row_data = df[df['id'] == selected_id].iloc[0]
            pdf_data = generate_danavis_pdf(row_data)
            st.download_button(
                label=f"📥 Download Receipt ({row_data['plate_number']})",
                data=pdf_data,
                file_name=f"danavis_receipt_{row_data['id']}.pdf",
                mime="application/pdf"
            )
else:
    st.info("No shipments found. Please add a record using the sidebar.")