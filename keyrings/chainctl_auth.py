"""
Chainctl Keyring Backend for Python Package Repositories

This module provides a keyring backend that authenticates to internal PyPI
repositories using chainctl pull tokens.
"""

import logging
import subprocess
from typing import Optional
from urllib.parse import urlparse

from keyring import backend
from keyring import credentials


class ChainctlAuthError(Exception):
    """Base exception for chainctl authentication errors."""

    pass


class ChainctlCommandError(ChainctlAuthError):
    """Raised when chainctl command execution fails."""

    pass


class ChainctlNotFoundError(ChainctlAuthError):
    """Raised when chainctl command is not found."""

    pass


class ChainctlTimeoutError(ChainctlAuthError):
    """Raised when chainctl command times out."""

    pass


class ChainctlAuth(backend.KeyringBackend):
    """Keyring backend for chainctl-based authentication."""

    priority = 9  # Higher priority than typical backends
    CHAINCTL_AUDIENCE = "libraries.cgr.dev"

    def __init__(self):
        super().__init__()
        self._credentials_cache = {}  # Cache both username and password
        self._logger = logging.getLogger(__name__)

    def _is_cgr_dev_service(self, service: str) -> bool:
        """Check if the service is a cgr.dev HTTPS URL.

        Args:
            service: The service URL to validate.

        Returns:
            True if the service is an HTTPS URL ending with .cgr.dev, False otherwise.
        """
        url = urlparse(service)

        # Only handle HTTPS URLs for domains ending with cgr.dev
        if not url.scheme == "https":
            return False

        # Check if the domain ends with cgr.dev
        if not url.hostname or not url.hostname.endswith(".cgr.dev"):
            return False

        return True

    def get_password(  # type: ignore[override]
        self, service: str, username: str
    ) -> Optional[str]:
        """Get password (auth token) for the given service.

        Args:
            service: The service URL requesting authentication.
            username: The username (unused, but required by keyring interface).

        Returns:
            The authentication token if available, None otherwise.
        """
        if not self._is_cgr_dev_service(service):
            return None

        if service in self._credentials_cache:
            return self._credentials_cache[service]

        try:
            token = self._get_chainctl_token()
            if token:
                self._credentials_cache[service] = token
                return token
            return None
        except ChainctlAuthError as e:
            self._logger.error(f"Failed to get chainctl pull token: {e}")
            return None

    def _get_chainctl_token(self) -> Optional[str]:
        """Execute chainctl command to get auth token.

        Returns:
            The authentication token from chainctl, or None if token is empty.

        Raises:
            ChainctlCommandError: If the chainctl command fails.
            ChainctlTimeoutError: If the chainctl command times out.
            ChainctlNotFoundError: If chainctl is not installed.
        """
        try:
            # Build the chainctl command
            cmd = [
                "chainctl",
                "auth",
                "token",
                f"--audience={self.CHAINCTL_AUDIENCE}",
            ]

            self._logger.debug(f"Executing: {' '.join(cmd)}")

            # Execute the command
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30,  # 30 second timeout
            )

            token = result.stdout.strip()
            if not token:
                return None
            return token

        except subprocess.CalledProcessError as e:
            self._logger.error(f"chainctl command failed: {e.stderr}")
            msg = f"chainctl command exited with status " f"{e.returncode}: {e.stderr}"
            raise ChainctlCommandError(msg) from e
        except subprocess.TimeoutExpired as e:
            raise ChainctlTimeoutError(
                f"chainctl command timed out after {e.timeout} seconds"
            ) from e
        except FileNotFoundError as e:
            msg = (
                "chainctl command not found. "
                "Please ensure chainctl is installed and in PATH"
            )
            raise ChainctlNotFoundError(msg) from e

    def set_password(self, service: str, username: str, password: str) -> None:
        """Setting passwords is not supported.

        Args:
            service: The service URL.
            username: The username.
            password: The password.

        Raises:
            NotImplementedError: Always raised as password setting is not supported.
        """
        raise NotImplementedError(
            "Setting passwords is not supported for chainctl auth"
        )

    def delete_password(self, service: str, username: str) -> None:
        """Deleting passwords is not supported.

        Args:
            service: The service URL.
            username: The username.

        Raises:
            NotImplementedError: Always raised as password deletion is not supported.
        """
        raise NotImplementedError(
            "Deleting passwords is not supported for chainctl auth"
        )

    def get_credential(  # type: ignore[override]
        self, service: str, username: str
    ) -> Optional[credentials.SimpleCredential]:
        """Get credential object for the service.

        Args:
            service: The service URL requesting authentication.
            username: The username (unused, but required by keyring interface).

        Returns:
            A SimpleCredential with username "_token" and the auth token as password,
            or None if authentication is not available.
        """
        if not self._is_cgr_dev_service(service):
            return None

        if service in self._credentials_cache:
            return credentials.SimpleCredential(
                "_token", self._credentials_cache[service]
            )

        password = self.get_password(service, username)
        if password:
            return credentials.SimpleCredential("_token", password)

        return None
