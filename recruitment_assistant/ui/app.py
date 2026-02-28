import streamlit as st
from recruitment_assistant.ui.api_client import APIClient
from recruitment_assistant.ui.components import (
    render_sidebar,
    render_jd_section,
    render_candidates_section,
    render_final_report,
)

API_BASE_URL: str = "http://localhost:8000"

st.set_page_config(page_title="Recruitment Assistant AI", layout="wide")

def main() -> None:
    api_client = APIClient(API_BASE_URL)
    render_sidebar(api_client)

    st.title("JD Dashboard & Campaign Manager")
    render_jd_section(api_client)
    candidates = render_candidates_section(api_client)
    render_final_report(api_client, candidates)


if __name__ == "__main__":
    main()
