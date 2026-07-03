import io
from services.supabase_client import supabase
import streamlit as st
import numpy as np
import pandas as pd
import ast

# Berechnet aus allen Spielen eines Spielers die Punkte (wue, normal und mit/ohne Klopfen)
def punkte_abspeichern(df_player, player):
    # Gewinnlogik:
    # - Wenn Spieler = Spielmacher oder Rufpartner und Gewonnen == True → Spieler gewinnt
    # - Wenn Spieler NICHT Spielmacher oder Rufpartner und Gewonnen == False → Spieler gewinnt
    # → Sonst verliert er
    if df_player.empty:
        df_player = pd.DataFrame([{
            "Hat_gewonnen": False,
            "Punkte": 0,
            "Punkte_Wue": 0,
            "Punkte_NK": 0,
            "Punkte_NK_Wue": 0
        }])
    else:
        df_player["Hat_gewonnen"] = df_player.apply(
            lambda x: (
                (x["Gewonnen"] == True and (player in [x["SpielmacherId"], x["RufpartnerId"]])) or
                (x["Gewonnen"] == False and player not in [x["SpielmacherId"], x["RufpartnerId"]])
            ),
            axis=1
        )
        # Anwenden auf DataFrame
        df_player[["Punkte", "Punkte_Wue", "Punkte_NK", "Punkte_NK_Wue"]] = df_player.apply(lambda x: berechne_punkte(x, player), axis=1)
        
    # Kumulativer Punktestand über die Zeit
    df_player["Kumulativer Punktestand"] = df_player["Punkte"].cumsum()
    df_player["Kumulativer Punktestand_Wue"] = df_player["Punkte_Wue"].cumsum()
    df_player["Kumulativer Punktestand_NK"] = df_player["Punkte_NK"].cumsum()
    df_player["Kumulativer Punktestand_NK_Wue"] = df_player["Punkte_NK_Wue"].cumsum()
    
    standardabweichung = {
    "stdPunkte": df_player["Punkte"].std(ddof=0),
    "stdPunkte_Wue": df_player["Punkte_Wue"].std(ddof=0),
    "stdPunkte_NK": df_player["Punkte_NK"].std(ddof=0),
    "stdPunkte_NK_Wue": df_player["Punkte_NK_Wue"].std(ddof=0),
    }
    return df_player


# Wir in Punkte abspeichern benötigt
def berechne_punkte(x, player):
    # Basiswert: + oder - je nach Sieg/Niederlage
    punkte = x["Wert"] if x["Hat_gewonnen"] else -x["Wert"]
    punkte_wue = x["Wert_Wue"] if x["Hat_gewonnen"] else -x["Wert_Wue"]
    # Weil es noch einen alten datentyp gibt...
    if np.isnan(x.get("Wert_NK", np.nan)) or np.isnan(x.get("Wert_Wue_NK", np.nan)):
        punkte_NK = x["Wert"]/(2**(x["Klopfer"])) if x["Hat_gewonnen"] else -x["Wert"]/(2**(x["Klopfer"]))
        punkte_NK_wue = x["Wert_Wue"]/(1+(x["Klopfer"])) if x["Hat_gewonnen"] else -x["Wert_Wue"]/(1+(x["Klopfer"]))  
    else: 
        punkte_NK = x["Wert_NK"] if x["Hat_gewonnen"] else -x["Wert_NK"]
        punkte_NK_wue = x["Wert_Wue_NK"] if x["Hat_gewonnen"] else -x["Wert_Wue_NK"]
    
    # Sonderfall: Kein Rufpartner → dreifacher Wert nur für Spielmacher
    if (pd.isna(x["RufpartnerId"]) or str(x["RufpartnerId"]).strip() == "") and player == x["SpielmacherId"]:
        punkte *= 3
        punkte_wue *= 3
        punkte_NK *= 3
        punkte_NK_wue *= 3
    
    return pd.Series([punkte, punkte_wue, punkte_NK, punkte_NK_wue])


def analyze_single_player(player, df, MinSpiele):
    """Analysiert die Daten für einen einzelnen Spieler (reine Strings)."""

    # 1. Filter: Spiele, bei denen der Spieler am Tisch saß (als String-Suche)
    def player_in_row(cell):
        try:
            liste = ast.literal_eval(cell) if isinstance(cell, str) else cell
            return player in liste
        except:
            return False

    df_player = df[df["MitspielerRundeIds"].apply(player_in_row)].copy()

    # Kriterien für Mindestspiele prüfen
    if df_player.empty or len(df_player) < MinSpiele:
        return None

    # Sortieren nach Zeitstempel und Punkte berechnen
    df_player.sort_values("Zeitstempel", inplace=True)
    df_player = punkte_abspeichern(df_player, player)

    # Basis-Statistiken
    spiele_len = len(df_player)
    gewonnene_spiele = df_player["Hat_gewonnen"].sum()
    quote = (gewonnene_spiele / spiele_len * 100) if spiele_len > 0 else 0

    # 2. Filter: Nur die Spiele als aktiver Spielmacher (ohne Ramsch)
    df_player_s = df_player[
        (df_player["SpielmacherId"] == player) &
        (df_player["Spielart"] != "Ramsch")
        ].copy()

    anzahl_spielmacher = len(df_player_s)
    anzahl_ramsch = len(df_player[(df_player["Spielart"] == "Ramsch")].copy())
    spiele_len_minus_ramsch = spiele_len - anzahl_ramsch
    anteil_spielmacher = (anzahl_spielmacher / spiele_len_minus_ramsch * 100) if spiele_len_minus_ramsch > 0 else 0

    # Punkte für die Runden als Spielmacher berechnen (falls vorhanden)
    if not df_player_s.empty:
        df_player_s = punkte_abspeichern(df_player_s, player)

    # 1. Spiele als Rufpartner herausfiltern
    df_player_rp = df_player[df_player["RufpartnerId"] == player]
    anzahl_rufpartner = len(df_player_rp)

    # 2. Siege als Rufpartner zählen (Wenn das Team gewonnen hat, hat auch der Rufpartner gewonnen)
    if not df_player_rp.empty:
        gewonnen_rufpartner = df_player_rp["Hat_gewonnen"].sum()
    else:
        gewonnen_rufpartner = 0

    # ---------------------------------------------------------
    # Gewinnquote als reine/r GegenspielerIn (Nicht-SpielerIn)
    # ---------------------------------------------------------
    # Wir ziehen Spielmacher- UND Rufpartner-Spiele von den Gesamtspielen ab
    nicht_spieler_spiele = spiele_len - anzahl_spielmacher - anzahl_rufpartner

    if nicht_spieler_spiele > 0:
        # Siege als Spielmacher ermitteln
        gewonnen_spielmacher = df_player_s["Hat_gewonnen"].sum() if not df_player_s.empty else 0

        # Reine Gegenspieler-Siege = Gesamte Siege minus (Siege als Chef + Siege als Partner)
        gewonnen_nicht_spieler = gewonnene_spiele - gewonnen_spielmacher - gewonnen_rufpartner

        quote_nicht_spieler = round((gewonnen_nicht_spieler / nicht_spieler_spiele) * 100, 2)
    else:
        quote_nicht_spieler = 0.0

    # Statistiken zusammenstellen
    player_stat = {
        "Spiele": df_player,
        "Anzahl_Spiele": spiele_len,
        "Gewonnene_Spiele": gewonnene_spiele,
        "Gewinnquote": round(quote, 1),
        "Anzahl_Spiele als SpielerIn": anzahl_spielmacher,
        "Ansagequote": round(anteil_spielmacher, 1),
        "Gewonnen als SpielerIn": df_player_s["Hat_gewonnen"].sum() if not df_player_s.empty else 0,
        "Gewinnquote als Nicht-SpielerIn": quote_nicht_spieler,

        # Endpunktestände als Mitspieler
        "Endpunktestand": df_player["Kumulativer Punktestand"].iloc[
            -1] if "Kumulativer Punktestand" in df_player else 0,
        "Endpunktestand_Wue": df_player["Kumulativer Punktestand_Wue"].iloc[
            -1] if "Kumulativer Punktestand_Wue" in df_player else 0,
        "Endpunktestand_NK": df_player["Kumulativer Punktestand_NK"].iloc[
            -1] if "Kumulativer Punktestand_NK" in df_player else 0,
        "Endpunktestand_NK_Wue": df_player["Kumulativer Punktestand_NK_Wue"].iloc[
            -1] if "Kumulativer Punktestand_NK_Wue" in df_player else 0,

        # Endpunktestände als aktiver Spieler
        "sEndpunktestand": df_player_s["Kumulativer Punktestand"].iloc[
            -1] if not df_player_s.empty and "Kumulativer Punktestand" in df_player_s else 0,
        "sEndpunktestand_Wue": df_player_s["Kumulativer Punktestand_Wue"].iloc[
            -1] if not df_player_s.empty and "Kumulativer Punktestand_Wue" in df_player_s else 0,
        "sEndpunktestand_NK": df_player_s["Kumulativer Punktestand_NK"].iloc[
            -1] if not df_player_s.empty and "Kumulativer Punktestand_NK" in df_player_s else 0,
        "sEndpunktestand_NK_Wue": df_player_s["Kumulativer Punktestand_NK_Wue"].iloc[
            -1] if not df_player_s.empty and "Kumulativer Punktestand_NK_Wue" in df_player_s else 0
    }

    return player_stat


def analyse_all_players(df, all_ids, MinSpiele):
    """Hauptfunktion, die durch alle Spieler iteriert."""
    spieler_stats = {}
    for ids in all_ids:
        # Aufruf der ausgelagerten Funktion
        player_stat = analyze_single_player(ids, df, MinSpiele)
        # Nur speichern, wenn der Spieler genug Spiele hatte (nicht None ist)
        if player_stat is not None:
            player = st.session_state.id_to_username[ids]
            spieler_stats[player] = player_stat

    return spieler_stats


# schreibt "Treppchen" etc.
def show_block(title, df, interesting_key):
        st.write(title)
        st.write(df[interesting_key].round(2))


# Erstellt die vergleichende Statistik des Turniers, also die große Tabelle in run_statistic()
def analyse_different_stats(spieler_stats, Punkteart, show=False):
      
    overview = pd.DataFrame.from_dict(
        {
            player: {
                "Spiele": stats["Anzahl_Spiele"],
                "Punkte": float(stats[Punkteart]),
                "PQ": round(stats[Punkteart]/stats["Anzahl_Spiele"] if stats["Anzahl_Spiele"] > 0 else 0, 1),
                "GQ (%)": round(stats["Gewinnquote"], 1),
                "AQ (%)": round(stats["Ansagequote"], 1),
                "GQ als SpielerIn (%)": round(stats["Gewonnen als SpielerIn"]/stats["Anzahl_Spiele als SpielerIn"] * 100 if stats["Anzahl_Spiele als SpielerIn"] > 0 else 0, 1),
                "PQ als SpielerIn": round(stats[f"s{Punkteart}"]/stats["Anzahl_Spiele als SpielerIn"] if stats["Anzahl_Spiele als SpielerIn"] > 0 else 0, 1),
                "GQ als nicht SpielerIn (%)":  round(stats["Gewinnquote als Nicht-SpielerIn"], 1),
            }
            for player, stats in spieler_stats.items()
        },
        orient="index"
    )

    # Indexname setzen
    overview.index.name = "SpielerIn"
    
    # Nach Punkten sortieren
    overview = overview.sort_values("Punkte", ascending=False)  
    
    top_3_punkte = overview.sort_values("Punkte", ascending=False).head(3)
    flop_3_punkte = overview.sort_values("Punkte", ascending=True).head(3)
    top_3_quote = overview.sort_values("GQ (%)", ascending=False).head(3)
    top_3_spielmacher = overview.sort_values("AQ (%)", ascending=False).head(3)
        
    if show == True:
        show_block("Das Treppchen:", top_3_punkte, "Punkte")
        show_block("Pech im Spiel - Glück in der Liebe:", flop_3_punkte, "Punkte")
        show_block("Die GewinnertypInnen:", top_3_quote, "GQ (%)")
        show_block("DIe SpielgestalterInnen:", top_3_spielmacher, "AQ (%)")

    return overview


# Macht den plot in run_statistic()
import plotly.graph_objects as go
def plot_stats_streamlit(spieler_stats, KeyKumulativ):

    fig = go.Figure()

    for player, stats in spieler_stats.items():
        df_player = stats["Spiele"]

        if KeyKumulativ not in df_player.columns:
            st.warning(f"Kein Punktestand für {player} gefunden – übersprungen.")
            continue

        y = df_player[KeyKumulativ].values
        x = np.arange(1, len(y) + 1) / len(y)

        # Startpunkt (0,0)
        x = np.insert(x, 0, 0)
        y = np.insert(y, 0, 0)

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines+markers",
                name=player,
                hovertemplate="<b>%{fullData.name}</b><extra></extra>"
            )
        )

    fig.update_layout(
        title="Entwicklung der Punkte",
        xaxis_title="Spiele normiert",
        yaxis_title=KeyKumulativ,
        hovermode="closest",
        legend=dict(orientation="h", y=-0.2),
        height=700
    )

    st.plotly_chart(fig, use_container_width=True)

print_filter = False

# Setzt die filter in run_statistic() um:
def filter_spiele(
    df: pd.DataFrame,
    namen_ids=None,
    group=None,
    spielarten=None,
    tournament=None,
    modus=False  # Wenn True, müssen ALLE Spieler der Runde aus 'namen' sein
):
    df_f = df.copy()

    if namen_ids:
        if modus == True:
            # NEUER MODUS: Alle Spieler (s) der Runde müssen im namen-Pool existieren
            df_f = df_f[
                df_f["MitspielerRundeIds"].apply(
                    lambda spieler_liste: all(
                        s in namen_ids
                        for s in (
                            ast.literal_eval(spieler_liste)
                            if isinstance(spieler_liste, str)
                            else spieler_liste
                        )
                    )
                )
            ]
            if print_filter:
                st.write("Filter 1")
                st.write(df_f)
        else:
            df_f = df_f[
                df_f["MitspielerRundeIds"].apply(
                    lambda spieler_liste: any(
                        n == s
                        for n in namen_ids
                        for s in (
                            ast.literal_eval(spieler_liste)
                            if isinstance(spieler_liste, str)
                            else spieler_liste
                        )
                    )
                )
            ]
            if print_filter:
                st.write("Filter 2")
                st.write(df_f)
    if group:
        df_f = df_f[df_f["groupname"].isin(group)]
        if print_filter:
            st.write("Filter 3")
            st.write(df_f)
    # --- Spielart ---
    if spielarten and "alle" not in spielarten:
        df_f = df_f[df_f["Spielart"].isin(spielarten)]
        if print_filter:
            st.write("Filter 4")
            st.write(df_f)
    # --- Tournament ---
    if tournament:
        df_f = df_f[df_f["tournament"].isin(tournament)]
        if print_filter:
            st.write("Filter 5")
            st.write(df_f)

    # 2. Deine bestehende Turnier-Filterung (auf 'is not None' korrigiert)
    if tournament is None:
        df_f = df_f[df_f["tournament"] != "Allgäuer-Rundn"]

    return df_f


def make_Punkteart(Punkteberechnung, OhneKlopfen):
    if Punkteberechnung == "Würzburg":
        Punkteart = "Endpunktestand_Wue"
    if Punkteberechnung == "Normal":
        Punkteart = "Endpunktestand"

    if OhneKlopfen == True:
        Punkteart = Punkteart[0:14] + "_NK" + Punkteart[14:]

    return Punkteart

def get_player_stats_row(stats, Punkteberechnung, OhneKlopfen):
    """Bereitet die Statistiken für eine Spielart als Tabellenzeile vor."""
    anzahl_spiele = stats["Anzahl_Spiele"]
    anzahl_spieler = stats["Anzahl_Spiele als SpielerIn"]
    punkteart = make_Punkteart(Punkteberechnung, OhneKlopfen)

    # Berechnungen
    pq = stats[punkteart] / anzahl_spiele if anzahl_spiele > 0 else 0

    pq_spieler = stats[f"s{punkteart}"] / anzahl_spieler if anzahl_spieler > 0 else 0
    gq_spieler = (stats["Gewonnen als SpielerIn"] / anzahl_spieler * 100) if anzahl_spieler > 0 else 0

    # Flaches Dictionary für die Tabellenzeile zurückgeben
    return {
        "Spiele": anzahl_spiele,
        "PQ": round(pq, 2),
        "GQ": round(stats["Gewinnquote"], 1),  # Für st.column_config.ProgressColumn durch 100 teilen
        "AQ": round(stats["Ansagequote"], 1),
        "GQ als SpielerIn": round(gq_spieler, 1),
        "PQ als SpielerIn": round(pq_spieler, 2),
        "GQ als NichtspielerIn": round(stats["Gewinnquote als Nicht-SpielerIn"], 1)
    }

import json
from scipy.stats import norm


def norm_value(val, avg, std):
    # Falls alle Spieler exakt denselben Wert haben (std == 0),
    # liegt der Spieler exakt im Durchschnitt, also bei 0.5
    if std == 0 or pd.isna(std):
        return 0.5

    # 1. Schritt: Wie viele Standardabweichungen liegt der Wert vom Schnitt entfernt?
    z_score = (val - avg) / std

    # 2. Schritt: z-Score auf die Skala 0.0 bis 1.0 mappen (Gauß-Glocke)
    norm_value = norm.cdf(z_score)

    return round(norm_value, 3)

def calculate_performance_score(row_dict, spielart, Punkteberechnung, OhneKlopfen):
    with open("stats_uebersicht.json", "r", encoding="utf-8") as f:
        stats_uebersicht = json.load(f)
        # Sicherer Zugriff, egal ob echtes Dict oder aus JSON geladen:
        klopf_key = str(OhneKlopfen)  # Macht aus True -> "True" oder aus false -> "False"

        # Falls JSON es kleingeschrieben hat (z.B. "true"), kannst du .lower() nutzen:
        klopf_key = str(OhneKlopfen).lower()  # Macht "true" oder "false"

        stats = stats_uebersicht[Punkteberechnung][klopf_key][spielart]


    anzahl_spiele = row_dict.get("Spiele", 0)
    if anzahl_spiele < 10:  # Schutz vor Verzerrung bei zu wenigen Spielen
        return None

    gq_aktiv = row_dict.get("GQ als SpielerIn", 0)
    gq_passiv = row_dict.get("GQ als NichtspielerIn", 0)
    aq = row_dict.get("AQ", 0) / 100
    pq = row_dict.get("PQ", 0)

    # Ausnahme Ramsch
    if spielart == "Ramsch":
        gq = norm_value(row_dict.get("GQ", 0), stats["GQ"]["avg"], stats["GQ"]["std"])
        pq = norm_value(row_dict.get("PQ", 0), stats["PQ"]["avg"], stats["PQ"]["std"])
        score = pq * 4 + gq * 6

    else:
        # 1. Abschneiden in der Statistik
        pq_norm = norm_value(pq, stats["PQ"]["avg"], stats["PQ"]["std"])
        gq_aktiv_norm = norm_value(gq_aktiv, stats["GQ als SpielerIn"]["avg"], stats["GQ als SpielerIn"]["std"])
        gq_passiv_norm = norm_value(gq_passiv, stats["GQ als NichtspielerIn"]["avg"], stats["GQ als NichtspielerIn"]["std"])

        # 2. Mut-Faktor (Ansagequote) mit neuem Erwartungswert (25%)
        aq_ziel = 0.25
        aq_faktor = min(1.0, aq / aq_ziel) if aq > 0 else 0.0

        # 3. Gesamt-Score nach Gewichtung zusammenrechnen
        # 40% Aktiv-Quote + 30% Passiv-Quote + 20% Punkte-Schnitt + 10% Mut-Faktor
        score = (gq_aktiv_norm * 2) + (gq_passiv_norm * 2) + (pq_norm * 5) + (aq_faktor * 1)

    return round(score, 1)

def analyse_display_playerstats(df, name_id, MinSpiele, Punkteberechnung, OhneKlopfen):
    stats = {}
    name = st.session_state.id_to_username[name_id]
    spielarten = ["Ruf", "Trumpfsolo", "Wenz + Geier", "Ramsch", "Bettel"]
    # --- In deinem Hauptskript / Schleife ---
    rows = {}
    for s in spielarten:
        if s == "Wenz + Geier":
            df_f = filter_spiele(df, [name_id], None,["Wenz", "Geier"], None)

        else:
            df_f = filter_spiele(df, [name_id], None, [s], None)

        player_stat = analyze_single_player(name_id, df_f, MinSpiele)

        if player_stat is not None:
            stats[name] = player_stat
            # Zeilen-Daten generieren und mit der Spielart als Key speichern
            rows[s] = get_player_stats_row(player_stat, Punkteberechnung, OhneKlopfen)
            rows[s]["Score"]= calculate_performance_score(rows[s], s, Punkteberechnung, OhneKlopfen)

    if rows:
        # Erstellt eine wunderschöne Gesamttabelle
        overview_df = pd.DataFrame.from_dict(rows, orient="index")
        overview_df.index.name = "Spielart"

        st.subheader(f"Statistik für {name}")

        # Streamlit Styling-Konfiguration für grandiose Optik
        st.dataframe(
            overview_df,
            use_container_width=True,
            column_config={
                "Spiele": st.column_config.NumberColumn("Spiele Gesamt", format="%d"),
                "PQ": st.column_config.NumberColumn("PQ", format="%.2f"),
                # Oder Punkte, je nach System
                "GQ": st.column_config.NumberColumn("GQ", format="%.0f %%", min_value=0.0,
                                                               max_value=100.0),
                "AQ": st.column_config.NumberColumn("AQ", format="%.0f %%", min_value=0.0,
                                                               max_value=100.0),
                "GQ als SpielerIn": st.column_config.NumberColumn("GQ als SpielerIn", format="%.0f %%", min_value=0.0,
                                                                  max_value=100.0),
                "PQ als SpielerIn": st.column_config.NumberColumn("PQ als SpielerIn"),
                "GQ als NichtspielerIn": st.column_config.NumberColumn("GQ als NichtspielerIn", format="%.0f %%", min_value=0.0,
                                                                     max_value=100.0),
                "Score": st.column_config.NumberColumn("Score", format="%.1f", min_value=0.0,
                                                                     max_value=100.0),
            }
        )
    else:
        st.info(f"Für {name} wurden mit den aktuellen Filtern (Mindestspiele: {MinSpiele}) keine Daten gefunden.")
    return rows



















def group_in_usernames():
    """Baut das DYNA_GRUPPEN Dict direkt aus dem Session State."""
    groups_res = supabase.table("groups").select("groupname, members").execute()

    DYNA_GRUPPEN = {}
    for g in groups_res.data:
        g_name = g["groupname"]
        member_ids = g.get("members", [])

        # Namen direkt aus dem zentralen Session State ziehen
        member_names = [
            st.session_state.id_to_username[m_id]
            for m_id in member_ids
            if m_id in st.session_state.id_to_username
        ]
        DYNA_GRUPPEN[g_name] = member_names
    return DYNA_GRUPPEN


def backup_df_to_supabase(df, filename="spiele_backup.csv"):
    """Lädt das DataFrame als CSV-Backup in den Supabase Storage (unverändert)."""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode('utf-8')

    response = supabase.storage.from_('all_games').upload(
        path=filename,
        file=csv_bytes,
        file_options={"content-type": "text/csv", "x-upsert": "true"}
    )
    return response


def load_df_from_supabase_backup(filename="spiele_backup.csv"):
    """Lädt das CSV-Backup aus dem Supabase Storage und gibt es als DataFrame zurück."""
    try:
        # 1. Datei als Bytes aus dem Supabase Storage herunterladen
        file_bytes = supabase.storage.from_('all_games').download(filename)

        # 2. Bytes in einen Stream umwandeln, den Pandas lesen kann
        csv_buffer = io.BytesIO(file_bytes)

        # 3. Als DataFrame einlesen
        df = pd.read_csv(csv_buffer)

        print(f"✅ Backup '{filename}' erfolgreich aus Supabase geladen! ({len(df)} Zeilen)")
        return df

    except Exception as e:
        print(f"❌ Fehler beim Laden des Backups aus Supabase: {e}")
        return None


def process_supabase_rounds(supabase_rows):
    """Verarbeitet die Supabase-Runden. Nutzt die Mapping-Dicts aus dem st.session_state."""
    if not supabase_rows:
        return pd.DataFrame()
    print(10*"\n")

    # Lokale Referenz auf das globale Mapping für schnelleren Zugriff
    id_to_name = st.session_state.id_to_username

    # Sortieren nach Erstellungszeitpunkt
    supabase_rows.sort(key=lambda x: x["created_at"])

    all_games = []
    seen_game_timestamps = set()

    for row in supabase_rows:
        data = row.get("data", {})
        runden_ts = row.get("created_at")
        games_list = data.get("spiele", [])

        # --- SCHRITT 1: Übersetzungs-Hilfe für diese Runde bauen ---
        mitspieler_raw = data.get("spieler", [])  # [["Name_Alt", "ID"], ...]

        # Ein kleines Wörterbuch, um von JEDEM bekannten Namen (alt oder neu) zur ID zu kommen
        name_zu_id = {}
        for s in mitspieler_raw:
            if isinstance(s, list) and len(s) >= 2:
                alt_name, uid = s[0], s[1]
                aktueller_name = id_to_name.get(uid, alt_name)

                name_zu_id[alt_name] = uid
                name_zu_id[aktueller_name] = uid

        # --- SCHRITT 2: Durch die Spiele gehen ---
        for game in games_list:
            game_ts = game.get("Zeitstempel", runden_ts)
            while game_ts in seen_game_timestamps:
                game_ts = str(game_ts) + "A"
            game["Zeitstempel"] = game_ts
            seen_game_timestamps.add(game_ts)

            # Wer hat an DIESEM Spiel tatsächlich teilgenommen? (Garantiert immer 4)
            tatsaechliche_mitspieler = game.get("Mitspieler_Runde", [])

            # Sicherheitsnetz: Falls es als String-Text in der DB lag, parsen
            if isinstance(tatsaechliche_mitspieler, str):
                try:
                    tatsaechliche_mitspieler = ast.literal_eval(tatsaechliche_mitspieler)
                except:
                    tatsaechliche_mitspieler = []

            # Jetzt filtern wir IDs und aktuelle Namen für genau diese 4 Spieler
            spiel_ids = []
            spiel_namen_aktuell = []

            for name in tatsaechliche_mitspieler:
                spiel_ids.append(name[1])
                spiel_namen_aktuell.append(name[0])
            # Spieldaten mit den exakten 4 Spielern aktualisieren
            game.update({
                "tournament": data.get("tournament"),
                "groupname": data.get("groupname"),
                "runden_timestamp": data.get("runden_timestamp", runden_ts),
                "start_info": data.get("start_info", ""),
                "Mitspieler_Runde": spiel_namen_aktuell,  # Nur die aktuellen 4 Namen!
                "MitspielerRundeIds": spiel_ids  # Nur die aktuellen 4 IDs!
            })

            # --- Spielmacher Zuordnung ---
            sm_raw = game.get("Spielmacher")
            if isinstance(sm_raw, list) and len(sm_raw) == 2:
                uid = sm_raw[1]
                game["SpielmacherId"] = uid
                game["Spielmacher"] = id_to_name.get(uid, sm_raw[0])
            else:
                game["SpielmacherId"] = None

            # --- Rufpartner Zuordnung ---
            rp_raw = game.get("Rufpartner")
            if isinstance(rp_raw, list) and len(rp_raw) == 2:
                uid = rp_raw[1]
                game["RufpartnerId"] = uid
                game["Rufpartner"] = id_to_name.get(uid, rp_raw[0])
            else:
                game["RufpartnerId"] = None

            all_games.append(game)

    final_df = pd.DataFrame(all_games)

    if not final_df.empty:
        if "Spielnummer" in final_df.columns:
            final_df.drop(columns=["Spielnummer"], inplace=True)
        final_df.insert(0, "Spielnummer", range(1, len(final_df) + 1))

    return final_df


def backup_process_data():
    """Holt die frischen Daten aus der DB, transformiert sie und überschreibt das Backup."""

    response = supabase.table("rounds").select("*").execute()
    final_df = process_supabase_rounds(response.data)

    # Sichert die fertig verarbeiteten Daten im Storage
    backup_df_to_supabase(final_df, filename="spiele_backup.csv")
    print("🔄 Backend: Daten verarbeitet, Backup aktualisiert und Cache geleert.")






