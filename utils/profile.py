
import streamlit as st
from services.supabase_client import supabase, log_event

def profile_menu(user):
    st.title("Profil & Gruppen")

    # --- PROFIL LADEN / INITIALISIEREN ---
    res = supabase.table("profiles").select("*").eq("user_id", user.id).execute()
    profile = res.data[0] if res.data else None

    if not profile:
        profile = {"user_id": user.id, "username": user.email.split("@")[0], "first_name": "", "last_name": ""}
        supabase.table("profiles").insert(profile).execute()

    # --- 1. PROFIL-DATEN ---
    with st.expander("Profildaten bearbeiten", expanded=True):
        with st.form("profile_form"):
            fn = st.text_input("Vorname", value=profile.get("first_name", ""))
            ln = st.text_input("Nachname", value=profile.get("last_name", ""))
            un = st.text_input("Benutzername", value=profile.get("username", ""))
            if st.form_submit_button("Speichern"):
                # Check ob Username vergeben (außer eigener)
                check = supabase.table("profiles").select("user_id").eq("username", un).execute()
                if any(r["user_id"] != user.id for r in check.data):
                    st.error("Benutzername vergeben.")
                else:
                    supabase.table("profiles").update({"first_name": fn, "last_name": ln, "username": un}).eq("user_id",
                                                                                                              user.id).execute()
                    st.success("Gespeichert!");
                    log_event(
                        level="INFO",
                        message=f"Profile of {un} succesfully changed",
                        details={"username": un, "first_name": fn, "last_name": ln }
                    )
                    st.rerun()

    # --- 2. ACCOUNT SICHERHEIT (Email & Passwort) ---
    with st.expander("Account und Sicherheit"):
        # Email ändern
        new_email = st.text_input("Neue E-Mail Adresse", placeholder=user.email)
        if st.button("E-Mail ändern"):
            try:
                supabase.auth.update_user({"email": new_email})
                st.info("Bestätigungs-Links wurden an die alte UND neue Adresse gesendet!")
                log_event(
                    level="INFO",
                    message=f"Email of {st.session_state.current_username} changed and confirmation send",
                    details={"new_email": new_email}
                )
            except Exception as e:
                st.error(f"Fehler: {e}")
                log_event(
                    level="INFO",
                    message=f"Email changing of {st.session_state.current_username} failed",
                    details={"error": e}
                )

        st.write("---")
        # Passwort ändern
        with st.form("pw_form"):
            p1 = st.text_input("Neues Passwort", type="password")
            p2 = st.text_input("Bestätigen", type="password")
            if st.form_submit_button("Passwort ändern"):
                if p1 == p2 and len(p1) >= 6:
                    supabase.auth.update_user({"password": p1})
                    st.success("Passwort geändert!")
                    log_event(
                        level="INFO",
                        message=f"password of {st.session_state.current_username} changed",
                        details={"user": st.session_state.current_username}
                    )
                else:
                    st.error("Passwörter prüfen (min. 6 Zeichen).")
                    log_event(
                        level="INFO",
                        message=f"password changing of {st.session_state.current_username} failed",
                        details={"user": st.session_state.current_username}
                    )

    # --- 3. GRUPPENVERWALTUNG ---
    st.divider()
    st.subheader("Gruppen")
    t1, t2 = st.tabs(["Gruppe gründen", "Verwalten & Einladen"])

    with t1:
        with st.form("new_group"):
            g_name = st.text_input("Name der Schafkopf-Runde")
            if st.form_submit_button("Gründen") and g_name:
                if supabase.table("groups").select("groupname").eq("groupname", g_name).execute().data:
                    st.error("Name existiert bereits.")
                else:
                    supabase.table("groups").insert(
                        {"groupname": g_name, "boss": user.id, "members": [user.id]}).execute()
                    st.success(f"Gruppe {g_name} gegründet!");
                    log_event(
                        level="INFO",
                        message=f"new group {g_name} added by {st.session_state.current_username}",
                        details={"name": g_name, "boss": user.id}
                    )
                    st.rerun()

    with t2:
        my_groups = supabase.table("groups").select("*").eq("boss", user.id).execute().data
        if not my_groups:
            st.info("Du bist Admin keiner Gruppe.")
        else:
            sel_g = st.selectbox("Gruppe wählen", [g["groupname"] for g in my_groups])
            g_data = next(g for g in my_groups if g["groupname"] == sel_g)

            # --- MITGLIEDER VERWALTEN ---
            st.write(f"**Mitglieder ({len(g_data['members'])}):**")
            all_p = {p["user_id"]: p["username"] for p in
                     supabase.table("profiles").select("user_id, username").execute().data}

            for m_id in g_data["members"]:
                c1, c2 = st.columns([3, 1])
                c1.write(f"🃏 {all_p.get(m_id, 'Unbekannt')}" + (" (Boss)" if m_id == user.id else ""))
                if m_id != user.id and c2.button("❌", key=f"del_{m_id}"):
                    new_m = [i for i in g_data["members"] if i != m_id]
                    supabase.table("groups").update({"members": new_m}).eq("groupname", sel_g).execute()
                    st.rerun()

            # --- HINZUFÜGEN ---
            other_users = {u: id for id, u in all_p.items() if id not in g_data["members"]}
            new_m_name = st.selectbox("Registrierten User hinzufügen", ["-- wählen --"] + list(other_users.keys()))
            if st.button("Hinzufügen") and new_m_name != "-- wählen --":
                new_list = g_data["members"] + [other_users[new_m_name]]
                supabase.table("groups").update({"members": new_list}).eq("groupname", sel_g).execute()
                st.rerun()

            # --- GEFAHRENBEREICH: GRUPPE LÖSCHEN ---
            st.divider()
            with st.expander("⚠️ Gruppe auflösen"):
                st.warning(
                    f"Bist du sicher, dass du die Gruppe '{sel_g}' komplett löschen willst? Alle Daten gehen verloren.")
                confirm_delete = st.text_input("Gib 'LÖSCHEN' ein, um zu bestätigen")

                if st.button(f"Gruppe '{sel_g}' endgültig löschen", type="primary"):
                    if confirm_delete == "LÖSCHEN":
                        try:
                            # Löschen via groupname (oder id, falls du eine hast)
                            supabase.table("groups").delete().eq("groupname", sel_g).execute()
                            st.success(f"Gruppe '{sel_g}' wurde aufgelöst.")
                            log_event(
                                level="INFO",
                                message=f"{st.session_state.current_username} deleted group {sel_g}",
                                details={"name": sel_g, "boss": user.id}
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Löschen: {e}")
                            log_event(
                                level="INFO",
                                message=f"Deleting group {sel_g} by {st.session_state.current_username} failed",
                                details={"name": sel_g, "boss": user.id}
                            )
                    else:
                        st.error("Bitte bestätige mit dem Wort 'LÖSCHEN'.")

