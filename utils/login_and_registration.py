import streamlit as st
from services.supabase_client import supabase
from services.supabase_client import log_event

def login_and_registration():
    # --- 1. INITIALISIERUNG ---
    for key, default in {
        "reset_mode": False,
        "otp_sent": False,
        "reset_email": ""
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    tab_login, tab_register = st.tabs(["Login", "Registrieren"])

    # ==================================================
    # LOGIN / PASSWORT RESET
    # ==================================================
    with tab_login:
        if not st.session_state.reset_mode:
            # NORMALER LOGIN
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Passwort", type="password")
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        if res.user:
                            # Session als Objekt speichern
                            st.session_state.user = res.user
                            st.session_state.session = res.session

                            # Profil-Check
                            p = supabase.table("profiles").select("*").eq("user_id", res.user.id).execute()
                            if not p.data:
                                supabase.table("profiles").insert(
                                    {"user_id": res.user.id, "username": email.split("@")[0]}).execute()
                            st.success("Erfolgreich eingeloggt!")

                            st.rerun()
                    except Exception as e:
                        err = str(e).lower()
                        msg = "🚫 Mail bestätigen!" if "email not confirmed" in err else "Daten falsch."
                        st.error(msg)

            if st.button("Passwort vergessen?"):
                st.session_state.reset_mode = True
                st.rerun()

        elif not st.session_state.otp_sent:
            # RESET STUFE 1: CODE ANFORDERN
            st.subheader("Code anfordern")
            res_mail = st.text_input("Email für Reset")
            c1, c2 = st.columns(2)
            if c1.button("Code senden", use_container_width=True) and res_mail:
                try:
                    supabase.auth.reset_password_for_email(res_mail)
                    st.session_state.reset_email, st.session_state.otp_sent = res_mail, True
                    st.success("Code wurde versandt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")
            if c2.button("Zurück", use_container_width=True):
                st.session_state.reset_mode = False
                st.rerun()

        else:
            # RESET STUFE 2: CODE EINGEBEN & UPDATE
            st.subheader("Code eingeben")
            st.info(f"Code gesendet an: {st.session_state.reset_email}")
            with st.form("otp_form"):
                code = st.text_input("8-stelliger Code")
                new_p = st.text_input("Neues Passwort (min. 6 Zeichen)", type="password")
                conf_p = st.text_input("Bestätigen", type="password")
                submit = st.form_submit_button("Passwort speichern & Einloggen")

                if submit:
                    if new_p == conf_p and len(new_p) >= 6:
                        try:
                            # 1. Verifizieren
                            v = supabase.auth.verify_otp({
                                "email": st.session_state.reset_email,
                                "token": code,
                                "type": "recovery"
                            })
                            if v.session:
                                # 2. Passwort aktualisieren (Nutzt die neue Session)
                                supabase.auth.update_user({"password": new_p})

                                # 3. Session im State setzen
                                st.session_state.user = v.user
                                st.session_state.session = v.session
                                st.session_state.reset_mode = False
                                st.session_state.otp_sent = False
                                st.success("Passwort geändert!")

                                log_event(
                                    level="INFO",
                                    message=f"{v.user} has succesfully changed pw",
                                    details={"user": v.user}
                                )

                                st.rerun()
                        except Exception as e:
                            log_event(
                                level="INFO",
                                message=f"{v.user} has failed changing pw",
                                details={"user": v.user}
                            )
                            st.error(f"Fehler: {e}")
                    else:
                        st.error("Prüfe deine Eingaben (Passwort-Länge/Gleichheit).")

            if st.button("Abbrechen"):
                st.session_state.otp_sent = False
                st.rerun()

    # ==================================================
    # REGISTER
    # ==================================================
    with tab_register:
        with st.form("reg_form"):
            reg_mail = st.text_input("Email")
            reg_pw = st.text_input("Passwort (min. 6 Zeichen)", type="password")
            if st.form_submit_button("Account erstellen", use_container_width=True, type="primary"):
                if len(reg_pw) >= 6:
                    try:
                        response = supabase.auth.sign_up({"email": reg_mail, "password": reg_pw})
                        if response.user:
                            st.success(f"✅ Account für {reg_mail} vorgemerkt!")
                            log_event(
                                level="INFO",
                                message=f"Registration mail send to {reg_mail}",
                                details={"mail": reg_mail}
                            )
                            st.info("Bitte schau in dein Postfach")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                else:
                    st.warning("Passwort zu kurz!")