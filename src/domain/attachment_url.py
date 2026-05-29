def resolve_attachment_url(value: str, base_url: str | None = None) -> str:
    if value.startswith(("http://", "https://")):
        return value
    if not base_url:
        raise ValueError(f"relative attachment '{value}' requires a base URL")
    return base_url.rstrip("/") + "/" + value.lstrip("/")
