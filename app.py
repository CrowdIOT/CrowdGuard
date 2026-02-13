import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
import plotly.express as px
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CROWDGUARD // COMMAND",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. "CRAZY" CYBERPUNK CSS STYLING ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(#111 1px, transparent 1px);
        background-size: 20px 20px;
        color: #00ff41;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Metrics Styling */
    div[data-testid="stMetricValue"] {
        font-size: 3rem;
        color: #00ff41;
        text-shadow: 0 0 10px #00ff41;
    }
    div[data-testid="stMetricLabel"] {
        color: #888;
        font-weight: bold;
    }
    
    /* Card/Container Styling */
    .css-1r6slb0, .css-12oz5g7 {
        border: 1px solid #333;
        background-color: #0a0a0a;
        padding: 20px;
        border-radius: 5px;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.1);
    }
    
    /* Buttons */
    .stButton>button {
        color: #00ff41;
        background-color: #000;
        border: 1px solid #00ff41;
        border-radius: 0px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #00ff41;
        color: black;
        box-shadow: 0 0 20px #00ff41;
    }
    
    /* Headers */
    h1, h2, h3 {
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 2px solid #333;
        padding-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE SETUP ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "data_history" not in st.session_state: st.session_state.data_history = []
if "events" not in st.session_state: st.session_state.events = []
if "latest" not in st.session_state: 
    st.session_state.latest = {"count": 0, "status": "OFFLINE", "gate": "N/A"}

# --- 4. MQTT CONNECTION (THE DATA RECEIVER) ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        st.session_state.latest = payload
        
        # Add timestamp for graph
        payload["time"] = datetime.now().strftime("%H:%M:%S")
        st.session_state.data_history.append(payload)
        
        # Keep only last 50 points
        if len(st.session_state.data_history) > 50:
            st.session_state.data_history.pop(0)
            
        # Log Critical Events
        if payload["status"] == "DANGER":
            log_entry = f"[{payload['time']}] ⚠️ SURGE DETECTED: {payload['count']} PAX"
            if not st.session_state.events or st.session_state.events[-1] != log_entry:
                st.session_state.events.append(log_entry)
                
    except:
        pass

# Only connect if not already connected (prevents multiple connections on rerun)
if "mqtt_client" not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect("broker.hivemq.com", 1883, 60)
        client.subscribe("crowdguard/system/data")
        client.loop_start()
        st.session_state.mqtt_client = client
    except:
        st.toast("⚠️ Network Offline")

# --- 5. THE LOGIN PAGE ---
def login_page():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.title("🔒 SECURE ACCESS")
        st.markdown("Enter credentials to access CrowdGuard Neural Network.")
        
        user = st.text_input("AGENT ID")
        pw = st.text_input("ACCESS CODE", type="password")
        
        if st.button("AUTHENTICATE"):
            if user == "admin" and pw == "admin":  # Simple login for demo
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("ACCESS DENIED")

# --- 6. THE DASHBOARD PAGE ---
def dashboard_page():
    # Top Bar
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("🛡️ CROWDGUARD // LIVE FEED")
    with c2:
        if st.button("LOGOUT"):
            st.session_state.logged_in = False
            st.rerun()

    # Live Metrics
    data = st.session_state.latest
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LIVE COUNT", f"{data['count']}")
    m2.metric("ZONE STATUS", data["status"])
    m3.metric("GATE LOCK", data["gate"])
    m4.metric("SYSTEM UPTIME", "99.9%")

    # Alert Banner
    if data["status"] == "DANGER":
        st.error(f"🚨 CRITICAL ALERT: CROWD SURGE DETECTED! GATES OPENING AUTOMATICALLY.")
        # Trigger audio visual alert effect
        st.markdown("""
            <div style="background-color:rgba(255,0,0,0.2); padding:20px; border: 1px solid red; text-align:center;">
            <h1>⚠️ EVACUATE ⚠️</h1>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider()

    # Charts & Logs
    g1, g2 = st.columns([2, 1])
    
    with g1:
        st.subheader("📊 DENSITY ANALYTICS")
        if st.session_state.data_history:
            df = pd.DataFrame(st.session_state.data_history)
            fig = px.area(df, x="time", y="count", template="plotly_dark")
            fig.update_traces(line_color='#00ff41', fillcolor='rgba(0, 255, 65, 0.2)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("WAITING FOR DATA STREAM...")

    with g2:
        st.subheader("📝 EVENT LOG")
        log_box = st.container(height=300)
        with log_box:
            for event in reversed(st.session_state.events):
                st.code(event, language="bash")

    # Auto-refresh logic (keeps the dashboard alive)
    time.sleep(1)
    st.rerun()

# --- 7. MAIN APP ROUTER ---
if st.session_state.logged_in:
    dashboard_page()
else:
    login_page()