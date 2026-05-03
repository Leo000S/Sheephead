import os
import streamlit as st
import json
import numpy as np
from huggingface_hub import hf_hub_download, HfApi, RepoFile
import requests
import re
import pandas as pd
import io
import itertools
import matplotlib.pyplot as plt
from typing import List, Optional



from sheephead_common.SpielerInnen import SPIELER_GRUPPEN
from sheephead_common.Statistik import berechne_punkte
from sheephead_common.Statistik import join_all_tischrundn
from sheephead_common.Statistik import analyse_all_players
from sheephead_common.Statistik import analyse_different_stats
from sheephead_common.Statistik import filter_spiele
from sheephead_common.Statistik import plot_stats_streamlit
from sheephead_common.AboutDataset import extract_file_timestamp
from sheephead_common.AboutDataset import hf_download_all_contributing_rounds
from sheephead_common.AboutDataset import collect_all_json_files
from sheephead_common.AboutDataset import hf_upload_file

@st.cache_resource(show_spinner=False)
def init_data():
    """
    Wird genau einmal pro Space-Lifecycle ausgeführt
    (oder bis Cache manuell gelöscht wird).
    """
    base_dir = "/tmp/AllContributingRounds"
    marker_file = "/tmp/.data_initialized"

    if os.path.exists(marker_file):
        return base_dir

    with st.spinner("📥 Lade Schafkopf-Daten aus HuggingFace..."):
        files = hf_download_all_contributing_rounds(
            repo_id="LeoDerLoewe/SchafkopfDataAutosave",
            local_base_dir=base_dir
        )

        with open(marker_file, "w") as f:
            f.write("ok")

    return base_dir
    
# ===============================
# Streamlit UI
# ===============================

st.set_page_config(layout="wide")
st.title("♠️ Schafkopf – Spielanalyse")


csv_dir = "/tmp/AllContributingRounds"
REPO_ID = "LeoDerLoewe/SchafkopfDataAutosave"
HF_TOKEN = os.getenv("HF_Token")
if HF_TOKEN is None:
    raise ValueError("HF_Token fehlt! Bitte in HuggingFace Secrets hinterlegen.")

DATA_DIR = init_data()
csv_files = collect_all_json_files(csv_dir)
final_df = join_all_tischrundn(csv_files, csv_dir)

output_dir = "/tmp/output"
os.makedirs(output_dir, exist_ok=True)
local_csv_path = os.path.join(output_dir, "final_df.csv")
final_df.to_csv(local_csv_path, index=False, encoding="utf-8")

hf_upload_file(
    repo_id=REPO_ID,
    local_path=local_csv_path,  
    path_in_repo="DerivedData/final_df.csv",
    hf_token=HF_TOKEN,
    commit_message="Update Statistik-CSV aus Space")

# -------------------------------
# Sidebar Filter
# -------------------------------
with st.sidebar:
    st.header("♠️ Daten")

    if st.button("🔄 Daten neu laden", use_container_width=True):
        marker_file = "/tmp/.data_initialized"
        if os.path.exists(marker_file):
            os.remove(marker_file)

        st.cache_resource.clear()
        st.rerun()

    st.divider()
    st.header("🔎 Filter")
df = final_df

alle_spielarten = sorted(df["Spielart"].dropna().unique())
alle_tournaments = sorted(df["tournament"].dropna().unique())
alle_spieler = sorted(
    {
        s.strip()
        for row in df["Mitspieler_Runde"].dropna()
        if isinstance(row, list)
        for s in row
        if isinstance(s, str) and s.strip()
    }
)

namen_einzel = st.sidebar.multiselect("SpielerInnen", options=alle_spieler)

gruppen = st.sidebar.multiselect("Gruppen", options=list(SPIELER_GRUPPEN.keys()))

namen = set(namen_einzel)
for gruppe in gruppen:
    namen.update(SPIELER_GRUPPEN[gruppe])
namen = list(namen)

spielarten = st.sidebar.multiselect("Spielart", options= ["alle"] + alle_spielarten)

tournament = st.sidebar.selectbox("Turnier", options=["alle"] + alle_tournaments)

OhneKlopfen = st.sidebar.checkbox("Soll das Klopfen herausgerechnent werden?")

Punkteberechnung = st.sidebar.selectbox("Berechnung der Punkte", options = ["Normal", "Würzburg"])

MinSpiele = st.sidebar.number_input("Mindestanzahl Spiele pro SpielerIn", min_value=0,step=10, value=0) 



if Punkteberechnung == "Würzburg": 
    Punkteart = "Endpunktestand_Wue"
    KeyKumulativ = "Kumulativer Punktestand_Wue" 
if Punkteberechnung == "Normal": 
    Punkteart = "Endpunktestand"
    KeyKumulativ = "Kumulativer Punktestand"

if OhneKlopfen == True:
    Punkteart = Punkteart[0:14] + "_NK" + Punkteart[14:]
    KeyKumulativ = KeyKumulativ[0:23] + "_NK" + KeyKumulativ[23:]

tournament_filter = (
    [t for t in df["tournament"].unique() if t != "Allgäuer-Rundn"]
    if tournament == "alle"
    else [tournament]
)

# -------------------------------
# Aktion
# -------------------------------

if st.button("📊 Anzeigen"):
    df_result = filter_spiele(
        df,
        namen=namen if namen else None,
        spielarten=spielarten if spielarten else None,
        tournament=tournament_filter,
    )

    spieler_stats = analyse_all_players(df_result, namen, MinSpiele)
    if spieler_stats != {}:
        overview = analyse_different_stats(spieler_stats, Punkteart, show=True)
        st.dataframe(overview, use_container_width=True, height=600)
        # Optional Download
        csv_bytes = overview.to_csv(sep=";", index=False).encode("utf-8")
        st.download_button("⬇️ CSV herunterladen", data=csv_bytes, file_name="gefilterte_overview.csv", mime="text/csv")

        
        plot_stats_streamlit(spieler_stats, KeyKumulativ)
            
    else: 
        st.write("⬅️ Bitte wähle SpielerInnen aus!")

else:
    st.info("⬅️ Filter auswählen und auf **Anzeigen** klicken")
