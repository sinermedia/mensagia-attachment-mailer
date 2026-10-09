# Version reported when the running code does not come from a tagged build
DEV_VERSION = "dev"


def _built_version() -> str | None:
    """Return the version written into the code by the build workflow.

    The workflow writes src/build_version.py from the release tag before
    compiling, so the version never has to be updated by hand. The file is
    not in the repository, so the source code and untagged builds have none.

    Returns:
        The tag the build was made from, such as 'v1.4.0', or None.
    """
    # Imported here rather than at the top because the module only exists
    # in tagged builds; PyInstaller still finds and bundles it
    try:
        from src.build_version import VERSION
    except ImportError:
        return None
    return VERSION


def current_version() -> str:
    """Return the version of the running application.

    A tagged build reports its own tag. The source code and untagged builds
    report 'dev', which is never compared with any release. To try the new
    version notice from the source code, create src/build_version.py by hand
    (git ignores it) with an older version, such as VERSION = "v1.3.0".

    Returns:
        The running version, such as 'v1.4.0', or 'dev'.
    """
    return _built_version() or DEV_VERSION
