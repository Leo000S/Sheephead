import io
import streamlit as st
import pandas as pd

from Statistik import analyse_all_players
from Statistik import analyse_different_stats
from Statistik import filter_spiele
from Statistik import plot_stats_streamlit
from services.supabase_client import supabase

def group_in_usernames():
    profiles_res = supabase.table("profiles").select("user_id, username").execute()
    id_to_name = {p["user_id"]: p["username"] for p in profiles_res.data}

    # 2. Gruppen aus Supabase laden
    groups_res = supabase.table("groups").select("groupname, members").execute()

    # 3. Das SPIELER_GRUPPEN Dictionary dynamisch bauen
    # Wir wandeln die Liste der IDs direkt in die Liste der Namen um
    DYNA_GRUPPEN = {}
    for g in groups_res.data:
        g_name = g["groupname"]
        member_ids = g.get("members", [])
        # Nur Namen hinzufügen, die wir auch in der Profiles-Tabelle finden
        member_names = [id_to_name[m_id] for m_id in member_ids if m_id in id_to_name]
        DYNA_GRUPPEN[g_name] = member_names
    return DYNA_GRUPPEN

def get_id_to_username_map():
    try:
        response = supabase.table("profiles").select("id, username").execute()
        # Erstellt ein Dictionary: {'uuid1': 'Username1', 'uuid2': 'Username2'}
        return {row['id']: row['username'] for row in response.data}
    except Exception as e:
        st.error(f"Fehler beim Laden der Profile: {e}")
        return {}

def backup_df_to_supabase(df, filename="spiele_backup.csv"):
    # 1. DataFrame in CSV (im Speicher) umwandeln
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    # 2. Upload zu Supabase Storage
    # Das 'upsert': True sorgt dafür, dass die alte Datei überschrieben wird
    response = supabase.storage.from_('all_games').upload(
        path=filename,
        file=csv_bytes,
        file_options={"content-type": "text/csv", "x-upsert": "true"}
    )
    return response


def process_supabase_rounds(supabase_rows, id_to_name_map):
    if not supabase_rows:
        return pd.DataFrame()

    # Sortieren nach Erstellungszeitpunkt
    supabase_rows.sort(key=lambda x: x["created_at"])

    all_games = []
    seen_game_timestamps = set()

    for row in supabase_rows:
        data = row.get("data", {})
        runden_ts = row.get("created_at")
        games_list = data.get("spiele", [])

        # --- Namen für die gesamte Runde vorab bestimmen ---
        mitspieler_raw = data.get("spieler", [])  # [["Name_Alt", "ID"], ...]

        runden_ids = []
        runden_namen_aktuell = []

        for s in mitspieler_raw:
            if isinstance(s, list) and len(s) >= 2:
                uid = s[1]
                runden_ids.append(uid)
                # Prio 1: Name aus Profil-Tabelle, Prio 2: Name aus Spieldatei
                runden_namen_aktuell.append(id_to_name_map.get(uid, s[0]))
            else:
                runden_ids.append(None)
                runden_namen_aktuell.append(s)

        for game in games_list:
            # Zeitstempel & Metadaten
            game_ts = game.get("Zeitstempel", runden_ts)
            while game_ts in seen_game_timestamps:
                game_ts = str(game_ts) + "A"
            game["Zeitstempel"] = game_ts
            seen_game_timestamps.add(game_ts)

            game.update({
                "tournament": data.get("tournament"),
                "runden_timestamp": data.get("runden_timestamp", runden_ts),
                "start_info": data.get("start_info", ""),
                "Mitspieler_Runde": runden_namen_aktuell,
                "MitspielerRundeIds": runden_ids
            })

            # --- Spielmacher Zuordnung ---
            sm_raw = game.get("Spielmacher")
            if isinstance(sm_raw, list) and len(sm_raw) == 2:
                uid = sm_raw[1]
                game["SpielmacherId"] = uid
                game["Spielmacher"] = id_to_name_map.get(uid, sm_raw[0])
            else:
                game["SpielmacherId"] = None

            # --- Rufpartner Zuordnung ---
            rp_raw = game.get("Rufpartner")
            if isinstance(rp_raw, list) and len(rp_raw) == 2:
                uid = rp_raw[1]
                game["RufpartnerId"] = uid
                game["Rufpartner"] = id_to_name_map.get(uid, rp_raw[0])
            else:
                game["RufpartnerId"] = None

            all_games.append(game)

    final_df = pd.DataFrame(all_games)

    if not final_df.empty:
        if "Spielnummer" in final_df.columns:
            final_df.drop(columns=["Spielnummer"], inplace=True)
        final_df.insert(0, "Spielnummer", range(1, len(final_df) + 1))

    return final_df
# ===============================
# Streamlit UI
# ===============================
def run_statistics():
    st.title("Statistik")

    # 1. Daten laden (mit Cache, damit es schnell geht)
    @st.cache_data(ttl=600)  # Speichert die Daten für 10 Minuten im RAM
    def load_and_process_data():
        name_map = get_id_to_username_map()
        response = supabase.table("rounds").select("*").execute()
        return process_supabase_rounds(response.data, name_map)

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
    st.write(df)


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
