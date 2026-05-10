# --- Konfiguration ---
SPIELWERTE = {"Ruf": 1, "Ramsch": 1, "Trumpfsolo": 5, "Wenz": 5, "Geier": 5, "Bettel": 5, "Durchmarsch": 5}
SPIELWERTE_AUX = {"Ruf": 1, "Ramsch": 1, "Trumpfsolo": 5, "Wenz": 5, "Durchmarsch": 5}
SPIELWERTE_AllR = {"Ruf": 1, "Trumpfsolo": 5, "Wenz": 5, "Bettel": 5}

# = Spielarten, Klopfen, Tout, Punkteart
Standard = [SPIELWERTE, True, True, True, "normal"]
Wue = [SPIELWERTE, True, True, True, "wue"]
Aux = [SPIELWERTE_AUX, False, False, False, "normal"]
AllR = [SPIELWERTE_AllR, False, False, False, "normal"]
