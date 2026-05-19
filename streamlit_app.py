import streamlit as st
from services.supabase_client import supabase
from services.supabase_client import init_global_user_data
from utils.statistic import run_statistics
from utils.book import run_book
from utils.login_and_registration import login_and_registration
from utils.profile import profile_menu
from utils.home import home
from utils.player_statistic import run_player_statistics
from services.supabase_client import log_event


if "session" in st.session_state:
    supabase.auth.set_session(
        access_token=st.session_state.session.access_token,
        refresh_token=st.session_state.session.refresh_token
    )

st.set_page_config(page_title="Schafkopf - Login", page_icon="🔐")

# -------- Session initialisieren --------
if "user" not in st.session_state:
    st.session_state.user = None


# =========================================
# NICHT EINGELOGGT → LOGIN / REGISTER
# =========================================
if st.session_state.user is None:
    st.title("Hallo liebe Freunde des Schafkopfens")

    login_and_registration()


# =========================================
# EINGELOGGT → APP BEREICH
# =========================================
else:
    user = st.session_state.user
    init_global_user_data()
    # -----------------------------
    # SIDEBAR NAVIGATION
    # -----------------------------
    st.sidebar.title("Menü")
    menu = st.sidebar.radio(
        "Navigation",
        ["Home", "Profile", "Sheephead-Book", "Sheephead-Statistic", "Personal-Statistic", "Logout"]
    )

    # =====================================
    # DASHBOARD
    # =====================================
    if menu == "Home":
        home(user)

    # =====================================
    # PROFIL
    # =====================================
    elif menu == "Profile":
        profile_menu(user)

    # =====================================
    # SPACE 1
    # =====================================
    elif menu == "Sheephead-Book":
        run_book()


    # =====================================
    # SPACE 2
    # =====================================
    elif menu == "Sheephead-Statistic":
        run_statistics()

    # =====================================
    # SPACE 3
    # =====================================
    elif menu == "Personal-Statistic":
        run_player_statistics()




    # =====================================
    # LOGOUT
    # =====================================
    elif menu == "Logout":
        logout = st.button("Logout?")
        if logout:
            supabase.auth.sign_out()
            st.session_state.clear()
            st.rerun()


# streamlit run /Users/leopoldschaller/Desktop/Sheephead/streamlit_app.py

# Code verschlanken???
