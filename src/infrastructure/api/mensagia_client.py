import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout


# Root URL of the Mensagia REST API v1.
BASE_URL = "https://api.mensagia.com/v1"

# Default page size for paginated list endpoints.
# 100 is the maximum the Mensagia API supports per request.
DEFAULT_PER_PAGE = 100


class MensagiaAPIError(Exception):
    """Raised when the Mensagia API returns an error or is unreachable.

    Wraps both HTTP-level errors (non-2xx responses parsed from the JSON
    error body) and transport-level errors (connection failures, timeouts)
    so callers only need to handle one exception type.

    Attributes:
        code: Mensagia application-level error code string, when available
            in the JSON response body (e.g. 'unauthorized'). None otherwise.
        http_code: HTTP status code of the response (e.g. 401, 404). None
            for transport errors where no response was received.
    """

    def __init__(self, message: str, code: str = None, http_code: int = None):
        """Initialise the error with a human-readable message and optional metadata.

        Args:
            message: Human-readable description of the error.
            code: Mensagia application-level error code, if available.
            http_code: HTTP status code of the response, if available.
        """
        super().__init__(message)
        self.code = code
        self.http_code = http_code


class MensagiaClient:
    """Low-level HTTP client for the Mensagia REST API v1.

    Encapsulates authentication (via api_token query parameter), request
    construction, response parsing, error handling, and pagination. Higher-
    level repository and sender adapters delegate all HTTP communication to
    this class so they stay thin and focused on data mapping.

    A single requests.Session is reused across calls to benefit from
    HTTP keep-alive connection pooling.
    """

    def __init__(self, api_token: str):
        """Initialise the client with the account's API token.

        Args:
            api_token: Mensagia API token string. Appended as a query
                parameter to every request because the Mensagia API does
                not use header-based bearer authentication.
        """
        self.api_token = api_token

        # Reuse a single session for all requests to take advantage of
        # connection pooling and avoid repeated TLS handshakes
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Perform a GET request and return the parsed JSON response.

        Args:
            endpoint: API path relative to BASE_URL (e.g. 'agendas').
            params: Optional query string parameters. The api_token is
                injected automatically and must not be included here.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            MensagiaAPIError: On non-2xx responses or transport failures.
        """
        params = params or {}
        # Inject authentication token as a query parameter on every request
        params["api_token"] = self.api_token
        try:
            response = self.session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
            self._raise_for_error(response)
            return response.json()
        except (ConnectionError, Timeout) as exc:
            raise MensagiaAPIError(f"Connection error: {exc}") from exc

    def _post(self, endpoint: str, data: dict = None) -> dict:
        """Perform a POST request with form-encoded body and return the parsed JSON.

        Args:
            endpoint: API path relative to BASE_URL (e.g. 'email/simple').
            data: Form fields to include in the request body. The api_token
                is injected automatically and must not be included here.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            MensagiaAPIError: On non-2xx responses or transport failures.
        """
        data = data or {}
        # Inject authentication token into the POST body (Mensagia API convention)
        data["api_token"] = self.api_token
        try:
            response = self.session.post(f"{BASE_URL}/{endpoint}", data=data, timeout=30)
            self._raise_for_error(response)
            return response.json()
        except (ConnectionError, Timeout) as exc:
            raise MensagiaAPIError(f"Connection error: {exc}") from exc

    def _raise_for_error(self, response: requests.Response):
        """Raise MensagiaAPIError if the response indicates a failure.

        Attempts to extract the structured error information from the JSON
        body first. Falls back to the raw response text if parsing fails.

        Args:
            response: The requests.Response object to inspect.

        Raises:
            MensagiaAPIError: When response.ok is False.
        """
        if not response.ok:
            try:
                # Try to parse the structured error body returned by Mensagia
                error = response.json().get("error", {})
                raise MensagiaAPIError(
                    error.get("message", response.text),
                    code=error.get("code"),
                    http_code=response.status_code,
                )
            except (ValueError, KeyError):
                # Fall back to raw text if the body is not valid JSON
                raise MensagiaAPIError(response.text, http_code=response.status_code)

    def get_all_pages(self, endpoint: str, params: dict = None) -> list:
        """Fetch all items from a paginated Mensagia list endpoint.

        Iterates through pages until the last page is reached, collecting
        all items into a single flat list. Uses the pagination metadata
        returned in the 'meta.pagination.total_pages' field to know when
        to stop.

        Args:
            endpoint: API path relative to BASE_URL.
            params: Extra query parameters to include on every page request.

        Returns:
            A flat list of all items across all pages.

        Raises:
            MensagiaAPIError: On any HTTP or transport error during pagination.
        """
        params = params or {}
        params["per_page"] = DEFAULT_PER_PAGE
        all_items = []
        page = 1

        # Keep fetching pages until we have reached the last one
        while True:
            params["page"] = page
            data = self._get(endpoint, params)

            items = data.get("data", [])
            all_items.extend(items)

            # Check pagination metadata to decide whether to continue
            pagination = data.get("meta", {}).get("pagination", {})
            if page >= pagination.get("total_pages", 1):
                break
            page += 1

        return all_items

    def get_agendas(self) -> list:
        """Fetch all contact groups (agendas) from the account.

        Returns:
            List of raw agenda dictionaries as returned by the API.
        """
        return self.get_all_pages("agendas")

    def get_contacts(self, group_id: int, in_mail_blacklist: bool = False) -> list:
        """Fetch all contacts belonging to the given agenda group.

        Args:
            group_id: Numeric ID of the agenda group to query.
            in_mail_blacklist: Whether to include contacts that are on the
                global email blacklist. Defaults to False to exclude them.
                Note: the blacklist is independent of agenda subscription
                status; this parameter does not filter by subscription.

        Returns:
            List of raw contact dictionaries as returned by the API.
        """
        params = {
            "groups": str(group_id),
            "in_mail_blacklist": "true" if in_mail_blacklist else "false",
        }
        return self.get_all_pages("contacts", params)

    def get_email_addresses(self) -> list:
        """Fetch all verified sender email addresses in the account.

        Returns:
            List of raw sender address dictionaries as returned by the API.
        """
        return self.get_all_pages("email/sender_address")

    def get_email_templates(self) -> list:
        """Fetch all email templates created in the account.

        Returns:
            List of raw template dictionaries as returned by the API.
        """
        return self.get_all_pages("email/templates")

    def get_extra_fields(self) -> list:
        """Fetch all custom extra field definitions for the account.

        Returns:
            List of raw extra field dictionaries as returned by the API.
        """
        return self.get_all_pages("extrafields")

    def send_email(self, payload: dict) -> dict:
        """Schedule a single email for delivery via the Mensagia simple send endpoint.

        Args:
            payload: Dictionary of form fields as required by the
                'email/simple' Mensagia API endpoint.

        Returns:
            Parsed JSON response dict containing the scheduled message details.

        Raises:
            MensagiaAPIError: If the API rejects the request or a transport
                error occurs.
        """
        return self._post("email/simple", payload)

    def validate_token(self) -> bool:
        """Check whether the stored API token is valid and the account is reachable.

        Performs a lightweight API call (fetching 1 agenda) to test
        authentication without loading significant data. Used on startup
        to give fast feedback if the token in .env is wrong.

        Returns:
            True if the token is accepted by the API; False otherwise.
        """
        try:
            # A minimal request to verify the token without loading data
            self._get("agendas", {"per_page": 1})
            return True
        except MensagiaAPIError:
            return False
