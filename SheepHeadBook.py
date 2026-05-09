from huggingface_hub import HfApi
import streamlit as st
import pandas as pd
from datetime import datetime
from collections import defaultdict
import json
import os
import requests




# Modus Augschburg
# --- Hilfsfunktionen ---
def spielwert_bestimmen_normal(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, SPIELWERTE):
    basis = SPIELWERTE.get(spielart, 1) 
    bonus = 0 + jungfrau
    if tout:
        basis += 1 
    if kontra: 
        bonus += 1
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1 
    wertn = (basis + laufende) * (2 ** bonus) * (2 ** klopfer)
    wertn_NK = (basis + laufende) * (2 ** bonus)
    return wertn, wertn_NK

def spielwert_bestimmen_wue(spielart, klopfer, laufende, tout, jungfrau, schneider, schwarz, kontra, gewonnen, SPIELWERTE):
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
    if schneider or schwarz:
        basis += 1 
    if schwarz:
        basis += 1  
    wert_wue = (basis+jungfrau) * (1 + kontrazahl + klopfer) + laufende
    wertn_wue_NK = (basis+jungfrau) * (1 + kontrazahl) + laufende
    return wert_wue, wertn_wue_NK


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




