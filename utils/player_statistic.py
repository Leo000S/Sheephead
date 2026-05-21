import streamlit as st
from Statistik import analyse_display_playerstats, backup_process_data, load_df_from_supabase_backup

def run_player_statistics():
    df = load_df_from_supabase_backup()

    if df is None or df.empty:
        st.warning("Keine Spieldaten im Backup gefunden.")

    # Wenn der Button geklickt wird, läuft der Code im if-Block
    if st.button("Daten aktualisieren"):
        with st.spinner("Aktualisieren..."):
            # 1. Frische Daten aus der DB holen und neues Backup im Storage überschreiben
            backup_process_data()
            load_df_from_supabase_backup.clear()

        st.success("Erfolgreich aktualisiert!")
        # 3. Die App kurz neu starten, damit sie die frischen Daten direkt zeichnet
        st.rerun()

    alle_tournaments = sorted(df["tournament"].dropna().unique())

    tournament = st.sidebar.selectbox("Turnier", options=["alle"] + alle_tournaments)

    OhneKlopfen = st.sidebar.checkbox("Soll das Klopfen herausgerechnent werden?")

    Punkteberechnung = st.sidebar.selectbox("Berechnung der Punkte", options = ["Normal", "Würzburg"])

    MinSpiele = 10

    tournament_filter = (
        [t for t in df["tournament"].unique() if t != "Allgäuer-Rundn"]
        if tournament == "alle"
        else [tournament]
    )

    name = st.session_state.current_username
    if name == "Leo Schaller":
        alle_spieler = list(st.session_state.id_to_username.values())
        name = st.sidebar.selectbox("SpielerInnen", options=alle_spieler)

    if st.button("Anzeigen"):
        rows = analyse_display_playerstats(df, name, MinSpiele, tournament_filter, Punkteberechnung, OhneKlopfen)

        try:
            combinedscore = (
                    0.3 * rows["Ruf"]["Score"]
                    + 0.3 * rows["Trumpfsolo"]["Score"]
                    + 0.3 * rows["Wenz + Geier"]["Score"]
                    + 0.05 * rows["Ramsch"]["Score"]
                    + 0.05 * rows["Bettel"]["Score"]
            )
            st.write(f"Du erhältst einen Gesamt-Performance-Score von {round(combinedscore, 3)}")

        except KeyError:
            st.write(f"Spiele mehr Schafkopf, um deinen Gesamt-Score zu erfahren!!!")

        with st.expander("ℹ️ Wie wird der Performance-Score berechnet?"):
            st.markdown("""
            Der Score bewertet das Spielkönnen auf einer Skala von **0 bis 10 Punkten** und wird **ab mindestens 10 Spielen** der jeweiligen Spielart berechnet.
    
            ### Die Formel (für Ruf, Trumpfsolo, Wenz+Geier, Bettel):
            """)
            st.latex(
                r"\text{Score} = (\text{GQ}_A^n \times 4) + (\text{GQ}_P^n \times 3) + (\text{PQ}^n \times 2) + (\text{AQ}_{faktor}^n \times 1)")

            st.markdown("""
            * **$ GQ_A^n$ (20%):** im Vergleich zur Gesamtstatistik normierte Gewinnquote als aktiver SpielerIn.
            * **$ GQ_P^n$ (20%):** im Vergleich zur Gesamtstatistik normierte Gewinnquote als NichtspielerIn.
            * **$ PQ^n$ (50%):** im Vergleich zur Gesamtstatistik normierte Punkteschnitt ($PQ$).
            * **$ AQ_{faktor}^n$ (10%):** Mut-Faktor, volle Punktzahl ab 25%.
    
            ### Sonderfall Ramsch:
            Da kein Spieler aktiv ansagt, entfällt der Mut-Faktor. Der Score berechnet sich aus **60% Gesamt-Gewinnquote** und **40% Punkte-Effizienz** (Punkte normiert von $0 \rightarrow 60$ gefressene Augen, je weniger desto besser).
            
            ### Gesamt-Performance-Score:
            Hier werden die Scores aller Spiele zusammngezählt. Man erhält eine Zahl zwischen 0 und 10.
            """)
