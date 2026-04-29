import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- distanza Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

st.title("Mappa GW + ricerca indirizzo")

uploaded_file = st.file_uploader("Carica CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Controllo colonne
    required_cols = {"GW", "LAT", "LON", "STATO"}
    if not required_cols.issubset(df.columns):
        st.error(f"Il CSV deve contenere: {required_cols}")
    else:
        st.dataframe(df.head())

        indirizzo = st.text_input("Inserisci indirizzo")

        if indirizzo:
            geolocator = Nominatim(user_agent="streamlit_map")
            location = geolocator.geocode(indirizzo)

            if location:
                search_lat, search_lon = location.latitude, location.longitude

                # --- distanza
                df["distance_km"] = df.apply(
                    lambda row: haversine(search_lat, search_lon, row["LAT"], row["LON"]),
                    axis=1
                )

                nearest = df.nsmallest(3, "distance_km")

                st.subheader("3 GW più vicini")
                st.dataframe(nearest[["GW", "STATO", "distance_km"]])

                # --- mappa
                mappa = folium.Map(location=[search_lat, search_lon], zoom_start=11)

                # punto cercato
                folium.Marker(
                    [search_lat, search_lon],
                    popup="Indirizzo cercato",
                    icon=folium.Icon(color="blue")
                ).add_to(mappa)

                # tutti i GW
                for _, row in df.iterrows():
                    colore = "green" if row["STATO"] == "A" else "gray"

                    folium.Marker(
                        [row["LAT"], row["LON"]],
                        popup=f"GW: {row['GW']}<br>STATO: {row['STATO']}",
                        icon=folium.Icon(color=colore)
                    ).add_to(mappa)

                # evidenzia i 3 più vicini
                for _, row in nearest.iterrows():
                    folium.Marker(
                        [row["LAT"], row["LON"]],
                        popup=f"{row['GW']} - {row['distance_km']:.2f} km",
                        icon=folium.Icon(color="red")
                    ).add_to(mappa)

                st_folium(mappa, width=700, height=500)

            else:
                st.error("Indirizzo non trovato")
