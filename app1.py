import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ૧. પેજ સેટઅપ - આ લાઈન સૌથી પહેલી હોવી જોઈએ
st.set_page_config(page_title="ORIX Smart Factory", layout="wide")

# CSS - વધારાનું મેનુ હાઈડ કરવા માટે
hide_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# ૨. કોન્સ્ટન્ટ્સ
LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# ૩. MQTT ફંક્શન
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        st.session_state.new_data_arrived = True 
    except Exception as e:
        print(f"MQTT Error: {e}")

# ૪. ડેટા સેવિંગ ફંક્શન
def save_to_csv_and_update_history():
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    new_row = pd.DataFrame([[now, temp, sound]], columns=['Date-time', 'Temperature', 'sound_level'])
    
    if 'history' not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
    
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

# ૫. સ્ટેટ ઇનિશિયલાઈઝેશન
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0

# MQTT ક્લાયન્ટ સેટઅપ
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# ડેટા અપડેટ લોજિક
if st.session_state.get('new_data_arrived', False):
    save_to_csv_and_update_history() 
    st.session_state.new_data_arrived = False

# --- UI શરૂઆત ---
st.title("🏭 ORIX Smart Factory Dashboard")

# ૬. સાઈડબાર - એરર-ફ્રી ઈમેજ લોડિંગ
st.sidebar.markdown("<h2 style='text-align: center; color: gold;'>ORIX IoT</h2>", unsafe_allow_html=True)

logo_path = "1000046431.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.info("💡 લોગો ફાઈલ GitHub પર મળતી નથી, પણ એપ ચાલુ રહેશે!")

points = st.sidebar.slider("Graph Points", 10, 100, 20)

# ૭. મેઈન ગ્રાફ અને મેટ્રિક્સ
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Temp", f"{last_temp}°C")
    with col2: st.metric("Max", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("Min", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("Sound Level", f"{last_sound}dB")

    if last_temp > 75:
        st.error(f"🚨 CRITICAL ALERT: High Temp {last_temp}°C")
    else:
        st.success("✅ System Healthy")

    st.subheader("📊 Performance Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
    fig.update_layout(template='plotly_dark', hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("⌛ ORIX સેન્સરના ડેટાની રાહ જોવાય છે... મશીન ચાલુ કરો.")

# ૮. ઓટો-રિફ્રેશ
time.sleep(2)
st.rerun()
