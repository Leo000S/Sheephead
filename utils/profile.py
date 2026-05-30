
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

