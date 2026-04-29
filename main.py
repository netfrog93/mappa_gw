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
def geocode_address(indirizzo):
    geolocator = Nominatim(user_agent="streamlit_map")
    return geolocator.geocode(indirizzo)

st.title("Mappa GW")

uploaded_file = st.file_uploader("Carica CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if {"GW", "LAT", "LON", "STATO"}.issubset(df.columns):

        # --- FILTRI
        col1, col2 = st.columns(2)

        with col1:
            gw_search = st.text_input("Cerca GW")

        with col2:
            raggio = st.slider("Raggio (metri)", 100, 50000, 5000)

        indirizzo = st.text_input("Inserisci indirizzo")

        if indirizzo:
            location = geocode_address(indirizzo)

            if location:
                search_lat, search_lon = location.latitude, location.longitude

                # distanza
                df["distance_m"] = df.apply(
                    lambda row: haversine(search_lat, search_lon, row["LAT"], row["LON"]),
                    axis=1
                )

                # filtro raggio
                df_filtrato = df[df["distance_m"] <= raggio]

                # filtro GW
                if gw_search:
                    df_filtrato = df_filtrato[df_filtrato["GW"].str.contains(gw_search, case=False, na=False)]

                # top 3
                nearest = df_filtrato.nsmallest(3, "distance_m")

                st.subheader("Risultati")
                st.dataframe(df_filtrato[["GW", "STATO", "distance_m"]])

                st.subheader("Top 3 più vicini")
                st.dataframe(nearest[["GW", "STATO", "distance_m"]])

                # --- mappa
                mappa = folium.Map(location=[search_lat, search_lon], zoom_start=12)

                # cerchio raggio
                folium.Circle(
                    location=[search_lat, search_lon],
                    radius=raggio,
                    color="blue",
                    fill=False
                ).add_to(mappa)

                # punto cercato
                folium.Marker(
                    [search_lat, search_lon],
                    popup="Indirizzo",
                    icon=folium.Icon(color="blue", icon="home", prefix="fa")
                ).add_to(mappa)

                cluster = MarkerCluster().add_to(mappa)

                # punti filtrati
                for _, row in df_filtrato.iterrows():
                    colore = "green" if row["STATO"] == "A" else "gray"

                    folium.Marker(
                        [row["LAT"], row["LON"]],
                        popup=f"{row['GW']} - {row['distance_m']:.0f} m",
                        icon=folium.Icon(color=colore, icon="signal", prefix="fa")
                    ).add_to(cluster)

                # top 3 evidenziati
                for _, row in nearest.iterrows():
                    folium.Marker(
                        [row["LAT"], row["LON"]],
                        popup=f"{row['GW']} - {row['distance_m']:.0f} m",
                        icon=folium.Icon(color="red", icon="star", prefix="fa")
                    ).add_to(mappa)

                st_folium(mappa, width=800, height=500)

            else:
                st.error("Indirizzo non trovato")
    else:
        st.error("CSV non valido")
