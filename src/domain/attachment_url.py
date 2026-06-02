def resolve_attachment_url(value: str, base_url: str | None = None) -> str:
    """Resolve an attachment value to a fully qualified URL.

    Contact extra fields can store either a complete URL
    (e.g. 'https://cdn.example.com/docs/contract_42.pdf') or just a
    filename / relative path (e.g. 'contract_42.pdf'). This function
    normalises both forms to an absolute URL that the Mensagia API and
    the attachment checker can use directly.

    When the value is already absolute (starts with http:// or https://)
    it is returned unchanged. When it is relative, *base_url* is required
    and is prepended after normalising the trailing/leading slashes.

    Args:
        value: The raw attachment value from the contact's extra field.
            Can be a full URL or a relative path/filename.
        base_url: Root URL to prepend when *value* is relative. May include
            a trailing slash — it is stripped before joining. Required
            whenever *value* is not an absolute URL; raises ValueError
            if absent in that case.

    Returns:
        A fully qualified URL string suitable for use as an email attachment.

    Raises:
        ValueError: If *value* is a relative path and *base_url* is None
            or an empty string.
    """
    # Absolute URLs are returned as-is — no transformation needed
    if value.startswith(("http://", "https://")):
        return value

    # Relative paths require a base URL to be useful
    if not base_url:
        raise ValueError(f"relative attachment '{value}' requires a base URL")

    # Join base and relative path, normalising slashes so there is exactly one
    return base_url.rstrip("/") + "/" + value.lstrip("/")
