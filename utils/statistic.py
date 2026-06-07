
import streamlit as st
from Statistik import backup_process_data, load_df_from_supabase_backup, analyse_all_players, analyse_different_stats, filter_spiele, plot_stats_streamlit, group_in_usernames
from services.supabase_client import supabase
from utils.book import hole_alle_turniere

# =====================================================================
# 3. STREAMLIT UI
# =====================================================================

def run_statistics():
    st.title("Schafkopf Statistik")
    df = load_df_from_supabase_backup()

    if df is None or df.empty:
        st.warning("Keine Spieldaten im Backup gefunden.")

    # Wenn der Button geklickt wird, läuft der Code im if-Block
    if st.button("Daten aktualisieren"):
        with st.spinner("Aktualisieren..."):
            # 1. Frische Daten aus der DB holen und neues Backup im Storage überschreiben
            backup_process_data()

        st.success("Erfolgreich aktualisiert!")
        # 3. Die App kurz neu starten, damit sie die frischen Daten direkt zeichnet
        st.rerun()

    alle_spielarten = sorted(df["Spielart"].dropna().unique())

    # 1. Alle Gruppen aus der DB holen
    alle_gruppen = supabase.table("groups").select("groupname, members").execute().data
    group = st.sidebar.selectbox(
        "Gruppe",
        options=["Alle Gruppen"] + alle_gruppen,
        format_func=lambda g: g["groupname"] if isinstance(g, dict) else g
    )

    erlaubte_spieler = list(st.session_state.id_to_username.values())

    tournament = "alle Turniere"
    if group != "Alle Gruppen":
        gruppen_mitglieder_ids = group["members"] if group else []
        erlaubte_spieler = [ name for name, uid in st.session_state.username_to_id.items() if uid in gruppen_mitglieder_ids ]
        Turnier_Komplett = hole_alle_turniere(group["groupname"])
        Turnier_Auswahl = [t["name"] for t in Turnier_Komplett]
        tournament = st.sidebar.selectbox("Turnier", options=["alle Turniere"] + Turnier_Auswahl)

    namen_einzel = st.sidebar.multiselect("SpielerInnen", options=erlaubte_spieler)
    if st.sidebar.checkbox("Alle Spieler auswählen?"):
        namen_einzel = erlaubte_spieler
    namen = set(namen_einzel)

    namen_ids = [
        user_id for user_id, username in st.session_state.id_to_username.items()
        if username in namen
    ]

    spielarten = st.sidebar.multiselect("Spielart", options=["alle"] + alle_spielarten)

    OhneKlopfen = st.sidebar.checkbox("Soll das Klopfen herausgerechnent werden?")

    OnlyNames = st.sidebar.checkbox("Nur Runden mit den ausgewählten SpielerInnen")

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
        if tournament == "alle Turniere"
        else [tournament]
    )

    if st.button("Anzeigen"):
        df_result = filter_spiele(
            df,
            namen_ids=namen_ids if namen_ids else None,
            group=[group["groupname"]] if group != "Alle Gruppen" else None,
            spielarten=spielarten if spielarten else None,
            tournament=tournament_filter,
            modus = OnlyNames
        )


        spieler_stats = analyse_all_players(df_result, namen_ids, MinSpiele)
        if spieler_stats != {}:
            overview = analyse_different_stats(spieler_stats, Punkteart, show=True)
            st.dataframe(overview, use_container_width=True, height=600)
            plot_stats_streamlit(spieler_stats, KeyKumulativ)

        else:

            st.write("⬅️ Bitte wähle SpielerInnen aus!")

    else:
        st.info("⬅️ Filter auswählen und auf **Anzeigen** klicken")
