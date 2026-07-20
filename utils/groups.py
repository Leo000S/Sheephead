import streamlit as st
from datetime import timedelta, timezone
import json

from services.supabase_client import supabase, log_event
from SpieleAuswahl import SPIELWERTE
Standard = [SPIELWERTE, True, True, True, "normal"]

def ist_admin_oder_boss(group_data, user_id):
    admins = group_data.get("admins") or []
    return user_id == group_data["boss"] or user_id in admins

def update_group_alle():
    try:
        alle_spieler_ids = st.session_state.user_ids
        supabase.table("groups") \
            .update({"members": alle_spieler_ids}) \
            .eq("groupname", "Alle") \
            .execute()

    except Exception as e:
        print(f"Fehler beim Synchronisieren der 'Alle'-Gruppe: {e}")


def group_menu(user):
    st.header("Gruppen- & Rechteverwaltung")

    all_p_data = supabase.table("profiles").select("user_id, username").execute().data
    all_p = {p["user_id"]: p["username"] for p in all_p_data}

    t1, t2, t3 = st.tabs([" Gruppe gründen", "Verwalten & Einladen", "Einladungen & Beitritte"])

    # =====================================================================
    # TAB 1: GRUPPE GRÜNDEN
    # =====================================================================
    with t1:
        with st.form("new_group"):
            g_name = st.text_input("Name der Schafkopf-Runde")
            if st.form_submit_button("Gründen") and g_name:
                if supabase.table("groups").select("groupname").eq("groupname", g_name).execute().data:
                    st.error("Gruppenname existiert bereits.")
                else:
                    supabase.table("groups").insert({
                        "groupname": g_name,
                        "boss": user.id,
                        "admins": [],
                        "members": [user.id]
                    }).execute()
                    st.success(f"Gruppe '{g_name}' erfolgreich gegründet!")
                    log_event(
                        level="INFO",
                        message=f"New group {g_name} founded by {st.session_state.current_username}",
                        details={"name": g_name, "boss": user.id}
                    )
                    st.rerun()

    # =====================================================================
    # TAB 2: VERWALTEN & EINLADEN (Aus Sicht von Boss & Admins)
    # =====================================================================
    with t2:
        alle_gruppen = supabase.table("groups").select("*").execute().data
        meine_verwalteten_gruppen = [g for g in alle_gruppen if ist_admin_oder_boss(g, user.id)]

        if not meine_verwalteten_gruppen:
            st.info("Du bist aktuell weder Admin noch GründerIn einer Gruppe.")
        else:
            sel_g = st.selectbox("Gruppe zum Verwalten wählen", [g["groupname"] for g in meine_verwalteten_gruppen])
            g_data = next(g for g in meine_verwalteten_gruppen if g["groupname"] == sel_g)

            ist_mein_boss = (user.id == g_data["boss"])
            aktuelle_mitglieder = g_data.get("members") or []
            aktuelle_admins = g_data.get("admins") or []

            with st.expander("Beitritte"):
                anfragen = supabase.table("group_requests") \
                    .select("*") \
                    .eq("groupname", sel_g) \
                    .eq("type", "request") \
                    .eq("status", "pending") \
                    .execute().data

                if not anfragen:
                    st.write("Keine offenen Anfragen vorhanden")
                else:
                    for req in anfragen:
                        from datetime import datetime
                        erstellt_am = datetime.fromisoformat(req["created_at"].replace("Z", "+00:00"))
                        tage_alt = (datetime.now(timezone.utc) - erstellt_am).days
                        antragsteller_id = req["user_id"]
                        antragsteller_name = all_p.get(antragsteller_id, "Unbekannt")

                        if tage_alt >= 10:
                            if antragsteller_id not in aktuelle_mitglieder:
                                neue_m_liste = aktuelle_mitglieder + [antragsteller_id]
                                supabase.table("groups").update({"members": neue_m_liste}).eq("groupname", sel_g).execute()
                            supabase.table("group_requests").update({"status": "accepted"}).eq("id", req["id"]).execute()
                            st.toast(f"10 Tage abgelaufen: {antragsteller_name} wurde automatisch aufgenommen!")
                            st.rerun()

                        c1, c2, c3 = st.columns([2, 1, 1])
                        c1.write(f"**{antragsteller_name}** *(Anfrage vor {tage_alt} Tagen)*")

                        if c2.button("Annehmen ✅", key=f"acc_{req['id']}"):
                            if antragsteller_id not in aktuelle_mitglieder:
                                supabase.table("groups").update({"members": aktuelle_mitglieder + [antragsteller_id]}).eq(
                                    "groupname", sel_g).execute()
                            supabase.table("group_requests").update({"status": "accepted"}).eq("id", req["id"]).execute()
                            st.rerun()

                        if c3.button("Ablehnen ❌", key=f"rej_{req['id']}"):
                            supabase.table("group_requests").update({"status": "rejected"}).eq("id", req["id"]).execute()
                            st.rerun()

            # --- MITGLIEDERLISTE & ROLLENVERGABE ---
            with st.expander(f"Mitglieder ({len(aktuelle_mitglieder)})"):
                for m_id in aktuelle_mitglieder:
                    rolle = ""
                    if m_id == g_data["boss"]:
                        rolle = " 👑 (Gründer)"
                    elif m_id in aktuelle_admins:
                        rolle = " 🛡️ (Admin)"

                    name_anzeige = f"{all_p.get(m_id, 'Unbekannt')}{rolle}"

                    # Eigener Name bekommt einen Hinweis
                    if m_id == user.id:
                        name_anzeige += " (Du)"

                    with st.expander(name_anzeige):
                        if ist_mein_boss and m_id != user.id:
                            btn_c1, btn_c2 = st.columns(2)

                            if m_id in aktuelle_admins:
                                if btn_c1.button("Admin entziehen ⬇️", key=f"dem_{m_id}", use_container_width=True):
                                    neue_ads = [a for a in aktuelle_admins if a != m_id]
                                    supabase.table("groups").update({"admins": neue_ads}).eq("groupname", sel_g).execute()
                                    st.rerun()
                            else:
                                if btn_c1.button("Befördern 🛡️", key=f"prom_{m_id}", use_container_width=True):
                                    neue_ads = aktuelle_admins + [m_id]
                                    supabase.table("groups").update({"admins": neue_ads}).eq("groupname", sel_g).execute()
                                    st.rerun()

                            if btn_c2.button("Entfernen ❌", key=f"kick_{m_id}", use_container_width=True):
                                neue_m = [m for m in aktuelle_mitglieder if m != m_id]
                                neue_a = [a for a in aktuelle_admins if a != m_id]
                                supabase.table("groups").update({"members": neue_m, "admins": neue_a}).eq("groupname",
                                                                                                          sel_g).execute()
                                st.rerun()

                        elif m_id != user.id:
                            st.caption("Keine Rechte für Aktionen")
                        else:
                            st.caption("Das bist du selbst.")

            with st.expander("SpielerIn in die Runde einladen"):
                bereits_aktiv = supabase.table("group_requests").select("user_id").eq("groupname", sel_g).eq("status",
                                                                                                             "pending").execute().data
                blockierte_ids = aktuelle_mitglieder + [b["user_id"] for b in bereits_aktiv]

                verfuegbare_user = {uname: uid for uid, uname in all_p.items() if uid not in blockierte_ids}

                if not verfuegbare_user:
                    st.write("Alle registrierten SpielerInnen sind bereits versorgt.")
                else:
                    zu_einladen = st.selectbox("SpielerIn wählen", ["-- bitte wählen --"] + list(verfuegbare_user.keys()))
                    if st.button("Einladung abschicken") and zu_einladen != "-- bitte wählen --":
                        ziel_id = verfuegbare_user[zu_einladen]
                        supabase.table("group_requests").insert({
                            "groupname": sel_g,
                            "user_id": ziel_id,
                            "type": "invite",
                            "status": "pending"
                        }).execute()
                        st.success(f"Einladung an {zu_einladen} wurde übermittelt!")
                        st.rerun()

                if st.session_state.current_username == "Leo Schaller":
                    st.write("Du bist Admin, du kannst auch einfach so Mitglieder hinzufügen!!!")
                    blockierte_ids = aktuelle_mitglieder
                    verfuegbare_user = {uname: uid for uid, uname in all_p.items() if uid not in blockierte_ids}

                    ausgewaehlter_name = st.selectbox(
                        "SpielerIn wählen",
                        ["-- bitte wählen --"] + list(verfuegbare_user.keys()), key=f"selectbox_add_member_{sel_g}_admin")

                    if st.button("SpielerIn verbindlich hinzufügen"):
                        if ausgewaehlter_name != "-- bitte wählen --":

                            neue_user_id = verfuegbare_user[ausgewaehlter_name]
                            neue_mitglieder_liste = aktuelle_mitglieder + [neue_user_id]
                            supabase.table("groups").update({"members": neue_mitglieder_liste}).eq("groupname",
                                                                                                   sel_g).execute()
                            st.success(f"{ausgewaehlter_name} wurde erfolgreich hinzugefügt!")
                            st.rerun()
                        else:
                            st.warning("Bitte wähle zuerst eine gültige SpielerIn aus!")

                if  ist_admin_oder_boss:
                    st.write("Du bist Admin, du kannst auch einfach so Mitglieder hinzufügen!!!")
                    blockierte_ids = aktuelle_mitglieder
                    verfuegbare_user = {uname: uid for uid, uname in all_p.items() if uid not in blockierte_ids}

                    ausgewaehlter_name = st.selectbox(
                        "SpielerIn wählen",
                        ["-- bitte wählen --"] + list(verfuegbare_user.keys()), key=f"selectbox_add_member_{sel_g}_admin")

                    if st.button("SpielerIn verbindlich hinzufügen"):
                        if ausgewaehlter_name != "-- bitte wählen --":

                            neue_user_id = verfuegbare_user[ausgewaehlter_name]
                            neue_mitglieder_liste = aktuelle_mitglieder + [neue_user_id]
                            supabase.table("groups").update({"members": neue_mitglieder_liste}).eq("groupname",
                                                                                                   sel_g).execute()
                            st.success(f"{ausgewaehlter_name} wurde erfolgreich hinzugefügt!")
                            st.rerun()
                        else:
                            st.warning("Bitte wähle zuerst eine gültige SpielerIn aus!")

            # =====================================================================
            # TAB 2.1 : Spieleinstellungen & Turniere (Komplett & Schlank)
            # =====================================================================
            from datetime import datetime
            with st.expander("Spieleinstellungen & Turniere"):
                st.divider()

                bisherige_raw = g_data.get("tournaments") or []
                if isinstance(bisherige_raw, str):
                    bisherige_raw = [bisherige_raw] if bisherige_raw else []

                bestehende_turniere = []
                for t_raw in bisherige_raw:
                    try:
                        bestehende_turniere.append(json.loads(t_raw))
                    except:
                        pass

                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Turnier-Verwaltung**")
                    turnier_optionen = ["🆕Neues Turnier erstellen🆕"] + [t["name"] for t in bestehende_turniere]
                    ausgewaehltes_turnier_name = st.selectbox("Turnier auswählen", options=turnier_optionen,
                                                              key=f"sel_tourney_{sel_g}")
                    default_name, bearbeitungs_modus, altes_t = "", False, None
                    default_start, default_end = datetime.now().date(), datetime.now().date() + timedelta(days=14)

                    if ausgewaehltes_turnier_name != "🆕Neues Turnier erstellen🆕":
                        bearbeitungs_modus = True
                        altes_t = next(t for t in bestehende_turniere if t["name"] == ausgewaehltes_turnier_name)
                        default_name = altes_t["name"]
                        try:
                            start_str, end_str = altes_t["zeitraum"].split("_")
                            default_start = datetime.strptime(start_str, "%Y%m%d").date()
                            default_end = datetime.strptime(end_str, "%Y%m%d").date()
                        except:
                            pass

                    t_name = st.text_input("Turnier-Name", value=default_name, disabled=bearbeitungs_modus,
                                           key=f"t_name_{sel_g}")
                    t_zeitraum = st.date_input("Turnier-Zeitraum", value=(default_start, default_end),
                                               key=f"t_date_{sel_g}")

                    if ausgewaehltes_turnier_name != "🆕Neues Turnier erstellen🆕":
                        t_name = ausgewaehltes_turnier_name

                with col2:
                    st.write("**Regelwerk & Einschränkungen**")
                    # Spezifische Restrictions holen oder auf Standard zurückgreifen
                    aktuelle_restr = altes_t.get("restrictions", Standard) if bearbeitungs_modus and altes_t else Standard
                    akt_spielwerte, akt_klopfen, akt_tout, akt_sie, akt_punkteart = aktuelle_restr

                    st.write("Erlaubte Spielarten:")
                    neue_spielwerte = {}
                    for spiel, wert in SPIELWERTE.items():
                        if st.checkbox(spiel, value=(spiel in akt_spielwerte), key=f"chk_{spiel}_{sel_g}"):
                            neue_spielwerte[spiel] = wert

                    st.divider()
                    neues_klopfen = st.checkbox("Klopfen erlaubt", value=akt_klopfen, key=f"klopfen_{sel_g}")
                    neues_tout = st.checkbox("Tout erlaubt", value=akt_tout, key=f"tout_{sel_g}")
                    neues_sie = st.checkbox("Sie erlaubt", value=akt_sie, key=f"sie_{sel_g}")
                    neue_punkteart = st.selectbox(
                        "Punkteart", ["normal", "wue"],
                        index=["normal", "wue"].index(akt_punkteart) if akt_punkteart in ["normal", "wue"] else 0,
                        key=f"punkte_{sel_g}"
                    )

                    start_tag, end_tag = "", ""
                    ist_zeitraum_valide = isinstance(t_zeitraum, tuple) and len(t_zeitraum) == 2

                    if ist_zeitraum_valide:
                        start_tag = t_zeitraum[0].strftime("%Y%m%d")
                        end_tag = t_zeitraum[1].strftime("%Y%m%d")

                        with col1:
                            if start_tag <= datetime.now().strftime("%Y%m%d") <= end_tag:
                                st.success(f"🟢'{t_name if t_name else 'Neues Turnier'}' läuft aktuell!")
                            else:
                                st.error(f"🔴'{t_name if t_name else 'Neues Turnier'}' ist aktuell inaktiv/abgelaufen.")

                    st.divider()
                    btn_col1, btn_col2 = st.columns([3, 1])

                    with btn_col1:
                        if st.button("Einstellungen & Turnier speichern", type="primary", use_container_width=True,
                                     key=f"save_{sel_g}"):

                            existierende_namen = [t["name"] for t in bestehende_turniere]

                            if not t_name.strip():
                                st.error("Bitte gib zuerst einen Turnier-Namen ein!")

                            elif not bearbeitungs_modus and t_name.strip() in existierende_namen:
                                st.error(
                                    f"🚫Turniername existiert bereits! Bitte wähle einen anderen Namen.")

                            elif not ist_zeitraum_valide:
                                st.error("Bitte wähle einen gültigen Zeitraum aus!")
                            else:
                                turnier_objekt = {
                                    "name": t_name.strip(),
                                    "zeitraum": f"{start_tag}_{end_tag}",
                                    "groupname": sel_g,
                                    "restrictions": [neue_spielwerte, neues_klopfen, neues_tout, neues_sie, neue_punkteart]
                                }
                                try:
                                    neue_liste_raw = [r for r in bisherige_raw if json.loads(r).get(
                                        "name") != ausgewaehltes_turnier_name] if bearbeitungs_modus else bisherige_raw.copy()
                                    neue_liste_raw.append(json.dumps(turnier_objekt))

                                    supabase.table("groups").update({"tournaments": neue_liste_raw}).eq("groupname",
                                                                                                        sel_g).execute()
                                    st.success("Erfolgreich gespeichert!")

                                    log_event(
                                        level="INFO",
                                        message=f"{t_name.strip()} founded/updated by {st.session_state.current_username}",
                                        details={"user": st.session_state.current_username, "group": sel_g, "tournament": t_name.strip()},
                                    )

                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler beim Speichern: {e}")

                    with btn_col2:
                        if bearbeitungs_modus:
                            if st.button("🗑️ Löschen", type="secondary", use_container_width=True, key=f"delete_{sel_g}"):
                                try:
                                    neue_liste_raw = [r for r in bisherige_raw if
                                                      json.loads(r).get("name") != ausgewaehltes_turnier_name]
                                    supabase.table("groups").update({"tournaments": neue_liste_raw}).eq("groupname",
                                                                                                        sel_g).execute()
                                    st.success("Turnier gelöscht!")

                                    log_event(
                                        level="INFO",
                                        message=f"{t_name.strip()} deleted by {st.session_state.current_username}",
                                        details={"user": st.session_state.current_username, "group": sel_g,
                                                 "tournament": t_name.strip()},
                                    )

                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler beim Löschen: {e}")
                        else:
                            st.write("")

            if ist_mein_boss:
                st.divider()
                with st.expander("⚠️ Gruppe unwiderruflich auflösen ⚠️"):
                    st.warning(
                        f"Das Löschen von '{sel_g}' entfernt alle Verknüpfungen. Das kann nicht rückgängig gemacht werden.")
                    bestaetigung = st.text_input("Tippe 'LÖSCHEN' zur Bestätigung")
                    if st.button("Gruppe jetzt auflösen", type="primary") and bestaetigung == "LÖSCHEN":
                        supabase.table("group_requests").delete().eq("groupname", sel_g).execute()
                        supabase.table("groups").delete().eq("groupname", sel_g).execute()
                        st.success("Gruppe erfolgreich gelöscht.")

                        log_event(
                            level="INFO",
                            message=f"{sel_g} deleted by {st.session_state.current_username}",
                            details={"user": st.session_state.current_username, "group": sel_g},
                        )

                        st.rerun()

    # =====================================================================
    # TAB 3: BEITRETEN & EINLADUNGEN (Sicht des "normalen" Kartlers)
    # =====================================================================
    with t3:
        st.write("### Erhaltene Einladungen")
        meine_einladungen = supabase.table("group_requests") \
            .select("*") \
            .eq("user_id", user.id) \
            .eq("type", "invite") \
            .eq("status", "pending") \
            .execute().data

        if not meine_einladungen:
            st.write("_Du hast aktuell keine offenen Einladungen_")
        else:
            for einl in meine_einladungen:
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"Du wurdest in die Gruppe **{einl['groupname']}** eingeladen!")

                if c2.button("Annehmen ✅", key=f"acc_inv_{einl['id']}"):
                    g_ref = supabase.table("groups").select("members").eq("groupname", einl["groupname"]).execute().data[0]
                    m_neu = (g_ref.get("members") or []) + [user.id]

                    supabase.table("groups").update({"members": m_neu}).eq("groupname", einl["groupname"]).execute()
                    supabase.table("group_requests").update({"status": "accepted"}).eq("id", einl["id"]).execute()
                    st.success("Gruppe beigetreten!")
                    st.rerun()

                if c3.button("Ablehnen ❌", key=f"rej_inv_{einl['id']}"):
                    supabase.table("group_requests").update({"status": "rejected"}).eq("id", einl["id"]).execute()
                    st.rerun()

        st.divider()
        st.write("### Gruppe suchen & beitreten")

        meine_gruppen_namen = [g["groupname"] for g in alle_gruppen if user.id in (g.get("members") or [])]
        meine_offenen_anfragen = [r["groupname"] for r in
                                  supabase.table("group_requests").select("groupname").eq("user_id", user.id).eq("status",
                                                                                                                 "pending").execute().data]

        offene_marktplatz_gruppen = [g["groupname"] for g in alle_gruppen if
                                     g["groupname"] not in meine_gruppen_namen and g[
                                         "groupname"] not in meine_offenen_anfragen]

        if not offene_marktplatz_gruppen:
            st.write("_Du bist bereits in allen Gruppen Mitglied oder es laufen bereits Anfragen._")
        else:
            wunsch_gruppe = st.selectbox("Gruppe auswählen", ["-- wählen --"] + offene_marktplatz_gruppen)
            if st.button("Beitrittsanfrage stellen") and wunsch_gruppe != "-- wählen --":
                supabase.table("group_requests").insert({
                    "groupname": wunsch_gruppe,
                    "user_id": user.id,
                    "type": "request",
                    "status": "pending"
                }).execute()
                st.info(
                    "Anfrage gesendet! Wenn die Admins innerhalb der nächsten 10 Tage nicht ablehnen, bist du automatisch Mitglied.")
                st.rerun()