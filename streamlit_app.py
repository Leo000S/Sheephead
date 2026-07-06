import streamlit as st
from services.supabase_client import supabase, init_global_user_data
from utils.statistic import run_statistics
from utils.book import run_book
from utils.login_and_registration import login_and_registration
from utils.profile import profile_menu
from utils.home import home
from utils.player_statistic import run_player_statistics
from utils.groups import group_menu, update_group_alle


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
    update_group_alle()
    # -----------------------------
    # SIDEBAR NAVIGATION
    # -----------------------------
    st.sidebar.title("Menü")
    menu = st.sidebar.radio(
        "Navigation",
        ["Home", "Profile", "Groups", "Sheephead-Book", "Sheephead-Statistic", "Personal-Statistic", "Logout"],
                key = "navigation_menu"
    )

    # =====================================
    # DASHBOARD
    # =====================================
    if menu == "Home":
        st.sidebar.divider()
        home(user)

    # =====================================
    # PROFIL
    # =====================================
    elif menu == "Profile":
        st.sidebar.divider()
        profile_menu(user)

    # =====================================
    # Gruppe
    # =====================================
    elif menu == "Groups":
        st.sidebar.divider()
        group_menu(user)

    # =====================================
    # SPACE 1
    # =====================================
    elif menu == "Sheephead-Book":
        st.sidebar.divider()
        run_book()

    # =====================================
    # SPACE 2
    # =====================================
    elif menu == "Sheephead-Statistic":
        st.sidebar.divider()
        run_statistics()

    # =====================================
    # SPACE 3
    # =====================================
    elif menu == "Personal-Statistic":
        st.sidebar.divider()
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
# Gastmodus
