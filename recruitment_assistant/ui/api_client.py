from dataclasses import dataclass
import requests
import structlog
from typing import Any, Dict, List, Optional

logger = structlog.get_logger(__name__)


@dataclass
class APIResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class APIClient:
    def __init__(self, base_url: str, timeout: int = 6) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = requests.request(method, url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            if response.status_code == 204:
                return APIResponse(success=True, data=True)
            return APIResponse(success=True, data=response.json())
        except requests.HTTPError as exc:
            message = (
                exc.response.text if exc.response and exc.response.text else str(exc)
            )
            logger.error(
                "api-http-error",
                endpoint=endpoint,
                status_code=exc.response.status_code if exc.response else None,
                message=message,
                exc_info=True,
            )
            return APIResponse(success=False, error=f"HTTP Error: {message}")
        except requests.RequestException as exc:
            message = str(exc)
            logger.error(
                "api-request-error",
                endpoint=endpoint,
                error=message,
                exc_info=True,
            )
            return APIResponse(success=False, error="Unable to reach the backend API at the moment. Please try again later.")

    def get_campaign_status(self, campaign_id: str) -> APIResponse:
        return self._request(f"campaigns/{campaign_id}/status")

    def create_campaign(self, payload: Dict[str, Any]) -> APIResponse:
        return self._request("campaigns", method="POST", payload=payload)

    def get_campaign_candidates(self, campaign_id: str) -> APIResponse:
        return self._request(f"campaigns/{campaign_id}/candidates")

    def rank_candidates(
        self, campaign_id: str, payload: Optional[Dict[str, Any]] = None
    ) -> APIResponse:
        return self._request(f"campaigns/{campaign_id}/rank", method="POST", payload=payload)

    def create_outreach_drafts(self, campaign_id: str) -> APIResponse:
        return self._request(f"campaigns/{campaign_id}/outreach", method="POST")

    def send_outreach(self, payload: Dict[str, Any]) -> APIResponse:
        return self._request("outreach/send", method="POST", payload=payload)

    def get_campaign_report(self, campaign_id: str) -> APIResponse:
        return self._request(f"campaigns/{campaign_id}/report")