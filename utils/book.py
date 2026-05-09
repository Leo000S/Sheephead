#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 11 20:41:00 2025

@author: leopoldschaller
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from services.supabase_client import supabase

from TurnierAuswahl import Turnier_Auswahl
from SheepHeadBook import spielwert_bestimmen_wue
from SheepHeadBook import spielwert_bestimmen_normal
from SheepHeadBook import (berechne_statistik)
from SpieleAuswahl import Aux, Wue, AllR, Standard

def load_open_rounds():
    user_response = supabase.auth.get_user()
    if not user_response.user:
        st.error("Kein Benutzer angemeldet!")
        return
    user_id = user_response.user.id
    heute = datetime.now().date().isoformat()

    # Query mit Filter auf User ID und Datum
    response = (
        supabase
        .table("rounds")
        .select("*")
        .eq("user_id", user_id)          # Nur Runden des aktuellen Users
        .gte("created_at", heute)        # Alles ab heute 00:00
        .execute()
    )

    offene_runden = []

    for row in response.data:
        # 'data' ist dein JSON-Feld in der Datenbank
        data = row.get("data", {})

        # Nur hinzufügen, wenn kein Ende-Info vorhanden ist
        # (Ich prüfe hier auf None oder leeren String, je nachdem was du speicherst)
        if not data.get("ende_info"):
            offene_runden.append(data)

    return offene_runden

def save_round(st):
    # Den aktuell eingeloggten User holen
    user_response = supabase.auth.get_user()
    if not user_response.user:
        st.error("Kein Benutzer angemeldet!")
        return
    user_id = user_response.user.id

    st.write(user_id)
    st.write("SESSION USER:", supabase.auth.get_user())
    st.write("SESSION ACCESS TOKEN:", supabase.auth.get_session())
    data = {
        "runden_timestamp": st.session_state.runden_timestamp,
        "tournament": st.session_state.tournament,
        "User": user_id,
        "start_info": st.session_state.start_info,
        "ende_info": st.session_state.ende,
        "spieler": st.session_state.spieler,
        "spiele": st.session_state.spiele
    }

    supabase.table("rounds").insert({
        "user_id": user_id,
        "created_at": st.session_state.runden_timestamp,
        "data": data
    }).execute()


def update_round(st):
    # Den aktuell eingeloggten User holen
    user_response = supabase.auth.get_user()
    if not user_response.user:
        st.error("Kein Benutzer angemeldet!")
        return

    user_id = user_response.user.id

    # Dein Daten-Objekt für die Spalte "data"
    data = {
        "runden_timestamp": st.session_state.runden_timestamp,
        "tournament": st.session_state.tournament,
        "User": user_id,
        "start_info": st.session_state.start_info,
        "ende_info": st.session_state.ende,
        "spieler": st.session_state.spieler,
        "spiele": st.session_state.spiele
    }

    # UPDATE mit Filter
    # WICHTIG: .eq() definiert, WELCHE Zeile geupdated wird.
    # Filter nach created_at + user_id
    try:
        supabase.table("rounds").update({
            "data": data  # Wir updaten primär das JSON-Feld
        }).eq("user_id", user_id) \
            .eq("created_at", st.session_state.runden_timestamp) \
            .execute()

        st.success("Runde erfolgreich aktualisiert!")
    except Exception as e:
        st.error(f"Fehler beim Update: {e}")

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

# load profiles:

def load_profiles():
    response = supabase.table("profiles") \
        .select("id, username") \
        .order("username") \
        .execute()

    return response.data if response.data else []


def run_book():

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
                f"{r['start_info']} ({', '.join(s[0] for s in r['spieler'])}) – {len(r['spiele'])} Spiele"
                for r in offene_runden
            ]

            auswahl = st.selectbox(
                "Runde fortsetzen:",
                range(len(optionen)),
                format_func=lambda i: optionen[i]
            )

            if st.button("Fortsetzen"):
                # 1. Das komplette Dictionary holen (kein "file, data = ...")
                runde_daten = offene_runden[auswahl]

                # 2. Session State befüllen
                st.session_state.runden_timestamp = runde_daten.get("runden_timestamp")
                st.session_state.ende = runde_daten.get("ende_info", False)
                st.session_state.spieler = runde_daten.get("spieler", [])
                st.session_state.spiele = runde_daten.get("spiele", [])
                st.session_state.anzahl = len(st.session_state.spieler)
                st.session_state.start_info = runde_daten.get("start_info", "")
                st.session_state.tournament = runde_daten.get("tournament", "")
                st.session_state.runde_aktiv = True

                # Erstelle erst die Liste der Namen
                player_list = [s[0] for s in st.session_state.spieler]
                player_to_id = {s[0]: s[1] for s in st.session_state.spieler}
                st.session_state.player_list = player_list
                st.session_state.player_to_id = player_to_id

                update_round(st)


                st.rerun()

    #########################################################################################
    # normaler Start einer Runde:
    #########################################################################################

        # Spieleranzahl muss außerhalb des Forms liegen!
        anzahl = st.number_input("Wie viele SpielerInnen?", min_value=4, max_value=7, value=4, key="anzahl_spieler")
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

            profiles = load_profiles()

            if not profiles:
                st.error("Keine Profile gefunden.")
                st.stop()

            # Mapping bauen
            username_to_id = {p["username"]: p["id"] for p in profiles}

            for i in range(st.session_state.anzahl_spieler):
                default_index = i
                auswahl = st.selectbox(f"Spieler {i+1}:", list(username_to_id.keys()), index=default_index, key=f"spieler_{i}" )
                auswahl_id = username_to_id[auswahl]
                spieler.append([auswahl, auswahl_id])
            user_ids = [s[1] for s in spieler]
            starten = st.form_submit_button("Los gehts🎯")

            if starten:
                if len(set(user_ids)) < st.session_state.anzahl_spieler:
                    st.error(f"Zackl-Zement! Choose {st.session_state.anzahl_spieler} unique players!")
                else:
                    st.session_state.runden_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")#
                    st.session_state.ende = False #
                    st.session_state.spieler = spieler #
                    st.session_state.spiele = [] #
                    st.session_state.anzahl = anzahl #
                    st.session_state.runde_aktiv = True #
                    st.session_state.start_info = Start_Info #
                    st.session_state.tournament = tournament #
                    save_round(st)
                    # Erstelle erst die Liste der Namen
                    player_list = [s[0] for s in spieler]
                    player_to_id = {s[0]: s[1] for s in spieler}
                    st.session_state.player_list = player_list
                    st.session_state.player_to_id = player_to_id

                    # Dann die Anzeige
                    st.success(f"Runde gestartet mit: {', '.join(player_list)}")
                    st.rerun()

    #########################################################################################
    # Spielerfassung:
    #########################################################################################

    if st.session_state.runde_aktiv:
        aussetzer = []
        if st.session_state.anzahl > 4:
            if st.session_state.anzahl == 5:
                a1 = st.selectbox("Diese SpielerIn setzt aus:", st.session_state.player_list, key="aus1")
                aussetzer.extend([[a1, st.session_state.player_to_id[a1]]])

            if st.session_state.anzahl == 6:
                a1 = st.selectbox("1. SpielerIn setzt aus:", st.session_state.player_list, key="aus1")
                # 2. Auswahl ohne den ersten Aussetzer
                rest = [s for s in st.session_state.player_list if s != a1]
                a2 = st.selectbox("2. SpielerIn setzt aus:", rest, key="aus2")
                aussetzer.extend([[a1, st.session_state.player_to_id[a1]], [a2, st.session_state.player_to_id[a2]]])

            if st.session_state.anzahl == 7:
                a1 = st.selectbox("1. SpielerIn setzt aus:", st.session_state.player_list, key="aus1")
                rest = [s for s in st.session_state.player_list if s != a1]

                a2 = st.selectbox("2. SpielerIn setzt aus:", rest, key="aus2")
                rest = [s for s in st.session_state.player_list if s not in [a1, a2]]

                a3 = st.selectbox("3. SpielerIn setzt aus:", rest, key="aus3")
                aussetzer.extend([[a1, st.session_state.player_to_id[a1]], [a2, st.session_state.player_to_id[a2]], [a3, st.session_state.player_to_id[a3]]])

        if "letztes_spiel" in st.session_state:
            st.success(st.session_state.letztes_spiel)

        if "eingabe_phase" not in st.session_state:
            st.session_state.eingabe_phase = 1

        if "spielart_temp" not in st.session_state:
            st.session_state.spielart_temp = None


        spielende_spieler = [s for s in st.session_state.spieler if s not in aussetzer]
        spielende_spieler_names = [s[0] for s in spielende_spieler]

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
                spielmacher = st.selectbox("Wer hat das Spiel angesagt?", spielende_spieler_names)
                spielmacher_id = st.session_state.player_to_id[spielmacher]
            if spielart == "Ramsch":
                spielmacher = st.selectbox("Wer hat den Ramsch verloren?", spielende_spieler_names)
                spielmacher_id = st.session_state.player_to_id[spielmacher]
            if st.session_state.KLOPFEN == False:
                klopfer = 0

            rufpartner = None
            rufpartner_id = None
            jungfrau = 0
            Sie = False
            tout = False

            if spielart == "Ruf":
                mögliche_rufpartner = [s for s in spielende_spieler_names if s != spielmacher]
                rufpartner = st.selectbox("RufpartnerIn", mögliche_rufpartner)
                rufpartner_id = st.session_state.player_to_id[rufpartner]
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
                    "Spielmacher": [spielmacher, spielmacher_id],
                    "Rufpartner": [rufpartner, rufpartner_id],
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
                update_round(st)
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
            df = berechne_statistik(st.session_state.player_list, st.session_state.spiele)
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
                update_round(st)

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
                    update_round(st)
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
        