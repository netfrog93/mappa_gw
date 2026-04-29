import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- distanza in metri
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

@st.cache_data
def geocode(address):
    geolocator = Nominatim(user_agent="gw_map")
    return geolocator.geocode(address)

st.title("Mappa siti")

uploaded_file = st.file_uploader("Carica Excel", type=["xlsx"])

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # normalizzazione nomi colonne
    df.columns = df.columns.str.strip()

    # rinomina colonne per comodità
    df = df.rename(columns={
        "SITE ID": "SITE_ID",
        "ID LORA": "ID_LORA",
        "Coordinate GPS (Latitude)": "LAT",
        "Coordinate GPS (Longitude)": "LON",
        "Stato Delivery": "STATO"
    })

    # conversione coordinate (virgola -> punto + float)
    df["LAT"] = df["LAT"].astype(str).str.replace(",", ".").astype(float)
    df["LON"] = df["LON"].astype(str).str.replace(",", ".").astype(float)

    st.dataframe(df.head())

    mode = st.radio("Modalità", ["SITE ID + raggio", "Indirizzo + raggio"])

    raggio = st.slider(
        "Raggio (metri)",
        min_value=100,
        max_value=5000,
        value=500,
        step=100
    )

    search_lat = search_lon = None

    # =========================
    # MODALITÀ SITE ID
    # =========================
    if mode == "SITE ID + raggio":
        site = st.text_input("SITE ID")

        if site:
            match = df[df["SITE_ID"] == site]

            if match.empty:
                st.warning("SITE ID non trovato")
                st.stop()

            search_lat = match.iloc[0]["LAT"]
            search_lon = match.iloc[0]["LON"]

    # =========================
    # MODALITÀ INDIRIZZO
    # =========================
    else:
        address = st.text_input("Indirizzo")

        if address:
            loc = geocode(address)

            if not loc:
                st.warning("Indirizzo non trovato")
                st.stop()

            search_lat, search_lon = loc.latitude, loc.longitude

    # =========================
    # LOGICA COMUNE
    # =========================
    if search_lat is not None:

        df["distance_m"] = df.apply(
            lambda r: haversine(search_lat, search_lon, r["LAT"], r["LON"]),
            axis=1
        )

        df_raggio = df[df["distance_m"] <= raggio]
        nearest3 = df.nsmallest(3, "distance_m")

        st.subheader("Risultati nel raggio")
        st.dataframe(df_raggio[["SITE_ID", "ID_LORA", "STATO", "distance_m"]])

        st.subheader("Top 3 più vicini")
        st.dataframe(nearest3[["SITE_ID", "ID_LORA", "STATO", "distance_m"]])

        # =========================
        # MAPPA
        # =========================
        mappa = folium.Map(location=[search_lat, search_lon], zoom_start=12)

        folium.Circle(
            location=[search_lat, search_lon],
            radius=raggio,
            color="blue",
            fill=False
        ).add_to(mappa)

        folium.Marker(
            [search_lat, search_lon],
            icon=folium.Icon(color="blue", icon="home", prefix="fa")
        ).add_to(mappa)

        cluster = MarkerCluster().add_to(mappa)

        for _, row in df_raggio.iterrows():
            colore = "green" if str(row["STATO"]).upper() == "A" else "gray"

            folium.Marker(
                [row["LAT"], row["LON"]],
                popup=f"SITE: {row['SITE_ID']}<br>LORA: {row['ID_LORA']}<br>{row['distance_m']:.0f} m",
                icon=folium.Icon(color=colore, icon="signal", prefix="fa")
            ).add_to(cluster)

        for _, row in nearest3.iterrows():
            folium.Marker(
                [row["LAT"], row["LON"]],
                popup=f"TOP: {row['SITE_ID']} - {row['distance_m']:.0f} m",
                icon=folium.Icon(color="red", icon="star", prefix="fa")
            ).add_to(mappa)

        st_folium(mappa, width=800, height=500)
