"""UI-focused tests that cover the Streamlit report download experience."""

from typing import Any, Dict

import pytest

from recruitment_assistant.ui import components
from recruitment_assistant.ui.api_client import APIClient, APIResponse


class DummyApiClient(APIClient):
    def __init__(self, response: APIResponse) -> None:
        super().__init__(base_url="http://example.com")
        self._response = response

    def get_campaign_report(self, campaign_id: str) -> APIResponse:
        return self._response


class StreamlitSpy:
    class _DummyCtx:
        def __enter__(self) -> "StreamlitSpy._DummyCtx":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
            return False

    class ColumnSpy:
        def __init__(self) -> None:
            self.metric_calls: list = []
            self.write_calls: list = []

        def metric(self, *args: Any, **kwargs: Any) -> None:
            self.metric_calls.append((args, kwargs))

        def write(self, *args: Any, **kwargs: Any) -> None:
            self.write_calls.append((args, kwargs))

    def __init__(self) -> None:
        self.download_button_calls: list = []
        self.warning_calls: list = []

    def container(self) -> "StreamlitSpy._DummyCtx":
        return self._DummyCtx()

    def columns(self, count: int) -> tuple["StreamlitSpy.ColumnSpy", ...]:
        return tuple(self.ColumnSpy() for _ in range(count))

    def expander(self, label: str, expanded: bool = False) -> "StreamlitSpy._DummyCtx":
        return self._DummyCtx()

    @staticmethod
    def subheader(*args: Any, **kwargs: Any) -> None:
        return None

    @staticmethod
    def markdown(*args: Any, **kwargs: Any) -> None:
        return None

    @staticmethod
    def info(*args: Any, **kwargs: Any) -> None:
        return None

    @staticmethod
    def success(*args: Any, **kwargs: Any) -> None:
        return None

    @staticmethod
    def json(*args: Any, **kwargs: Any) -> None:
        return None

    @staticmethod
    def write(*args: Any, **kwargs: Any) -> None:
        return None

    def download_button(self, *args: Any, **kwargs: Any) -> None:
        self.download_button_calls.append((args, kwargs))

    def warning(self, message: str) -> None:
        self.warning_calls.append(message)


REPORT_PAYLOAD: Dict[str, Any] = {
    "campaign_id": "CAMP_001",
    "session_summary": {
        "total_candidates_sourced": 2,
        "high_quality_matches": 1,
        "manual_review_items": 0,
        "ethical_audit": {"status": "ready"},
    },
    "performance_metrics": {
        "total_execution_time": "5s",
        "avg_latency_per_agent": "0.2s",
        "estimated_token_cost": 123,
    },
    "recommendation": "Proceed with outreach",
}


def _render_final_report(monkeypatch: pytest.MonkeyPatch, pdf_bytes: bytes) -> StreamlitSpy:
    """Drive render_final_report with a stubbed API client and Streamlit spy."""
    stub = StreamlitSpy()
    monkeypatch.setattr(components, "st", stub)
    monkeypatch.setattr(components, "generate_pdf_report", lambda *_: pdf_bytes)
    api_response = APIResponse(success=True, data=REPORT_PAYLOAD)
    client = DummyApiClient(api_response)
    components.render_final_report(client, [])
    return stub


def test_render_final_report_hides_download_button_when_pdf_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _render_final_report(monkeypatch, b"")
    assert not stub.download_button_calls


def test_render_final_report_warns_when_pdf_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _render_final_report(monkeypatch, b"")
    assert stub.warning_calls
    assert "Couldn't generate the PDF report" in stub.warning_calls[0]