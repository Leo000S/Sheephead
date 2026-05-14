import streamlit as st
import pandas as pd
from datetime import datetime
from services.supabase_client import supabase

from TurnierAuswahl import Turnier_Auswahl
from SheepHeadBook import spielwert_bestimmen_wue
from SheepHeadBook import spielwert_bestimmen_normal
from SheepHeadBook import (berechne_statistik)
from SheepHeadBook import load_open_rounds
from SheepHeadBook import update_round
from SheepHeadBook import save_round
from SheepHeadBook import load_profiles
from SpieleAuswahl import Aux, Wue, AllR, Standard

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

    st.session_state.SPIELWERTE = restrictions[0]
    st.session_state.KLOPFEN = restrictions[1]
    st.session_state.TOUT = restrictions[2]
    st.session_state.SIE = restrictions[3]
    st.session_state.mode = restrictions[4]


def load_profiles():
    response = supabase.table("profiles") \
        .select("id, username") \
        .order("username") \
        .execute()

    return response.data if response.data else []


def run_book():

    # --- Streamlit App ---
    st.set_page_config(page_title="Sheephead - the game of bavarian culture", layout="centered")

    st.session_state.profiles = load_profiles()
    if not st.session_state.profiles:
        st.error("Keine Profile gefunden.")
        st.stop()
    # Mapping bauen
    st.session_state.username_to_id = {p["username"]: p["id"] for p in st.session_state.profiles}

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

                # Hintergrundeinstellungen:
                resolve_restrictions(st.session_state.tournament)
                save_round(st)
                st.rerun()

    #########################################################################################
    # normaler Start einer Runde:
    #########################################################################################

        # Spieleranzahl muss außerhalb des Forms liegen!
        anzahl = st.number_input("Wie viele SpielerInnen?", min_value=4, max_value=7, value=4, key="anzahl_spieler")
        tournament = st.selectbox("Welche Turnierstatistik soll gefüllt werden?", Turnier_Auswahl)

        Start_Info = st.text_input("Infos zur Tischrundn (optional):")

        with st.form("runde_start"):
            st.write("Wählt die SpielerInnen aus!")
            spieler = []

            for i in range(st.session_state.anzahl_spieler):
                default_index = i
                auswahl = st.selectbox(f"Spieler {i+1}:", list(st.session_state.username_to_id.keys()), index=default_index, key=f"spieler_{i}" )
                auswahl_id = st.session_state.username_to_id[auswahl]
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

                    # Hintergrundeinstellung der Runde
                    resolve_restrictions(tournament)
                    save_round(st)
                    st.rerun()

    #########################################################################################
    # Spielerfassung:
    #########################################################################################

    if st.session_state.runde_aktiv:

        if st.session_state.anzahl < 7:

            if st.checkbox("➕ Weiteren Spieler nachtragen"):
                i = st.session_state.anzahl
                bereits = [s[0] for s in st.session_state.spieler]

                optionen = [
                    name for name in st.session_state.username_to_id.keys()
                    if name not in bereits
                ]

                if optionen:
                    auswahl = st.selectbox(
                        f"Spieler {i + 1}:",
                        optionen,
                        key=f"spieler_{i}"
                    )

                    if st.button("Spieler hinzufügen"):
                        auswahl_id = st.session_state.username_to_id[auswahl]
                        st.session_state.spieler.append([auswahl, auswahl_id])
                        st.session_state.anzahl = len(st.session_state.spieler)
                        st.rerun()

        # Erstelle erst die Liste der Namen
        player_list = [s[0] for s in st.session_state.spieler]
        player_to_id = {s[0]: s[1] for s in st.session_state.spieler}
        st.session_state.player_list = player_list
        st.session_state.player_to_id = player_to_id

        # Wer setzt die Runde aus?
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
                update_round(st)

                st.session_state.letztes_spiel = (spielmacher + " hat ein " + spielart + " für " + str(Punkte) + " (" + st.session_state.mode + ")" + Punkte_str + win_text)
                st.session_state.eingabe_phase = 1
                st.session_state.spielart_temp = None
                st.rerun()

    #########################################################################################
    # Anzeige der Statistik und Spiel zurücksetzen und Runde beenden:
    #########################################################################################

        # --- STATISTIK ---
        if st.session_state.spiele:
            st.subheader("Statistik der Tischrundn")
            df = berechne_statistik(st.session_state.player_list, st.session_state.spiele)
            if st.session_state.mode == "normal":
                ausblenden = ["Punkte_Wue", "Verloren", "Gespielt"]
                st.dataframe(
                    df.drop(columns=ausblenden),
                    hide_index=True)
            if st.session_state.mode == "wue":
                ausblenden = ["Punkte", "Verloren", "Gespielt"]
                st.dataframe(
                    df.drop(columns=ausblenden),
                    hide_index=True)

            # --- einzelne Spiele ---
            spiele_df = pd.DataFrame(st.session_state.spiele)
            spiele_df.index = range(1, len(spiele_df) + 1)
            spiele_df.reset_index(inplace=True)
            spiele_df.rename(columns={"index": "Spielnummer"}, inplace=True)

            # 2. Listen-Spalten "entpacken" (Nur den Namen extrahieren)
            for col in ["Spielmacher", "Rufpartner"]:
                if col in spiele_df.columns:
                    spiele_df[col] = spiele_df[col].apply(
                        lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x
                    )

            # 2. Mitspieler_Runde (Liste von Listen [[Name, ID], [Name, ID], ...])
            if "Mitspieler_Runde" in spiele_df.columns:
                spiele_df["Mitspieler_Runde"] = spiele_df["Mitspieler_Runde"].apply(
                    lambda x: ", ".join([spieler[0] for spieler in x if isinstance(spieler, list)])
                    if isinstance(x, list) else x
                )
            # Hier gibst du an, welche Spalten du behalten willst
            gewuenschte_spalten = ["Spielnummer", "Spielart", "Spielmacher", "Rufpartner", "Gewonnen", "Wert", "Wert_Wue", "Mitspieler_Runde"]
            spiele_anzeige_df = spiele_df[gewuenschte_spalten]
            st.dataframe(spiele_anzeige_df)

            # --- Kompakter Lösch-Bereich ---
            if st.session_state.spiele:
                cols = st.columns([2, 1, 1])  # Verhältnis der Breite: Auswahl, Check, Button

                with cols[0]:
                    spiel_optionen = list(range(1, len(st.session_state.spiele) + 1))
                    selected_nr = st.selectbox(
                        "Spiel löschen:",  # Label kurz halten
                        options=spiel_optionen,
                        index=len(spiel_optionen) - 1,
                        label_visibility="collapsed"  # Versteckt das Label für noch mehr Kompaktheit
                    )
                    idx = selected_nr - 1
                    s = st.session_state.spiele[idx]
                    sm = s.get('Spielmacher', ['?'])[0]
                    art = s.get('Spielart', 'Spiel')

                with cols[1]:
                    confirm = st.checkbox("Sicher?", key="del_conf")

                with cols[2]:
                    if st.button(f"#{selected_nr} Spiel löschen!", disabled=not confirm, use_container_width=True):
                        st.session_state.spiele.pop(idx)
                        st.toast(f"Spiel #{selected_nr} ({art} von {sm}) gelöscht!")  # Dezentes Feedback oben rechts
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
        