"""
Tox plugin to automatically configure chainctl authentication for test environments.

This plugin ensures that chainctl authentication is available when running tests
with tox, particularly useful for testing packages that depend on private
repositories hosted on *.cgr.dev domains.
"""

import logging

try:
    from tox import hookimpl
except ImportError:
    # When tox is not installed (e.g., during testing), create a no-op decorator
    def hookimpl(func):
        return func


logger = logging.getLogger(__name__)


@hookimpl
def tox_configure(config):
    """Configure tox to use chainctl authentication."""
    # Log that the plugin is active
    logger.info("Chainctl auth tox plugin activated")


@hookimpl
def tox_testenv_install_deps(venv, action):
    """
    Hook called before installing dependencies in a test environment.

    Ensures chainctl authentication is available for pip installations.
    """
    # Ensure the keyring backend is available
    result = venv.run_install(
        ["keyrings-chainguard-libraries"],
        action=action,
    )

    if result:
        action.setactivity("chainctl-auth", "Installed chainctl keyring backend")

    return result


@hookimpl
def tox_runtest_pre(venv):
    """
    Hook called before running tests.

    Verifies that chainctl is available and properly configured.
    """
    # Check if chainctl is available
    try:
        result = venv.run(["chainctl", "version"], capture=True, check=False)
        if result.returncode != 0:
            logger.warning(
                "chainctl command not found or not working properly. "
                "Authentication to *.cgr.dev repositories may fail."
            )
    except Exception as e:
        logger.warning(f"Could not verify chainctl installation: {e}")


# Plugin metadata
plugin = "chainctl_auth_tox.bootstrap"
