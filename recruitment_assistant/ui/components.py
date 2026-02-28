"""Streamlit UI components for the Recruitment Assistant dashboard."""

import pandas as pd
import streamlit as st
from typing import Any, Dict, List, Optional

from recruitment_assistant.ui.api_client import APIClient
from recruitment_assistant.ui.report_utils import generate_pdf_report


def render_sidebar(api_client: APIClient) -> None:
    """Render the collapsible sidebar with campaign status info."""
    with st.sidebar:
        if "exit_requested" not in st.session_state:
            st.session_state.exit_requested = False
        if st.button("Exit App", key="exit_app", use_container_width=True):
            st.session_state.exit_requested = True
        if st.session_state.exit_requested:
            st.success("You have exited the UI. Close the browser tab or stop Streamlit/uvicorn with Ctrl+C to fully shut down.")
            st.stop()

        st.title("Recruitment AI")
        st.markdown("---")

        status_resp = api_client.get_campaign_status("CAMP_001")
        if not status_resp.success:
            st.warning(status_resp.error or "Backend API not available.")
            return
        if not status_resp.data:
            st.warning("Backend returned empty status data.")
            return
        status = status_resp.data
        candidates = status.get("candidates_found", 0)
        targets = status.get("targets", 1) or 1
        st.info(f"Status: **{status.get('status', '').capitalize()}**")
        st.progress(min(candidates / targets, 1.0))
        st.write(f"Current Phase: `{status.get('current_phase', 'initializing')}`")
        st.write(f"Candidates Found: `{candidates}` / `{targets}` target")

        st.markdown("---")
        if st.button("Purge All Data", type="primary"):
            st.warning("Are you sure? This will delete all campaign data.")


def render_jd_section(api_client: APIClient) -> None:
    """Render the job description upload/initialization section."""
    with st.expander("📝 1. Upload Job Description (JD)", expanded=True):
        jd_title = st.text_input("Job Title", placeholder="e.g. Senior Software Engineer")
        jd_text = st.text_area("Full Job Description / Requirements", height=200, placeholder="Paste JD here...")
        uploaded_file = st.file_uploader("Or Upload JD (PDF/TXT)", type=["pdf", "txt"])

        if st.button("Initialize Campaign"):
            if jd_title and (jd_text or uploaded_file):
                payload = {"title": jd_title, "content": jd_text}
                res = api_client.create_campaign(payload)
                if res.success:
                    st.success(f"Campaign initialized for {jd_title}!")
                else:
                    st.error(res.error or "Failed to initialize campaign.")
            else:
                st.error("Please provide a Title and JD content.")


def render_candidates_section(api_client: APIClient) -> List[Dict[str, Any]]:
    """List candidate reviews and provide outreach approval controls."""
    st.subheader("🕵️ Selected Candidate Review")
    candidates_resp = api_client.get_campaign_candidates("CAMP_001")
    if not candidates_resp.success:
        st.error(candidates_resp.error or "Unable to load candidates.")
        return []

    candidates = candidates_resp.data or []
    if not candidates:
        st.info("Start a campaign or ensure the API is running to view candidate results.")
        return []

    for cand in candidates:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {cand.get('name', 'Candidate')}")
            st.markdown(f"**Role**: {cand.get('role', 'Unknown')}")
            tags = cand.get("tags", [])
            st.markdown(f"**Tags**: {' '.join([f'`{t}`' for t in tags])}")
            with st.expander("🔍 View Agent Rationale (HITL Transparency)"):
                st.write(cand.get("rationale", "No rationale provided."))

        with col2:
            st.markdown("### Outreach Draft Review")
            outreach_draft = st.text_area(
                f"Draft for {cand.get('name','Candidate')}",
                value=cand.get("outreach_draft", ""),
                height=150,
                key=f"outreach_{cand.get('id', 'candidate')}",
            )
            if st.button(f"Approve & Send to {cand.get('name','Candidate')}", key=f"btn_{cand.get('id','candidate')}"):
                payload = {
                    "campaign_id": "CAMP_001",
                    "candidate_id": cand.get("id", ""),
                    "message": outreach_draft or cand.get("outreach_draft", ""),
                }
                send_resp = api_client.send_outreach(payload)
                if send_resp.success:
                    st.success(f"Outreach queued for {cand.get('name','Candidate')}!")
                else:
                    st.error(send_resp.error or "Outreach queueing failed.")
    return candidates


def render_final_report(api_client: APIClient, candidates: Optional[List[Dict[str, Any]]]) -> None:
    """Show the final report metrics, recommendation, and download action."""
    st.markdown("---")
    st.subheader("📑 Final Recruitment Session Report")
    report_resp = api_client.get_campaign_report("CAMP_001")
    if not report_resp.success:
        st.info(report_resp.error or "Session report will be ready soon.")
        return

    report = report_resp.data or {}
    summ = report.get("session_summary", {})
    perf = report.get("performance_metrics", {})

    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Candidates Sourced", summ.get("total_candidates_sourced", 0))
        col2.metric("High Quality Matches", summ.get("high_quality_matches", 0))
        col3.metric("Manual Reviews", summ.get("manual_review_items", 0))
        col4.metric("Ethical Audit Status", summ.get("ethical_audit", {}).get("status", "pending"))
        st.markdown("#### Execution Performance")
        pcol1, pcol2, pcol3 = st.columns(3)
        pcol1.write(f"**Total Runtime**: {perf.get('total_execution_time', 'N/A')}")
        pcol2.write(f"**Avg Agent Latency**: {perf.get('avg_latency_per_agent', 'N/A')}")
        pcol3.write(f"**Estimated Cost (Tokens)**: {perf.get('estimated_token_cost', 'N/A')}")
        st.markdown("#### Strategic Recommendation")
        st.success(report.get("recommendation", "Recommendation pending."))

        pdf_bytes = generate_pdf_report(report, candidates or [])
        if not pdf_bytes:
            st.warning("Couldn\'t generate the PDF report right now; please try again shortly.")
        else:
            st.download_button(
                label="📄 Download Recruitment Report (PDF)",
                data=pdf_bytes,
                file_name=f"recruitment_session_{report.get('campaign_id','campaign')}.pdf",
                mime="application/pdf",
            )

        with st.expander("Detailed Audit & Ethics Logs (GDPR Requirement)"):
            st.json(report)