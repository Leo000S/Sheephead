import streamlit as st
def home(user):
    st.title("Infos & Aktuelles")
    # Begrüßung
    st.info(f"Schön, dass du da bist! Eingeloggt als: **{st.session_state.current_username}**")

    st.divider()

    st.markdown('<p style="font-size:14px; margin-bottom:0px; color:gray;">BesitzerIn des Wanderpokals</p>',
                unsafe_allow_html=True)
    st.markdown('<p style="font-size:18px; font-weight:bold;">Davina, herzlichen Glückwunsch !!!</p>',
                unsafe_allow_html=True)
    st.divider()


    st.subheader("Nächste Termine")

    t1, t2 = st.columns(2)

    with t1:
        st.markdown('<p style="font-size:14px; margin-bottom:0px; color:gray;">Großes Turnier</p>',
                    unsafe_allow_html=True)
        st.markdown('<p style="font-size:18px; font-weight:bold;">23.12 in der Augsburger Stadtbücherei</p>',
                    unsafe_allow_html=True)

    with t2:
        st.markdown('<p style="font-size:14px; margin-bottom:0px; color:gray;">Nächstes Turnier</p>',
                    unsafe_allow_html=True)
        st.markdown('<p style="font-size:24px; font-weight:bold;">??</p>', unsafe_allow_html=True)

    st.divider()
    st.subheader("*Wusstest du schon?*")
    st.write("Allein durch den Klick auf Spiel abspeichern ist das Spiel schon online gesichert - also bitte nicht Spiele doppelt nachtragen")
    st.write("Streamlit stürzt leider ab, wenn es Verbindungsprobleme gibt oder dein Browser neu lädt. Bereits angefangene Runden kannst du über \" offene Runden \" jedoch später einfach weiterfüllen")

    st.subheader("*Freunde einladen*")
    app_url = "https://sheephead.streamlit.app"
    st.code(f"{app_url}", language="text")
    st.caption("Kopiere diesen Link und sende ihn deinen Freunden, damit sie sich registrieren können.")

    with st.expander("Regelwerk"):
        with open("assets/RegelwerkWue.pdf", "rb") as f:
            st.download_button(
                label="Würzburger Regeln als PDF herunterladen",
                data=f,
                file_name="Schafkopf_Regeln_Wue.pdf",
                mime="application/pdf"
            )

    with st.expander("So werden die Punkte berechnet"):
        aux, wue = st.columns([1, 1])
        with aux:
            st.subheader("Normale Berechnung")
            st.write("- Hier halten wir uns an die traditionellen Punkteverteilung:")
            st.write("- Ruf = 1 Punkt, Soli (Wenz und Trumpfsolo) = 5 Punkte")
            st.write("- Schneider, Schwarz = +1 Punkt")
            st.write(r"- Klopfen, Kontra, Tout, ... führt zu Verdopplung der Punkte, also ein Faktor $2^n$ = 2, 4, 6, ...")
            st.write("- Zusätzlich gibt es einen Ramsch (1 Punkt) und Durchmarsch (3 Punkte)")
        with wue:
            st.subheader("Würzburger Berechnung")
            st.write("- Hier ist der Ruf wertvoller, und eine Niederlage als Spielerpartei schmerzhaft (+1 Punkt):")
            st.write("- Ruf = 1 Punkt, Soli (Wenz und Trumpfsolo) = 3 Punkte")
            st.write("- Schneider, Schwarz = +1 Punkt")
            st.write(r"- Klopfen, Kontra, Tout, ...  Erhöhung der Punkte um den Faktor n+1 = 2, 3, 4, ...")
            st.write("- Zusätzlich gibt es einen Ramsch (1 Punkt), Durchmarsch (3 Punkte), Geier(3 Punkte) und einen Bettel (Brett) für 3(4) Punkte")

    with st.expander("Rechtliches & Unterstützung"):
        st.write("""
        **Erklärung des Erstellers:**
        Diese App wurde nach bestem Wissen und Gewissen entwickelt. 
        *   Es wird **keine Haftung** für Richtigkeit der Punkte, Serverausfälle oder verlorene Daten übernommen.
        *   Dies ist ein privates Projekt zur Förderung unserer Spielkultur.""")
        #**Support:**
        #Wenn dir die App gefällt und du das Projekt unterstützen möchtest:
        #""")

        #st.caption("Email für PayPal: schallerleopold01@gmail.com")
        #st.caption("Email für Wero: schallerleopold01@gmail.com")