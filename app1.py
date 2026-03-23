import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import json
import paho.mqtt.client as mqtt
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ૧. પેજ સેટઅપ (આખા કોડમાં સૌથી પહેલી લાઈન)

# CSS - વધારાનું મેનુ હાઈડ કરવા માટે
hide_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stStatusWidget"] {visibility: hidden;}
.viewerBadge_container__1QS13 {display: none !important;}
div.stDeployButton {display:none;}
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

# ૪. ડેટા સેવ કરવાનું ફંક્શન (કેલેન્ડર માટે)
def save_to_csv_and_update_history():
    now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
    temp = st.session_state.temp
    sound = st.session_state.sound
    new_row = pd.DataFrame([[now, temp, sound]], columns=['Date-time', 'Temperature', 'sound_level'])
    
    # હિસ્ટ્રી અપડેટ
    if 'history' not in st.session_state:
        st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
    
    # CSV માં લખો
    new_row.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

# ૫. ઇનિશિયલાઈઝેશન
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Date-time', 'Temperature', 'sound_level'])
if 'temp' not in st.session_state: st.session_state.temp = 0.0
if 'sound' not in st.session_state: st.session_state.sound = 0.0

# MQTT કનેક્શન
if 'mqtt_client' not in st.session_state:
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 60)
    client.subscribe(MQTT_TOPIC)
    client.loop_start()
    st.session_state.mqtt_client = client

# નવો ડેટા પ્રોસેસ કરો
if st.session_state.get('new_data_arrived', False):
    save_to_csv_and_update_history() 
    st.session_state.new_data_arrived = False

# --- UI શરૂઆત ---
st.title("🏭 ORIX Smart Factory Dashboard")
st.write("Welcome, motor monitoring system")

# Sidebar
st.sidebar.image("1000046431.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center; color: gold;'>ORIX IoT</h3>", unsafe_allow_html=True)
points = st.sidebar.slider("GRAPH PROPORTION", 10, 100, 20)
user_phone = st.sidebar.text_input("Worker Number", value="+91")

# ૬. મેઈન ડિસ્પ્લે લોજિક
if not st.session_state.history.empty:
    display_data = st.session_state.history.tail(points)
    last_temp = display_data['Temperature'].iloc[-1]
    last_sound = display_data['sound_level'].iloc[-1]

    # મેટ્રિક્સ
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("🌡️ Current Temp", f"{last_temp}°C")
    with col2: st.metric("📈 Max Temp", f"{display_data['Temperature'].max()}°C")
    with col3: st.metric("📉 Min Temp", f"{display_data['Temperature'].min()}°C")
    with col4: st.metric("🔊 Sound Level", f"{last_sound}dB")

    # એલર્ટ્સ
    if last_temp > 70 or last_sound > 85:
        st.error("🚨 CRITICAL ALERT! Motor at Risk!")
        st.components.v1.html("<audio autoplay><source src='https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg' type='audio/ogg'></audio>", height=0)
    else:
        st.success(f"✅ System Healthy: {last_temp}°C | {last_sound}dB")

    # લાઈવ ગ્રાફ
    st.subheader("📊 ORIX Live Performance Graph")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['Temperature'], mode='lines+markers', name='Temp (°C)', line=dict(color='#FF4B4B')))
    fig.add_trace(go.Scatter(x=display_data['Date-time'], y=display_data['sound_level'], mode='lines', name='Sound (dB)', line=dict(color='#1C83E1', dash='dot')))
    fig.update_layout(template='plotly_dark', hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⌛ Waiting for data from ORIX sensors... Please start the motor.")

st.markdown("---")

# ૭. કેલેન્ડર રિપોર્ટ સેક્શન (તારો માનીતો ભાગ!)
st.header("🔍 Historical Data Report (Calendar)")
selected_date = st.date_input("Select Date for Report", value=datetime.now())

if st.button("Show Report"):
    if os.path.exists(LOG_FILE):
        df_h = pd.read_csv(LOG_FILE)
        df_h['Date-time'] = pd.to_datetime(df_h['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        filtered_data = df_h[df_h['Date-time'].dt.date == selected_date]
        
        if not filtered_data.empty:
            st.success(f"📊 Displaying report for {selected_date}")
            fig_report = go.Figure()
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['Temperature'], name='Temp (°C)', line=dict(color='#FF4B4B')))
            fig_report.add_trace(go.Scatter(x=filtered_data['Date-time'], y=filtered_data['sound_level'], name='Sound (dB)', line=dict(color='#1C83E1')))
            fig_report.update_layout(title=f"Motor Performance on {selected_date}", template='plotly_dark')
            st.plotly_chart(fig_report, use_container_width=True)
            
            csv_data = filtered_data.to_csv(index=False)
            st.download_button("📥 Download This Report", data=csv_data, file_name=f"ORIX_report_{selected_date}.csv", mime='text/csv')
        else:
            st.warning(f"⚠️ No data found for {selected_date}.")
    else:
        st.error("❌ No log file found.")

st.markdown("---") 
current_time = datetime.now().strftime("%H:%M:%S")
st.write(f"🕒 **Last Updated: {current_time}**")

# આ લાઈન દર ૨ સેકન્ડે એપ રિફ્રેશ કરશે
time.sleep(2)
st.rerun()
