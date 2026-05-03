from huggingface_hub import HfApi
import streamlit as st
import pandas as pd
from datetime import datetime
from collections import defaultdict
import json
from streamlit_autorefresh import st_autorefresh
import os
import requests

from .SpielerInnen import SPIELER_AUSWAHL
from .TurnierAuswahl import Turnier_Auswahl



# -----------------------------
# HUGGING FACE SETTINGS
# -----------------------------
REPO_ID = "LeoDerLoewe/SchafkopfDataAutosave"
api = HfApi()


HF_TOKEN = os.getenv("Sheephead_Autosave")
if HF_TOKEN is None:
    raise ValueError("HF_Token fehlt! Bitte in HuggingFace Secrets hinterlegen.")

# KEIN login() aufrufen!
api = HfApi(token=HF_TOKEN)

### ###

# -----------------------------
# Hilfsfunktionen für HF Upload/Download
# -----------------------------
def _hf_upload_json(filename, data):
    """Upload einer JSON-Datei ins HF-Dataset-Repo."""

    # Unterordner definieren
    unterordner = f"/tmp/AllContributingRounds/{filename[16:26]}"
    path_repo = f"AllContributingRounds/{filename[16:26]}/{filename}"
    # Ordner erstellen, falls er noch nicht existiert
    os.makedirs(unterordner, exist_ok=True)

    # Dateipfad bauen
    local_path = os.path.join(unterordner, filename)

    # JSON lokal speichern
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Upload zu HuggingFace
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=path_repo,  # optional: Unterordner im Repo
        repo_id=REPO_ID,
        repo_type="dataset",
    )

# -----------------------------
# AUTOSAVE-FUNKTIONEN
# -----------------------------

def autosave_start_new_round(st):
    """Wird bei Rundenstart aufgerufen. Erstellt neue Autosave-Datei."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Schafkopf_Runde_{timestamp}.json"
    

    st.session_state.autosave_file = filename
    st.session_state.runden_timestamp = timestamp

    data = {
        "runden_timestamp": timestamp,
        "User": st.session_state.user,
        "start_info": st.session_state.get("start_info", ""),  # <-- DEFAULT WERT
        "spieler": st.session_state.spieler,
        "tournament": st.session_state.tournament,
        "spiele": []
    }

    

    _hf_upload_json(filename, data)

def autosave_add_game(st):
    """Speichert alle Spiele aus st.session_state.spiele ins HF Dataset."""
    filename = st.session_state.autosave_file

    # Unterordner definieren
    unterordner = f"/tmp/AllContributingRounds/{filename[16:26]}"
    path_repo = f"AllContributingRounds/{filename[16:26]}/{filename}"


    local_path = os.path.join(unterordner, filename)
    os.makedirs(unterordner, exist_ok=True)


    # Daten zusammenstellen
    data = {
        "runden_timestamp": st.session_state.runden_timestamp,
        "tournament": st.session_state.tournament,
        "User": st.session_state.user,
        "start_info": st.session_state.start_info,
        "ende_info": st.session_state.ende,
        "spieler": st.session_state.spieler,
        "spiele": st.session_state.spiele  # <-- komplette Liste
    }

    # Lokal speichern
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    # Upload zu HuggingFace
    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=path_repo,
        repo_id=REPO_ID,
        repo_type="dataset"
    )


# Modus Augschburg
# --- Hilfsfunktionen ---
def spielwert_bestimmen_normal(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, SPIELWERTE):
    basis = SPIELWERTE.get(spielart, 1) 
    bonus = 0 + jungfrau
    if tout:
        basis += 1 
    if kontra: 
        bonus += 1
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1 
    wertn = (basis + laufende) * (2 ** bonus) * (2 ** klopfer)
    wertn_NK = (basis + laufende) * (2 ** bonus)
    return wertn, wertn_NK

def spielwert_bestimmen_wue(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, gewonnen, SPIELWERTE):
    basis = SPIELWERTE.get(spielart, 1) 
    if basis == 5:
        basis = 3
    kontrazahl = 0
    if not gewonnen and spielart == "Ruf":
        basis += 1
    if tout:
        basis += 1 
    if kontra: 
        kontrazahl += 1
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1  
    wert_wue = (basis+jungfrau) * (1 + kontrazahl + klopfer) + laufende
    wertn_wue_NK = (basis+jungfrau) * (1 + kontrazahl) + laufende
    return wert_wue, wertn_wue_NK

def berechne_statistik(spieler, spiele):
    konto_normal = defaultdict(int)
    konto_wue = defaultdict(int)
    statistik = defaultdict(lambda: {"Spiele": 0, "Gespielt": 0, "Gewonnen": 0, "Verloren": 0})

    for spiel in spiele:
        faktor = spiel.get("Verteilungsfaktor", 1)
        sa = spiel["Spielart"]
        sm = spiel["Spielmacher"]
        rp = spiel["Rufpartner"]
        wertn = spiel["Wert"]
        wertw = spiel["Wert_Wue"]
        gewonnen = spiel["Gewonnen"]
        alle = set(spieler)
        spielende = set(spiel["Mitspieler_Runde"])
        team = {sm}
        if rp:
            team.add(rp)
        gegner = spielende - team

        # Statistikzähler
        for s in spielende:
            statistik[s]["Spiele"] += 1
        for s in team:
            if sa != "Ramsch":
                statistik[s]["Gespielt"] += 1

        # Punkteverteilung
        if gewonnen:
            for s in team:
                konto_normal[s] += wertn * len(gegner) * faktor
                konto_wue[s] += wertw * len(gegner) * faktor
                statistik[s]["Gewonnen"] += 1
            for g in gegner:
                konto_normal[g] -= wertn * len(team) * faktor
                konto_wue[g] -= wertw * len(team) * faktor
                statistik[g]["Verloren"] += 1
        if not gewonnen:
            for s in team:
                konto_normal[s] -= wertn * len(gegner) * faktor
                konto_wue[s] -= wertw * len(gegner) * faktor
                statistik[s]["Verloren"] += 1
            for g in gegner:
                konto_normal[g] += wertn * len(team) * faktor
                konto_wue[g] += wertw * len(team) * faktor
                statistik[g]["Gewonnen"] += 1

    df = pd.DataFrame([
        {
            "Spieler": s,
            "Runden": statistik[s]["Spiele"],
            "Gespielt": statistik[s]["Gespielt"],
            "Gewonnen": statistik[s]["Gewonnen"],
            "Verloren": statistik[s]["Verloren"],
            "Punkte": konto_normal[s],
            "Punkte_Wue": konto_wue[s]
        }
        for s in spieler
    ])
    
    return df


