import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ૧. આ લાઈન સૌથી ઉપર અને એકદમ સાફ હોવી જોઈએ
st.set_page_config(page_title="ORIX Smart Factory", layout="wide")

# CSS - બધું હાઈડ કરવા માટે
hide_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

LOG_FILE = "motor_logs.csv"
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "janit/motor/data"

# MQTT on_message
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        st.session_state.temp = float(data.get('temp', 0))
        st.session_state.sound = float(data.get('sound', 0))
        st.session_state.new_data_arrived = True 
    except Exception as e:
        print(f"MQTT Error: {e}")

# Save function
def save_to_csv_and_update_history():
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    new_row = pd.DataFrame([[now, temp, sound]], columns=['Date-time', 'Temperature', 'sound_level'])
    if 'history' not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

# Initialize state
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0

# MQTT setup
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# Process new data
if st.session_state.get('new_data_arrived', False):
    save_to_csv_and_update_history() 
    st.session_state.new_data_arrived = False

st.title("🏭 ORIX Smart Factory Dashboard")

# Sidebar
st.sidebar.image("1000046431.png", use_container_width=True)
points = st.sidebar.slider("Graph Points", 10, 100, 20)

# Main Logic
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Temp", f"{last_temp}°C")
    with col2: st.metric("Max Temp", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("Min Temp", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("Sound Level", f"{last_sound}dB")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], name='Temp'))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], name='Sound'))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ Waiting for ORIX data...")

time.sleep(2)
st.rerun()
