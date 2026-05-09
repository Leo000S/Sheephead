import streamlit as st
from supabase import create_client

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_ANON_KEY"]
service_key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(url, key)
supabase_admin = create_client(url, service_key)