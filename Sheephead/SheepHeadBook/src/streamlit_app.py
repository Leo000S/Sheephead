#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 11 20:41:00 2025

@author: leopoldschalleer
"""

from huggingface_hub import HfApi
import streamlit as st
import pandas as pd
from datetime import datetime
from collections import defaultdict
import json
from streamlit_autorefresh import st_autorefresh
import os


from sheephead_common.TurnierAuswahl import Turnier_Auswahl
from sheephead_common.SpielerInnen import SPIELER_AUSWAHL
from sheephead_common.SheepHeadBook import spielwert_bestimmen_wue
from sheephead_common.SheepHeadBook import spielwert_bestimmen_normal
from sheephead_common.SheepHeadBook import berechne_statistik
from sheephead_common.SheepHeadBook import autosave_start_new_round
from sheephead_common.SheepHeadBook import autosave_add_game
from sheephead_common.SpieleAuswahl import Aux, Wue, AllR, Standard

# -----------------------------
# HUGGING FACE SETTINGS
# -----------------------------
REPO_ID = "LeoDerLoewe/SchafkopfDataAutosave"
HF_TOKEN = os.getenv("Sheephead_Autosave")
if HF_TOKEN is None:
    raise ValueError("HF_Token fehlt! Bitte als Umgebungsvariable setzen.")

api = HfApi(token=HF_TOKEN)

ROUNDS_PREFIX = "AllContributingRounds"

api = HfApi()

def load_open_rounds():

    heute = datetime.now().strftime("%Y-%m-%d")

    files = api.list_repo_files(
        repo_id=REPO_ID,
        repo_type="dataset"
        )

    offene_runden = []

    
    for file in files:

        if file.startswith(f"{ROUNDS_PREFIX}/{heute}") and file.endswith(".json"):

            url = f"https://huggingface.co/datasets/{REPO_ID}/resolve/main/{file}"

            try:
                import requests
                data = requests.get(url).json()

                if not data.get("ende_info", False):
                    offene_runden.append((file, data))

            except:
                pass

    return offene_runden

def resolve_restrictions(tournament):
    restrictions = Standard
    if tournament[0:3] == "Aux":
        restrictions = Aux
    if tournament[0:12] == "Ak-Schafkopf":
        restrictions = Wue
    if tournament == "Gesamtstatistik":
        restrictions = Standard
    if tournament == "Allgäuer-Rundn":
        restrictions = AllR
    return restrictions
    
KLOPFEN = True
TOUT = True
SIE = True
SPIELWERTE = Standard[0]
mode = Standard[3]

# --- Streamlit App ---
st.set_page_config(page_title="Sheephead - the game of bavarian culture", layout="centered")

# --- Session State initialisieren ---
if "runde_aktiv" not in st.session_state:
    st.session_state.runde_aktiv = False

if "spieler" not in st.session_state:
    st.session_state.spieler = []

if "spiele" not in st.session_state:
    st.session_state.spiele = []

if "open_rounds" not in st.session_state:
    st.session_state.open_rounds = []


# --- RUNDENSTART ---
if not st.session_state.runde_aktiv:
    st.header("Griaß di, spui ma o gscheide Rundn?")
    
#########################################################################################
# Offene Runde???
#########################################################################################

    if st.button("🔄 Offene Runden suchen"):
        with st.spinner("Suche nach offenen Tischrunden..."):
            st.session_state.open_rounds = load_open_rounds()

    offene_runden = st.session_state.open_rounds
    
    if offene_runden:

        st.subheader("🔄 Laufende Tischrunden")
    
        optionen = [
            f"{r[1]['start_info']} ({', '.join(r[1]['spieler'])}) – {len(r[1]['spiele'])} Spiele"
            for r in offene_runden
        ]
    
        auswahl = st.selectbox(
            "Runde fortsetzen:",
            range(len(optionen)),
            format_func=lambda i: optionen[i]
        )
    
        if st.button("Fortsetzen"):
            file, data = offene_runden[auswahl]
            
            st.session_state.runden_timestamp = data.get("runden_timestamp")
            st.session_state.ende = data.get("ende_info", False)
            st.session_state.spieler = data.get("spieler", [])
            st.session_state.spiele = data.get("spiele", [])
            st.session_state.anzahl = len(st.session_state.spieler)
            st.session_state.start_info = data.get("start_info", "")
            st.session_state.tournament = data.get("tournament", "")
            st.session_state.user = data.get("User", "")
            st.session_state.autosave_file = file[33:]
            st.session_state.runde_aktiv = True
            autosave_add_game(st)
        
            st.rerun()
            
#########################################################################################
# normaler Start einer Runde:
#########################################################################################

    # Spieleranzahl muss außerhalb des Forms liegen!
    anzahl = st.number_input("Wie viele SpielerInnen?", min_value=4, max_value=7, value=4, key="anzahl_spieler")
    user = st.selectbox("Wer bist du?", SPIELER_AUSWAHL)
    tournament = st.selectbox("Welche Turnierstatistik soll gefüllt werden?", Turnier_Auswahl)
    
    restrictions = resolve_restrictions(tournament)

    st.session_state.SPIELWERTE = restrictions[0]
    st.session_state.KLOPFEN = restrictions[1]
    st.session_state.TOUT = restrictions[2]
    st.session_state.SIE = restrictions[3]
    st.session_state.mode = restrictions[4]
    
    Start_Info = st.text_input("Infos zur Tischrundn (optional):")

    with st.form("runde_start"):
        st.write("Wählt die SpielerInnen aus!")
        spieler = []

        for i in range(st.session_state.anzahl_spieler):
            default_index = i if i < len(SPIELER_AUSWAHL) else 0
            auswahl = st.selectbox(f"Spieler {i+1}:", SPIELER_AUSWAHL, index=default_index, key=f"spieler_{i}" )
            spieler.append(auswahl)

        starten = st.form_submit_button("Los gehts🎯")

        if starten:
            if len(set(spieler)) < st.session_state.anzahl_spieler:
                st.error(f"Zackl-Zement! Choose {st.session_state.anzahl_spieler} unique players!")
            else:
                st.session_state.ende = False
                st.session_state.spieler = spieler
                st.session_state.spiele = []
                st.session_state.anzahl = anzahl
                st.session_state.runde_aktiv = True
                st.session_state.start_info = Start_Info
                st.session_state.tournament = tournament
                st.session_state.user = user
                autosave_start_new_round(st)
                st.success(f"Runde gestartet mit: {', '.join(spieler)}")
                st.rerun()
                
#########################################################################################
# Spielerfassung:
#########################################################################################

if st.session_state.runde_aktiv:
    spielende_spieler = st.session_state.spieler
    aussetzer = []
    if st.session_state.anzahl > 4:
        if st.session_state.anzahl == 5:
            a1 = st.selectbox("Diese SpielerIn setzt aus:", st.session_state.spieler, key="aus1")
            aussetzer.append(a1)
    
        if st.session_state.anzahl == 6:
            a1 = st.selectbox("1. SpielerIn setzt aus:", st.session_state.spieler, key="aus1")
            # 2. Auswahl ohne den ersten Aussetzer
            rest = [s for s in st.session_state.spieler if s != a1]
            a2 = st.selectbox("2. SpielerIn setzt aus:", rest, key="aus2")
            aussetzer.extend([a1, a2])

        if st.session_state.anzahl == 7:
            a1 = st.selectbox("1. SpielerIn setzt aus:", st.session_state.spieler, key="aus1")
            rest = [s for s in st.session_state.spieler if s != a1]
    
            a2 = st.selectbox("2. SpielerIn setzt aus:", rest, key="aus2")
            rest = [s for s in st.session_state.spieler if s not in [a1, a2]]
    
            a3 = st.selectbox("3. SpielerIn setzt aus:", rest, key="aus3")
            aussetzer.extend([a1, a2, a3])

    if "letztes_spiel" in st.session_state:
        st.success(st.session_state.letztes_spiel)

    if "eingabe_phase" not in st.session_state:
        st.session_state.eingabe_phase = 1
    
    if "spielart_temp" not in st.session_state:
        st.session_state.spielart_temp = None
    
    
    spielende_spieler = [s for s in st.session_state.spieler if s not in aussetzer]
    
    # -------------------------
    # Phase 1: Nur Spielart wählen
    # -------------------------
    if st.session_state.eingabe_phase == 1:
        spielart = st.selectbox(
            "Was wurde gespielt?",
            list(st.session_state.SPIELWERTE.keys()))
        klopfer = 0
        if st.session_state.KLOPFEN == True:
            klopfer = st.number_input("Geklopft?", min_value=0, max_value=4, value=0)
    
        if st.button("Weiter"):
            st.session_state.spielart_temp = spielart
            st.session_state.klopfer_temp = klopfer
            st.session_state.eingabe_phase = 2
            st.rerun()
            
    # -------------------------
    # Phase 2: Restliche Eingaben abhängig von der Spielart
    # -------------------------
    elif st.session_state.eingabe_phase == 2:
        spielart = st.session_state.spielart_temp
        klopfer = st.session_state.klopfer_temp 
        st.write(f"**Spiel:** {spielart}")

        if st.button("Zurück zur Spielauswahl"):
            st.session_state.eingabe_phase = 1
            st.rerun()
    
        Verteilungsfaktor = 1
        if spielart != "Ramsch":
            spielmacher = st.selectbox("Wer hat das Spiel angesagt?", spielende_spieler)
        if spielart == "Ramsch":
            spielmacher = st.selectbox("Wer hat den Ramsch verloren?", spielende_spieler)
        if st.session_state.KLOPFEN == False:
            klopfer = 0
        
        rufpartner = None
        jungfrau = 0
        Sie = False
        tout = False
    
        if spielart == "Ruf":
            mögliche_rufpartner = [s for s in spielende_spieler if s != spielmacher ]
            rufpartner = st.selectbox("RufpartnerIn", mögliche_rufpartner)
            Verteilungsfaktor *= 0.5
            
            gewonnen = st.checkbox("Gewonnen?")
            kontra = st.checkbox("Kontra?")
            schneider = st.checkbox("Schneider? (Verliererteam unter 30 Punkte)")
            schwarz = st.checkbox("Schwarz?")
            laufende = st.selectbox("Wie viele Laufende?", [0] + list(range(3, 15)))
            
        if spielart == "Ramsch":
            jungfrau = st.number_input(
                "Wie viele Jungfrauen sitzen am Tisch?",
                min_value=0, max_value=3, value=0)
            
            gewonnen = False
            kontra = False
            schwarz = False
            schneider = False
            laufende = 0

        if spielart == "Bettel":
            gewonnen = st.checkbox("Gewonnen?")
            if st.session_state.TOUT == True:
                tout = st.checkbox("Brett?")
            if st.session_state.TOUT == False:
                tout = False
            kontra = False
            schwarz = False
            schneider = False
            laufende = 0
    
        if spielart == "Durchmarsch":
            gewonnen = True
            kontra = False
            schwarz = False
            schneider = False
            laufende = 0
    
        if spielart not in ["Ramsch", "Ruf", "Bettel", "Durchmarsch"]:
            gewonnen = st.checkbox("Gewonnen?")
            if st.session_state.TOUT == True:
                tout = st.checkbox("Tout (= mit offenen Karten spielen)?")
            if st.session_state.TOUT == False:
                tout = False
            if st.session_state.SIE == True:
                Sie = st.checkbox("Sie (= ich mache alle Stiche)?")
            if st.session_state.SIE == False:
                Sie = False
            kontra = st.checkbox("Kontra?")
            schneider = st.checkbox("Schneider? (Verliererteam unter 30 Punkte)")
            schwarz = st.checkbox("Schwarz?")
            laufende = st.selectbox("Wie viele Laufende?", [0] + list(range(2, 15)))

        wertn, wertn_NK = spielwert_bestimmen_normal(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, st.session_state.SPIELWERTE) 
        wertw, wertw_NK = spielwert_bestimmen_wue(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, gewonnen, st.session_state.SPIELWERTE) 
        win_text = "gewonnen"
        if gewonnen == False:
            win_text = " verloren"
        Punkte = wertn
        Punkte_str = " Punkt "
        if st.session_state.mode == "wue":
            Punkte = wertw
        if Punkte > 1:
            Punkte_str = " Punkte "
        st.write(spielmacher + " würde ein " + spielart + " für " + str(Punkte) + " (" + st.session_state.mode + ")" + Punkte_str + win_text + " haben")
        abschicken = st.button("Spiel abspeichern ✅")

        if abschicken: 
            # 🕒 individueller Zeitstempel pro Spiel 
            spiel_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
            spiel_info = {
                "Spielart" :spielart, 
                "Klopfer" :klopfer, 
                "Laufende" :laufende, 
                "Tout" :tout, 
                "Sie" :Sie, 
                "Jungfrau" :jungfrau, 
                "Schneider" :schneider, 
                "Schwarz" :schwarz, 
                "Kontra" :kontra, 
                "Gewonnen" :gewonnen
            }
            spiel_dict = {
                "Zeitstempel": spiel_timestamp,
                "Spielart": spielart,
                "Spielmacher": spielmacher,
                "Rufpartner": rufpartner,
                "Klopfer": klopfer,
                "Gewonnen": gewonnen,
                "Wert": wertn,
                "Wert_NK": wertn_NK,
                "Wert_Wue": wertw,
                "Wert_Wue_NK": wertw_NK,
                "Verteilungsfaktor": Verteilungsfaktor,
                "Mitspieler_Runde": spielende_spieler,
                "spiel_info" : spiel_info
            }
        
            st.session_state.spiele.append(spiel_dict)
        
    
            # ⬇️ NEU: in Autosave-Datei einfügen
            autosave_add_game(st)
            st.session_state.letztes_spiel = (spielmacher + " hat ein " + spielart + " für " + str(Punkte) + " (" + st.session_state.mode + ")" + Punkte_str + win_text)
            st.session_state.eingabe_phase = 1
            st.session_state.spielart_temp = None
            st.rerun()
            
#########################################################################################
# Anzeige der Statistik und Downloads und letztes Spiel zurücksetzen und Runde beenden:
#########################################################################################

    # --- STATISTIK ---
    if st.session_state.spiele:
        st.subheader("📊 Statistik der Tischrundn")
        df = berechne_statistik(st.session_state.spieler, st.session_state.spiele)
        if st.session_state.mode == "normal":
            ausblenden = ["Punkte_Wue", "Verloren"]
            st.dataframe(
                df.drop(columns=ausblenden),
                hide_index=True)
        if st.session_state.mode == "wue":
            ausblenden = ["Punkte", "Verloren"]
            st.dataframe(
                df.drop(columns=ausblenden),
                hide_index=True)
        
        # --- CSV Export Rundenstatistik---
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dateiname = f"Schafkopfrunde_{timestamp}.csv"
        csv_data = df.to_csv(index=False, sep=";").encode("utf-8")

        # --- CSV Export: einzelne Spiele ---
        spiele_df = pd.DataFrame(st.session_state.spiele)
        spiele_df.index = range(1, len(spiele_df) + 1)
        spiele_df.reset_index(inplace=True)
        spiele_df.rename(columns={"index": "Spielnummer"}, inplace=True)
        
        # Spieler und Zeitstempel ergänzen
        st.dataframe(spiele_df, hide_index=True)

        st.download_button(
            label="📥 Export Tischrundn Statistik (csv.)",
            data=csv_data,
            file_name=dateiname,
            mime="text/csv"
        )
        
        # --- Info zum letzten Spiel ---
        letztes_spiel = st.session_state.spiele[-1]
        
        # --- Button zum Löschen ---
        if st.button("🔙 Lösche das letzte Spiel"):
            geloeschtes_spiel = st.session_state.spiele.pop()
        
            # ⬇️ NEU: in Autosave-Datei einfügen
            autosave_add_game(st)
        
            st.warning(
                f"Letztes Spiel gelöscht: {geloeschtes_spiel['Spielart']} von {geloeschtes_spiel['Spielmacher']}"
            )
            st.rerun()
        
    # --- Runde beenden ---
    if st.button("🔚 Beende die Tischrundn?"):
        st.session_state.show_confirm_dialog = True
    
    
    if st.session_state.get("show_confirm_dialog", False):
    
        @st.dialog("Tischrundn wirklich beenden?")
        def confirm_end_dialog():
            st.write("Willst du die Tischrundn wirklich beenden?")
            
            if st.button("Ja, beenden"):
                st.session_state.ende = True
                autosave_add_game(st)
                st.session_state.runde_aktiv = False
                st.session_state.spiele = []
                st.session_state.spieler = []
                st.session_state.show_confirm_dialog = False
    
                st.success("Tischrundn beendet !!!")
                st.rerun()
    
            if st.button("Nein, zurück"):
                st.session_state.show_confirm_dialog = False
                st.rerun()
    
        confirm_end_dialog()
        