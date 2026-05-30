
import pandas as pd
from collections import defaultdict
from services.supabase_client import supabase
import streamlit as st
from datetime import datetime


# Modus Augschburg
# --- Hilfsfunktionen ---
def spielwert_bestimmen_normal(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, Re, SPIELWERTE):
    basis = SPIELWERTE.get(spielart, 1) 
    bonus = 0 + jungfrau
    if tout:
        basis += 1 
    if kontra: 
        bonus += 1
    if Re:
        bonus += 1
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1 
    wertn = (basis + laufende) * (2 ** bonus) * (2 ** klopfer)
    wertn_NK = (basis + laufende) * (2 ** bonus)
    return wertn, wertn_NK

def spielwert_bestimmen_wue(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, Re, gewonnen, SPIELWERTE):
    basis = SPIELWERTE.get(spielart, 1) 
    if basis == 5:
        basis = 3
    kontrazahl = 0
    if not gewonnen and spielart == "Ruf":
        basis += 1
    if tout:
        basis += 1 
    if kontra: 
        kontrazahl += 1
    if Re:
        kontrazahl += 1
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1  
    wert_wue = (basis+jungfrau) * (1 + kontrazahl + klopfer) + laufende
    wertn_wue_NK = (basis+jungfrau) * (1 + kontrazahl) + laufende
    return wert_wue, wertn_wue_NK

# Berechnung der Statistik, welche im book angezeigt wird...
def berechne_statistik(spieler, spiele):
    konto_normal = defaultdict(int)
    konto_wue = defaultdict(int)
    statistik = defaultdict(lambda: {"Spiele": 0, "Gespielt": 0, "Gewonnen": 0, "Verloren": 0})

    for spiel in spiele:
        faktor = spiel.get("Verteilungsfaktor", 1)
        sa = spiel["Spielart"]
        sm = spiel["Spielmacher"][0]
        rp = spiel["Rufpartner"][0]
        wertn = spiel["Wert"]
        wertw = spiel["Wert_Wue"]
        gewonnen = spiel["Gewonnen"]
        spielende = set([s[0] for s in spiel["Mitspieler_Runde"]])
        team = {sm}
        if rp:
            team.add(rp)
        gegner = spielende - team

        # Statistikzähler
        for s in spielende:
            statistik[s]["Spiele"] += 1
        for s in team:
            if sa != "Ramsch":
                statistik[s]["Gespielt"] += 1

        # Punkteverteilung
        if gewonnen:
            for s in team:
                konto_normal[s] += wertn * len(gegner) * faktor
                konto_wue[s] += wertw * len(gegner) * faktor
                statistik[s]["Gewonnen"] += 1
            for g in gegner:
                konto_normal[g] -= wertn * len(team) * faktor
                konto_wue[g] -= wertw * len(team) * faktor
                statistik[g]["Verloren"] += 1
        if not gewonnen:
            for s in team:
                konto_normal[s] -= wertn * len(gegner) * faktor
                konto_wue[s] -= wertw * len(gegner) * faktor
                statistik[s]["Verloren"] += 1
            for g in gegner:
                konto_normal[g] += wertn * len(team) * faktor
                konto_wue[g] += wertw * len(team) * faktor
                statistik[g]["Gewonnen"] += 1

    df = pd.DataFrame([
        {
            "Spieler": s,
            "Runden": statistik[s]["Spiele"],
            "Gespielt": statistik[s]["Gespielt"],
            "Gewonnen": statistik[s]["Gewonnen"],
            "Verloren": statistik[s]["Verloren"],
            "Punkte": konto_normal[s],
            "Punkte_Wue": konto_wue[s]
        }
        for s in spieler
    ])

    return df

def load_open_rounds():
    heute = datetime.now().date().isoformat()

    # Query mit Filter auf User ID und Datum
    response = (
        supabase
        .table("rounds")
        .select("*")
        .eq("user_id", st.session_state.current_user_id)          # Nur Runden des aktuellen Users
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
    data = {
        "runden_timestamp": st.session_state.runden_timestamp,
        "tournament": st.session_state.tournament_name,
        "groupname": st.session_state.groupname,
        "User": st.session_state.current_user_id,
        "start_info": st.session_state.start_info,
        "ende_info": st.session_state.ende,
        "spieler": st.session_state.spieler,
        "spiele": st.session_state.spiele
    }
    try:
        supabase.table("rounds").insert({
            "user_id": st.session_state.current_user_id,
            "created_at": st.session_state.runden_timestamp,
            "data": data
        }).execute()

        st.success("Runde erfolgreich aktualisiert!")
    except Exception as e:
        st.error(f"Fehler beim Update: {e}")


def update_round(st):
    # Das Daten-Objekt für die Spalte "data"
    data = {
        "runden_timestamp": st.session_state.runden_timestamp,
        "tournament": st.session_state.tournament_name,
        "groupname" : st.session_state.groupname,
        "User": st.session_state.current_user_id,
        "start_info": st.session_state.start_info,
        "ende_info": st.session_state.ende,
        "spieler": st.session_state.spieler,
        "spiele": st.session_state.spiele
    }

    try:
        supabase.table("rounds").update({
            "data": data  # Wir updaten primär das JSON-Feld
        }).eq("user_id", st.session_state.current_user_id) \
            .eq("created_at", st.session_state.runden_timestamp) \
            .execute()

        st.success("Runde erfolgreich aktualisiert!")
    except Exception as e:
        st.error(f"Fehler beim Update: {e}")









