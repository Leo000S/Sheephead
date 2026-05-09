# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  9 16:22:47 2025

@author: leopoldschaller
"""

import os
from pathlib import Path

import requests

import os


folder_dir = "/Users/leopoldschaller/Desktop/Sheephead/old_data"

def list_all_json_files(API_URL):
    """
    Durchsucht rekursiv einen API-Ordner und gibt
    eine Liste aller .json-Dateipfade zurück.
    """
    r = requests.get(API_URL)
    r.raise_for_status()
    data = r.json()

    json_files = []

    for item in data:
        if item["type"] == "file" and item["path"].endswith(".json"):
            json_files.append(item["path"])

        elif item["type"] == "directory":
            subfolder_url = f"{API_URL}/{item['path'].split('/')[-1]}"
            json_files.extend(list_all_json_files(subfolder_url))


    return json_files

def download_file(path, target_base):
    raw_url = f"https://huggingface.co/datasets/LeoDerLoewe/SchafkopfDataAutosave/resolve/main/{path}"

    target = Path(target_base) / Path(path).name
    target.parent.mkdir(parents=True, exist_ok=True)

    print(f"✔ Lade {raw_url}")
    r = requests.get(raw_url)
    r.raise_for_status()

    target.write_bytes(r.content)
    print(f"✔ Gespeichert nach: {target} \n")

def download_entire_folder(target_dir, API_URL):
    # Ordnerinhalt löschen
    if os.path.exists(target_dir):
        print(f"Lösche alten Inhalt von {target_dir} ...")
        for f in os.listdir(target_dir):
            path = os.path.join(target_dir, f)
            if os.path.isfile(path):
                os.remove(path)  # Datei löschen
            elif os.path.isdir(path):
                try:
                    os.rmdir(path)  # Nur leere Ordner löschen
                except OSError:
                    print(f"Ordner {path} nicht leer, bitte manuell löschen.")
    else:
        os.makedirs(target_dir, exist_ok=True)

    # Download starten
    print("Hole Dateiliste aus Dataset...\n")
    files = list_all_json_files(API_URL)
    print(f"Gefundene Dateien: {len(files)}\n")

    for file in files:
        download_file(file, target_dir)

    print("\n✔ Ordner vollständig heruntergeladen.")

# Woher herunterladen?
API_URL = "https://huggingface.co/api/datasets/LeoDerLoewe/SchafkopfDataAutosave/tree/main/AllContributingRounds"

# Rphdaten wohin?
csv_dir = os.path.join(folder_dir, "raw_data")

if __name__ == "__main__":
    download_entire_folder(csv_dir, API_URL)

#############################################################################################
# Davor muss jede Person online eingeloggt sein, einen benutzernamen und einen user_id haben...



# für jeder json Datei in os.path.join(folder_dir, "raw_data") soll folgendes passieren:

# 1. dict "data" wird erstellt, indem die jeweiligen dateien bei den keys "Spieler" (list) und je Spiel "Spielmacher", "Rufpartner" und "Mitspieler_Runde" (list) verändert werden.
# Dabei soll jedem Spieler zusätzlich seine user_id zugewießen werden, also von "Leo" zu ["Leos Benutzername", "ajnciherlisduivhkjsjdfzbfv"].
# Der key "User" soll nur mit der user_id des dort stehenden Namens überschrieben werden. Die Werte AlterName, NeuerName und User_id werden als input in einem dict gegeben.
# Das ganze soll dann als data in die column "data" der supabase tabelle geschrieben werden.

# 2. aus dem dateinamen soll mit dem key "runden_timestamp" der wert "created_at" in die supabase table geschrieben werden. Wenn es mehrere gibt, sollen diese unterschiedlich gemacht werden.

# 3. in "user_id" der supabase table soll folgender wert geschrieben werden: "..."
