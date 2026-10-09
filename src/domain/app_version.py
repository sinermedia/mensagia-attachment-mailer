import re


# A release number as written in the tags: three numbers, optionally after a v.
# Anything else (a pre-release suffix, "dev"...) is deliberately not matched,
# so it never takes part in a comparison
_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str | None) -> tuple[int, int, int] | None:
    """Read a release number such as 'v1.4.0' into comparable numbers.

    The parts are returned as integers so versions compare by number rather
    than by text: as text, 'v1.10.0' would sort before 'v1.9.0'.

    Args:
        text: Version to read, with or without the leading 'v'. Surrounding
            spaces are ignored.

    Returns:
        The (major, minor, patch) numbers, or None when the text is not a
        plain three-number version, such as 'dev' or 'v1.5.0-rc1'.
    """
    match = _VERSION.fullmatch((text or "").strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer(candidate: str | None, current: str | None) -> bool:
    """Tell whether *candidate* is a later release than *current*.

    Args:
        candidate: Version that may be newer, such as the latest release.
        current: Version it is compared with, such as the running one.

    Returns:
        True only when both versions can be read and the candidate is the
        higher one; an unreadable version on either side gives False, so
        nothing is ever reported on doubtful data.
    """
    candidate_parts, current_parts = parse_version(candidate), parse_version(current)
    if candidate_parts is None or current_parts is None:
        return False
    return candidate_parts > current_parts
