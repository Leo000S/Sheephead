import streamlit as st
from Statistik import analyse_display_playerstats, backup_df_to_supabase, process_supabase_rounds, make_Punkteart
from services.supabase_client import supabase

def run_player_statistics():

    # 1. Daten laden (mit Cache, damit es schnell geht)
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

    alle_tournaments = sorted(df["tournament"].dropna().unique())

    tournament = st.sidebar.selectbox("Turnier", options=["alle"] + alle_tournaments)

    OhneKlopfen = st.sidebar.checkbox("Soll das Klopfen herausgerechnent werden?")

    Punkteberechnung = st.sidebar.selectbox("Berechnung der Punkte", options = ["Normal", "Würzburg"])

    MinSpiele = st.sidebar.number_input("Mindestanzahl Spiele pro SpielerIn", min_value=0,step=20, value=0)

    Punkteart = make_Punkteart(Punkteberechnung, OhneKlopfen)


    tournament_filter = (
        [t for t in df["tournament"].unique() if t != "Allgäuer-Rundn"]
        if tournament == "alle"
        else [tournament]
    )

    # -------------------------------
    # Aktion
    # -------------------------------
    user_response = supabase.auth.get_user()
    if not user_response.user:
        st.error("Kein Benutzer angemeldet!")
    else:
        # Profil abfragen (Spaltenname ggf. auf 'id' oder 'user_id' anpassen)
        res = supabase.table("profiles").select("username").eq("user_id",
                                                               user_response.user.id).maybe_single().execute()

        # Username auslesen
        name = res.data["username"] if res.data else "Unbekannt"

    analyse_display_playerstats(df, name, MinSpiele, tournament_filter, Punkteberechnung, OhneKlopfen)

    with st.expander("ℹ️ Wie wird der Performance-Score berechnet?"):
        st.markdown("""
        Der Score bewertet das Spielkönnen auf einer Skala von **0 bis 10 Punkten** und wird **ab mindestens 10 Spielen** der jeweiligen Spielart berechnet.

        ### Die Formel (für Ruf, Trumpfsolo, Wenz, Bettel):
        """)
        st.latex(
            r"\text{Score} = (\text{GQ}_A^n \times 4) + (\text{GQ}_P^n \times 3) + (\text{PQ}^n \times 2) + (\text{AQ}_{faktor}^n \times 1)")

        st.markdown("""
        * **$ GQ_A^n$ (40%):** im Vergleich zur Gesamtstatistik normierte Gewinnquote als aktiver SpielerIn.
        * **$ GQ_P^n$ (30%):** im Vergleich zur Gesamtstatistik normierte Gewinnquote als NichtspielerIn.
        * **$ PQ^n$ (20%):** im Vergleich zur Gesamtstatistik normierte Punkteschnitt ($PQ$).
        * **$ AQ_{faktor}^n$ (10%):** Mut-Faktor, volle Punktzahl ab 25%.

        ### Sonderfall Ramsch:
        Da kein Spieler aktiv ansagt, entfällt der Mut-Faktor. Der Score berechnet sich aus **60% Gesamt-Gewinnquote** und **40% Punkte-Effizienz** (Punkte normiert von $0 \rightarrow 60$ gefressene Augen, je weniger desto besser).
        """)
