import streamlit as st
import requests
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np

# 📱 Station und API
API_KEY = '4fb8bb1278864b31b8bb127886fb3132'
STATION_ID = 'IKRNTENU3'
today = date.today().strftime("%Y%m%d")

# 🔗 API-URL
url = (
    f"https://api.weather.com/v2/pws/history/all?stationId={STATION_ID}"
    f"&format=json&units=m&date={today}&apiKey={API_KEY}"
)

# 🌭 Richtung in Himmelsrichtung umwandeln
def grad_to_richtung(deg):
    richtungen = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']
    ix = int((deg + 22.5) % 360 / 45)
    return richtungen[ix]

# 📊 Daten abrufen
@st.cache_data(ttl=600)
def get_data():
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json().get("observations", [])
        times, speeds_avg, gusts_high, dirs_deg, richtungen = [], [], [], [], []
        for obs in data:
            speed = obs.get("metric", {}).get("windspeedAvg")
            gust = obs.get("metric", {}).get("windgustHigh")
            direction = obs.get("winddirAvg")
            time = obs.get("obsTimeLocal")
            if speed is not None and gust is not None and direction and time:
                zeit_kurz = time[-8:-3]  # "14:05"
                stunde = int(zeit_kurz[:2])
                if stunde >= 7:
                    times.append(zeit_kurz)
                    speeds_avg.append(speed)
                    gusts_high.append(gust)
                    dirs_deg.append(direction)
                    richtungen.append(grad_to_richtung(direction))
        return times, speeds_avg, gusts_high, dirs_deg, richtungen
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Wetterdaten: {e}")
        return [], [], [], [], []

# 🌬️ Windrose
def plot_windrose(speeds, dirs_deg):
    dirs_rad = [np.deg2rad(d) for d in dirs_deg]
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)
    ax.bar(dirs_rad, speeds, width=np.deg2rad(22.5), color='skyblue', edgecolor='black')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("🌬️ Windrose")
    return fig

# 📈 Plotly-Diagramm mit beiden Linien
def plot_interactive_lines(times, speeds, gusts):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=times,
        y=speeds,
        mode='lines+markers+text',
        name="Windgeschwindigkeit",
        text=[f"{s:.0f} km/h" for s in speeds],
        textposition="top center",
        line=dict(color='blue'),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=times,
        y=gusts,
        mode='lines+markers+text',
        name="Windböe max.",
        text=[f"{g:.0f} km/h" for g in gusts],
        textposition="bottom center",
        line=dict(color='red', dash='dash'),
        marker=dict(size=6)
    ))

    fig.update_layout(
        title="📈 Windgeschwindigkeit & Böen über den Tag",
        xaxis_title="Uhrzeit",
        yaxis_title="km/h",
        yaxis=dict(range=[0, max(gusts + speeds + [30])]),
        template="simple_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig

# 📉 Kompaktes Balkendiagramm für Mobilgeräte
def plot_mobile_bar(times, speeds, gusts):
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(times[-10:], speeds[-10:], color='skyblue', label='Wind')
    ax.plot(times[-10:], gusts[-10:], color='red', linestyle='--', marker='o', label='Böe')
    ax.set_title("Wind & Böen (letzte Messwerte)")
    ax.set_ylabel("km/h")
    ax.legend()
    plt.xticks(rotation=45, ha='right')
    fig.tight_layout()
    return fig

# 📋 Prozentuale Windverteilung
def berechne_windverteilung(richtungen):
    df = pd.Series(richtungen)
    verteilung = df.value_counts(normalize=True).sort_index() * 100
    verteilung = verteilung.reindex(['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW'], fill_value=0)
    return verteilung.round(1)

#🔍 Gerät erkennen (per URL-Parameter ua=mobile)
def is_mobile():
    ua_param = st.query_params.get("ua", "")
    return "mobile" in ua_param.lower() if isinstance(ua_param, str) else False


# 🖥️ Web-App anzeigen
st.set_page_config(page_title="Wetterstation Petzen", layout="centered")
st.title("🌤️ Wetterstation Petzen – Aktuelle Tagesdaten")
st.caption(f"Datum: {today}")

# 📦 Daten laden
times, speeds_avg, gusts_high, dirs_deg, richtungen = get_data()

if times:
    st.pyplot(plot_windrose(speeds_avg, dirs_deg))

    if is_mobile():
        st.markdown("### Kompakte Übersicht (Mobil)")
        st.pyplot(plot_mobile_bar(times, speeds_avg, gusts_high))
    else:
        st.markdown("### 📈 Windverlauf (Desktop)")
        st.plotly_chart(plot_interactive_lines(times, speeds_avg, gusts_high), use_container_width=True)

    st.markdown("### Windverteilung (heute in %)")
    verteilung = berechne_windverteilung(richtungen)
    df_verteilung = pd.DataFrame({
        "Richtung": verteilung.index,
        "Anteil (%)": verteilung.values
    })
    st.dataframe(df_verteilung.style.format({"Anteil (%)": "{:.1f}"}), use_container_width=True)

    # 📋 Einzelne Messwerte
    st.markdown("### Einzelne Messwerte")
    df_messwerte = pd.DataFrame({
        "Uhrzeit": times,
        "Wind (km/h)": speeds_avg,
        "Windböe max. (km/h)": gusts_high,
        "Windrichtung": richtungen
    })
    st.dataframe(df_messwerte, use_container_width=True)

else:
    st.warning("Noch keine Daten für heute verfügbar.")

# Footer
st.markdown("---")
st.markdown(
    'Erstellt von [**Go2Fly**](https://www.go2fly.at)',
    unsafe_allow_html=True
)
