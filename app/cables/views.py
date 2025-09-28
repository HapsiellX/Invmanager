"""
Cable inventory views
"""

import streamlit as st
from core.security import require_auth


@require_auth
def show_cables_page():
    """
    Cable inventory management page
    """
    st.header("🔌 Kabel Inventar")
    st.info("Kabel Inventar Seite - Implementation in Arbeit")