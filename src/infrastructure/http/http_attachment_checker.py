import requests
from requests.exceptions import RequestException
from src.domain.ports.attachment_checker import AttachmentChecker


class HttpAttachmentChecker(AttachmentChecker):
    def is_accessible(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 405:
                with requests.get(url, timeout=10, allow_redirects=True, stream=True) as r:
                    return r.status_code == 200
            return response.status_code == 200
        except RequestException:
            return False
