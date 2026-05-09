import streamlit as st
from services.supabase_client import supabase


def home(user):
    st.title("🃏 Infos & Aktuelles")

    # Begrüßung
    st.info(f"Schön, dass du da bist! Eingeloggt als: **{user.email}**")

    # Spalten-Layout für die erste Sektion
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📢 Neuigkeiten")
        st.write("""
        *   **Nächstes Turnier:** 25. Mai 2026!
        *   **App-Status:** Wir sind jetzt in einer Art Beta-Phase.
        """)

    with col2:
        st.caption("Besitzer des Wanderpokals seit: 12.04.2026")
        st.write("Ben - *Ehre, wem Ehre gebührt!*")

    st.divider()

    # Termine & Kalender
    st.subheader("📅 Nächste Termine")
    t1, t2, t3 = st.columns(3)
    t1.metric("Stammtisch", "Jeden ??.")
    t2.metric("Nächster Spielabend", "??. Mai")
    t3.metric("Großes Turnier", "Juni '??")

    st.divider()

    # Rechtliches & Spende in einem expander (nimmt nicht so viel Platz weg)
    with st.expander("⚖️ Rechtliches & Unterstützung"):
        st.write("""
        **Erklärung des Erstellers:**
        Diese App wurde nach bestem Wissen und Gewissen entwickelt. 
        *   Es wird **keine Haftung** für Richtigkeit der Punkte, Serverausfälle oder verlorene Daten übernommen.
        *   Die Nutzung erfolgt auf eigene Gefahr.
        *   Dies ist ein privates Projekt zur Förderung unserer Spielkultur.

        **Support:**
        Wenn dir die App gefällt und du die Serverkosten (oder mein nächstes Kaltgetränk) unterstützen möchtest, freue ich mich über eine kleine Spende:
        """)

        st.caption("Email für PayPal: schallerleopold01@gmail.com")
        st.caption("Email für Wero: schallerleopold01@gmail.com")

    # Was dir noch einfallen könnte (Vorschlag: Statistiken oder Zitate)
    st.divider()
    st.subheader("💡 Wusstest du schon?")
    st.write("_'Ein schlechtes Blatt ist kein Grund für schlechte Laune – außer es ist ein Solo-Tout.'_")

    # Optional: Ein kleiner Quick-Link-Bereich
    # Einladungs-Link Sektion
    st.write("**Freunde einladen**")
    app_url = "https://deine-app.streamlit.app"  # ODER localhost:8501
    st.code(f"{app_url}", language="text")
    st.caption("Kopiere diesen Link und sende ihn deinen Freunden, damit sie sich registrieren können.")
