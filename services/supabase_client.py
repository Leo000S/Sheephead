import streamlit as st
from supabase import create_client
import streamlit as st


def log_event(level: str, message: str, details: dict = None):
    """
    Schreibt einen Log-Eintrag in die Supabase-Datenbank.
    Levels: 'INFO', 'WARNING', 'ERROR'
    """
    try:
        # Versuche die aktuell gespeicherte User-ID aus dem Session State zu holen
        user_id = st.session_state.get("current_user_id", None)

        log_entry = {
            "level": level.upper(),
            "message": message,
            "user_id": user_id,
            "details": details  # Kann ein Python-Dict sein oder None
        }

        # In Supabase einfügen
        supabase.table("app_logs").insert(log_entry).execute()

    except Exception as e:
        # WICHTIG: Wenn das Logging fehlschlägt, darf nicht die ganze App abstürzen!
        # Daher loggen wir es hier nur stumpf in die Server-Konsole.
        print(f"CRITICAL: Logging fehlgeschlagen: {e}: #{message}#")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)


def init_global_user_data():
    """Lädt alle Profile und den aktuellen User einmalig in den Session State."""

    # 1. Alle Profile laden, falls noch nicht geschehen
    if "id_to_username" not in st.session_state:
        try:
            res = supabase.table("profiles").select("user_id, username").execute()
            profiles = res.data if res.data else []

            # Die beiden gewünschten Lookup-Dicts bauen
            st.session_state.id_to_username = {p["user_id"]: p["username"] for p in profiles}
            st.session_state.username_to_id = {p["username"]: p["user_id"] for p in profiles}
        except Exception as e:
            st.error(f"Fehler beim Laden der Profile: {e}")
            st.session_state.id_to_username = {}
            st.session_state.username_to_id = {}

    # 2. Aktuell eingewählten User bestimmen
    if "current_user_id" not in st.session_state:
        try:
            user_response = supabase.auth.get_user()
            if user_response.user:
                u_id = user_response.user.id
                st.session_state.current_user_id = u_id
                # Username aus dem frisch gebauten Dict holen
                st.session_state.current_username = st.session_state.id_to_username.get(u_id, "Unbekannt")
            else:
                st.session_state.current_user_id = None
                st.session_state.current_username = "Nicht angemeldet"
        except Exception:
            st.session_state.current_user_id = None
            st.session_state.current_username = "Fehler"