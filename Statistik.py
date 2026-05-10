import os
import streamlit as st
import json
import numpy as np
import re
import pandas as pd

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
                (x["Gewonnen"] == True and (player in [x["Spielmacher"], x["Rufpartner"]])) or
                (x["Gewonnen"] == False and player not in [x["Spielmacher"], x["Rufpartner"]])
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
    if (pd.isna(x["Rufpartner"]) or str(x["Rufpartner"]).strip() == "") and player == x["Spielmacher"]:
        punkte *= 3
        punkte_wue *= 3
        punkte_NK *= 3
        punkte_NK_wue *= 3
    
    return pd.Series([punkte, punkte_wue, punkte_NK, punkte_NK_wue])


# Erstellt die Datentabelle für alle Spieler einzeln, welche die Inhalte in der großen Tabelle definieren in run_statistic():
def analyse_all_players(df, all_players, MinSpiele):
    
    spieler_stats = {} 
       
    for player in all_players:
        # Spiele, bei denen der Spieler beteiligt war
        df_player = df[df["Mitspieler_Runde"].str.contains(player, regex=False, na=False)].copy()
        
        # Nichts zu tun, falls keine Spiele übrig sind
        if df_player.empty:
            continue 
        if len(df_player) < MinSpiele:
            continue
        
        # Sortieren nach Zeitstempel
        df_player.sort_values("Zeitstempel", inplace=True)
        df_player = punkte_abspeichern(df_player, player)
        
        # Basis-Statistiken
        spiele_len = len(df_player)
        gewonnene_spiele = df_player["Hat_gewonnen"].sum()
        quote = (gewonnene_spiele / spiele_len * 100) if spiele_len > 0 else 0

        # Nur die spiele als SpielerIn
        df_player_s = df_player[df_player["Spielmacher"].str.contains(player, regex=False, na=False)].copy()
        df_player_s = df_player_s[df_player_s["Spielart"] != "Ramsch"].copy()
        anzahl_spielmacher = len(df_player_s) 
        anteil_spielmacher = (anzahl_spielmacher / spiele_len * 100) if spiele_len > 0 else 0

        df_player_s = punkte_abspeichern(df_player_s, player) 

        # Ergebnisse speichern
        spieler_stats[player] = {
            "Spiele": df_player,
            "Anzahl_Spiele": spiele_len,
            "Gewonnene_Spiele": gewonnene_spiele,
            "Gewinnquote": round(quote, 1),
            "Anzahl_Spiele als SpielerIn": anzahl_spielmacher,
            "Ansagequote": round(anteil_spielmacher, 1),
            "Gewonnen als SpielerIn": df_player_s["Hat_gewonnen"].sum(),
            "Gewinnquote als Nicht-SpielerIn": round((df_player["Hat_gewonnen"].sum() - df_player_s["Hat_gewonnen"].sum())/(spiele_len - anzahl_spielmacher) * 100, 2),
            "Endpunktestand": df_player["Kumulativer Punktestand"].iloc[-1],
            "Endpunktestand_Wue": df_player["Kumulativer Punktestand_Wue"].iloc[-1],
            "Endpunktestand_NK": df_player["Kumulativer Punktestand_NK"].iloc[-1],
            "Endpunktestand_NK_Wue": df_player["Kumulativer Punktestand_NK_Wue"].iloc[-1],
            "sEndpunktestand": df_player_s["Kumulativer Punktestand"].iloc[-1],
            "sEndpunktestand_Wue": df_player_s["Kumulativer Punktestand_Wue"].iloc[-1],
            "sEndpunktestand_NK": df_player_s["Kumulativer Punktestand_NK"].iloc[-1],
            "sEndpunktestand_NK_Wue": df_player_s["Kumulativer Punktestand_NK_Wue"].iloc[-1]
                               if not df_player.empty else 0
        }
    
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


# Setzt die filter in run_statistic() um:
def filter_spiele(
    df: pd.DataFrame,
    namen=None,
    spielarten=None,
    tournament=None,
 ):
    df_f = df.copy()

    # --- Namen ---
    if namen:
        df_f = df_f[
            df_f["Mitspieler_Runde"].apply(
                lambda spieler: any(n in spieler for n in namen)
            )
        ]

    # --- Spielart ---
    if spielarten and "alle" not in spielarten:
        df_f = df_f[df_f["Spielart"].isin(spielarten)]

    # --- Tournament ---
    if tournament:
        df_f = df_f[df_f["tournament"].isin(tournament)]


    return df_f


