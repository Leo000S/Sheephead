import io
import streamlit as st
import pandas as pd
from Statistik import backup_df_to_supabase, process_supabase_rounds, analyse_all_players, analyse_different_stats, filter_spiele, plot_stats_streamlit, group_in_usernames
from services.supabase_client import supabase
# ===============================
# Streamlit UI
# ===============================
def run_statistics():
    st.title("Statistik")

    # 1. Daten laden (mit Cache, damit es schnell geht)
    @st.cache_data(ttl=600)  # Speichert die Daten für 10 Minuten im RAM
    def load_and_process_data():
        response = supabase.table("rounds").select("*").execute()
        return process_supabase_rounds(response.data)

    try:
        final_df = load_and_process_data()
        backup_df_to_supabase(final_df, filename="spiele_backup.csv")

    except Exception as e:
        st.error(f"Fehler beim Laden der Statistik: {e}")

    if st.button("Daten neu laden"):
        try:
            final_df = load_and_process_data()
            backup_df_to_supabase(final_df, filename="spiele_backup.csv")

        except Exception as e:
            st.error(f"Fehler beim Laden der Statistik: {e}")

    # Das ist dein DF für die restliche Statistik-Seite
    df = final_df

    alle_spielarten = sorted(df["Spielart"].dropna().unique())
    alle_tournaments = sorted(df["tournament"].dropna().unique())


    # 1. Alle Profile laden (Mapping von ID zu Username erstellen)
    profiles_res = supabase.table("profiles").select("user_id, username").execute()
    id_to_name = {p["user_id"]: p["username"] for p in profiles_res.data}
    alle_spieler = list(id_to_name.values())

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

    # -------------------------------
    # Aktion
    # -------------------------------

    if st.button("📊 Anzeigen"):
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
