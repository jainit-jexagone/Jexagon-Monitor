
#OWNER_PHONE = "+919XXXXXXXXX"  
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime
LOG_FILE = "motor_logs.csv"
import os
#import pywhatkit as kit
from datetime import datetime, timedelta
import plotly.graph_objects as go
import requests

CHANNEL_ID = "3299971"
READ_API_KEY = "JSZ9OOOK0UXVQJH3"

def get_live_data():
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results=1"
    try:
        response = requests.get(url)
        data = response.json()
        
        temp = data['feeds'][0]['field1']
        sound = data['feeds'][0]['field2']
        
        return float(temp), float(sound)
    except Exception as e:
        
        return 0.0, 0.0

def cleanup_old_data(filename):
    if os.path.exists(filename):

        try:
            df = pd.read_csv(filename)
            df['Date-time'] = pd.to_datetime(df['Date-time'], format='mixed', dayfirst=True)
            
            cutoff_date = datetime.now() - timedelta(days=180)
            filtered_df = df[df['Date-time'] >= cutoff_date]
            
            if len(filtered_df) < len(df):
                filtered_df.to_csv(filename, index=False)
        except Exception as e:
            st.error(f"Error cleaning data: {e}")


st.set_page_config(page_title="Smart Factory", layout="wide")
st.title("Smart Factory Dashboard")
st.write("Welcome, motor monitoring system")

points = st.sidebar.slider("GRAPH PROPORTION", 10, 100, 20)

current_time=datetime.now().strftime("%d/%m/%Y | %H:%M:%S")

if 'history' not in st.session_state:
    
    st.session_state.history = pd.DataFrame(columns=['Temperature','sound_level'])
    

now = datetime.now().strftime("%d/%m/%Y | %H:%M:%S")
new_temp = np.random.randint(40, 80)
new_sound = np.random.randint(40, 91)

new_data = pd.DataFrame({ 'Date-time': [now], 
                         'Temperature': [new_temp],
                         'sound_level': [new_sound]})
TEMP_LIMIT = 70.0
SOUND_LIMIT = 85.0 

#if (new_temp > TEMP_LIMIT) or (new_sound > SOUND_LIMIT):
   # kit.sendwhatmsg_instantly(OWNER_PHONE, f"🚨 Danger! Temp: {new_temp}C, Sound: {new_sound}dB")


if new_temp > TEMP_LIMIT:
    st.error(f"⚠️ ખતરો (DANGER): મશીન અતિશય ગરમ છે! તાપમાન: {new_temp}°C")
    st.markdown(f"<h1 style='color:red; text-align:center;'>🚨 MACHINE OVERHEATING 🚨</h1>", unsafe_allow_html=True)

if new_sound > SOUND_LIMIT:
    st.warning(f"🔔 ચેતવણી (WARNING): મશીનનો અવાજ વધી રહ્યો છે! લેવલ: {new_sound}dB")

import pywhatkit as kit

#if new_temp > TEMP_LIMIT:
    # મેસેજ મોકલવા માટે: (નંબર, મેસેજ)
    # અત્યારે આને કમેન્ટમાં રાખવું અથવા સાવચેતીથી વાપરવું
    # kit.sendwhatmsg_instantly("+91XXXXXXXXXX", f"🚨 એલર્ટ: મશીન M01 ગરમ છે! તાપમાન: {new_temp}°C")
    #st.success("WhatsApp એલર્ટ મોકલવામાં આવ્યો છે!")


user_phone = st.sidebar.text_input("worker number", value="+91")

if new_temp > TEMP_LIMIT:
    if len(user_phone) > 10: 
        kit.sendwhatmsg_instantly(user_phone, f"🚨 મશીન એલર્ટ: તાપમાન વધી ગયું છે!")

st.session_state.history = pd.concat([st.session_state.history, new_data], ignore_index=True)

display_data = st.session_state.history.tail(points)

last_temp =display_data['Temperature'].iloc[-1]

if last_temp < 75:
    st.success(f"System Healthy: {last_temp}°C")

else:
    st.error(f"High Temp Alert: {last_temp}°C")

last_sound=display_data['sound_level'].iloc[-1]

if last_sound > 85:
    st.error(f"sound is very high: {last_sound}dB")
else:
    st.success(f"sound is maintain :{last_sound}dB")

critical_condition = (last_temp > 75) or (last_sound > 85)
if critical_condition:
    st.error("🚨 CRITICAL ALERT! Motor at Risk!")
    st.components.v1.html(
        """
        <audio autoplay>
          <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
        </audio>
        """,
        height=0
    )        
else:   st.success(f"✅ System Normal: {last_temp}°C | {last_sound}dB")    

max_temp = display_data['Temperature'].max()
min_temp = display_data['Temperature'].min()

new_entry = pd.DataFrame([[current_time, new_temp, new_sound]], 
                         columns=['Date-time', 'Temperature', 'Sound'])

if not os.path.isfile(LOG_FILE):
    new_entry.to_csv(LOG_FILE, index=False)
else:
    new_entry.to_csv(LOG_FILE, mode='a', index=False, header=False)

col1, col2, col3, col4  = st.columns(4)

with col1:
    st.metric("હાલનું (Current)", f"{last_temp}°C")
with col2:
    st.metric("મહત્તમ (Max)", f"{max_temp}°C")
with col3:
    st.metric("ન્યૂનતમ (Min)", f"{min_temp}°C")
with col4:
    st.metric("sound level",f"{last_sound}dB") 

st.markdown("---")
st.header("🔍 Search History (Single Day)")

# આજના દિવસથી ૬ મહિના (૧૮૦ દિવસ) પહેલાની તારીખ ગણો
six_months_ago = datetime.now() - timedelta(days=180)

# કેલેન્ડરમાં લિમિટ મૂકો
selected_date = st.date_input(
    "Select Date", 
    value=datetime.now(),
    min_value=six_months_ago, # આનાથી જૂની તારીખ નહીં દેખાય
    max_value=datetime.now()
)

if st.button("Show Report"):
    try:
        
        df_history = pd.read_csv("motor_logs.csv")
        
        df_history['Date-time'] = pd.to_datetime(df_history['Date-time'], format='%d/%m/%Y | %H:%M:%S')
        
        filtered_df = df_history[df_history['Date-time'].dt.date == selected_date]
        
        if not filtered_df.empty:
            st.success(f"📊 Report for {selected_date}")
            st.line_chart(filtered_df.set_index('Date-time')['Temperature'])
            st.write(filtered_df)
        else:
            st.warning(f"Dilgiri, {selected_date} na divas no koi data save thayo nathi.")
            
    except FileNotFoundError:
        st.error("Haji sudhi koi data save thayo nathi (CSV file missing).")

st.markdown("---") 
st.write(f"🕒 **Last Updated: {current_time}**")
       
st.markdown("---")
st.subheader("📊 GRAPH")

# ૧. નવો પ્લોટલી ગ્રાફ બનાવવો
fig = go.Figure()

# ૨. તાપમાનની લાઈન (Temperature)
fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['Temperature'],
                         mode='lines+markers', 
                         name='તાપમાન (°C)',
                         line=dict(color='#FF4B4B', width=3)))

# ૩. અવાજની લાઈન (Sound)
fig.add_trace(go.Scatter(x=display_data['Date-time'], 
                         y=display_data['sound_level'],
                         mode='lines', 
                         name='sound (dB)',
                         line=dict(color='#1C83E1', width=2, dash='dot')))

# ૪. ગ્રાફનો દેખાવ (Layout) સેટ કરવો
fig.update_layout(template='plotly_dark', 
                  xaxis_title='time', 
                  yaxis_title='value',
                  hovermode='x unified')

# ૫. ગ્રાફને સ્ક્રીન પર બતાવવો
st.plotly_chart(fig, use_container_width=True)

time.sleep(2)
st.rerun()
