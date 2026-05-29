import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout


BASE_URL = "https://api.mensagia.com/v1"
DEFAULT_PER_PAGE = 100


class MensagiaAPIError(Exception):
    def __init__(self, message: str, code: str = None, http_code: int = None):
        super().__init__(message)
        self.code = code
        self.http_code = http_code


class MensagiaClient:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict = None) -> dict:
        params = params or {}
        params["api_token"] = self.api_token
        try:
            response = self.session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
            self._raise_for_error(response)
            return response.json()
        except (ConnectionError, Timeout) as exc:
            raise MensagiaAPIError(f"Connection error: {exc}") from exc

    def _post(self, endpoint: str, data: dict = None) -> dict:
        data = data or {}
        data["api_token"] = self.api_token
        try:
            response = self.session.post(f"{BASE_URL}/{endpoint}", data=data, timeout=30)
            self._raise_for_error(response)
            return response.json()
        except (ConnectionError, Timeout) as exc:
            raise MensagiaAPIError(f"Connection error: {exc}") from exc

    def _raise_for_error(self, response: requests.Response):
        if not response.ok:
            try:
                error = response.json().get("error", {})
                raise MensagiaAPIError(
                    error.get("message", response.text),
                    code=error.get("code"),
                    http_code=response.status_code,
                )
            except (ValueError, KeyError):
                raise MensagiaAPIError(response.text, http_code=response.status_code)

    def get_all_pages(self, endpoint: str, params: dict = None) -> list:
        params = params or {}
        params["per_page"] = DEFAULT_PER_PAGE
        all_items = []
        page = 1
        while True:
            params["page"] = page
            data = self._get(endpoint, params)
            items = data.get("data", [])
            all_items.extend(items)
            pagination = data.get("meta", {}).get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break
            page += 1
        return all_items

    def get_agendas(self) -> list:
        return self.get_all_pages("agendas")

    def get_contacts(self, group_id: int, in_mail_blacklist: bool = False) -> list:
        params = {
            "groups": str(group_id),
            "in_mail_blacklist": "true" if in_mail_blacklist else "false",
        }
        return self.get_all_pages("contacts", params)

    def get_email_addresses(self) -> list:
        return self.get_all_pages("email/sender_address")

    def get_email_templates(self) -> list:
        return self.get_all_pages("email/templates")

    def get_extra_fields(self) -> list:
        return self.get_all_pages("extrafields")

    def send_email(self, payload: dict) -> dict:
        return self._post("email/simple", payload)

    def validate_token(self) -> bool:
        try:
            self._get("agendas", {"per_page": 1})
            return True
        except MensagiaAPIError:
            return False
