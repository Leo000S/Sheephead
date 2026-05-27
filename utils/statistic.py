
import streamlit as st
from Statistik import backup_process_data, load_df_from_supabase_backup, analyse_all_players, analyse_different_stats, filter_spiele, plot_stats_streamlit, group_in_usernames
from services.supabase_client import supabase

# =====================================================================
# 3. STREAMLIT UI
# =====================================================================

def run_statistics():
    st.title("Schafkopf Statistik")

    # Daten blitzschnell aus dem Cache (oder frisch aus dem Storage Backup) holen
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

    alle_spielarten = sorted(df["Spielart"].dropna().unique())
    alle_tournaments = sorted(df["tournament"].dropna().unique())
    alle_spieler = list(st.session_state.id_to_username.values())

    namen_einzel = st.sidebar.multiselect("SpielerInnen", options=alle_spieler)

    # Hier nutzen wir nun unser dynamisches Dictionary
    DYNA_GRUPPEN = group_in_usernames()
    gruppen_auswahl = st.sidebar.multiselect("Gruppen", options=list(DYNA_GRUPPEN.keys()))

    namen = set(namen_einzel)
    for gruppe in gruppen_auswahl:
        namen.update(DYNA_GRUPPEN[gruppe])

    namen = list(namen)

    spielarten = st.sidebar.multiselect("Spielart", options= ["alle"] + alle_spielarten)

    tournament = st.sidebar.selectbox("Turnier", options=["alle"] + alle_tournaments)

    OhneKlopfen = st.sidebar.checkbox("Soll das Klopfen herausgerechnent werden?")

    # exclude_strangers = st.sidebar.checkbox("Nur Spiele mit ausgewählten SpielerInnen")

    Punkteberechnung = st.sidebar.selectbox("Berechnung der Punkte", options = ["Normal", "Würzburg"])

    MinSpiele = st.sidebar.number_input("Mindestanzahl Spiele pro SpielerIn", min_value=0,step=20, value=0)

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

    if st.button("Anzeigen"):
        df_result = filter_spiele(
            df,
            namen=namen if namen else None,
            spielarten=spielarten if spielarten else None,
            tournament=tournament_filter
        )


        spieler_stats = analyse_all_players(df_result, namen, MinSpiele)
        if spieler_stats != {}:
            overview = analyse_different_stats(spieler_stats, Punkteart, show=True)
            st.dataframe(overview, use_container_width=True, height=600)
            plot_stats_streamlit(spieler_stats, KeyKumulativ)

        else:
            st.write("⬅️ Bitte wähle SpielerInnen aus!")

    else:
        st.info("⬅️ Filter auswählen und auf **Anzeigen** klicken")
