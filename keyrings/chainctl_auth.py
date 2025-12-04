"""
Chainctl Keyring Backend for Python Package Repositories

This module provides a keyring backend that authenticates to internal PyPI
repositories using chainctl pull tokens.
"""

import logging
import subprocess
from urllib.parse import urlparse

from keyring import backend
from keyring import credentials


class ChainctlAuth(backend.KeyringBackend):
    """Keyring backend for chainctl-based authentication."""

    priority = 9  # Higher priority than typical backends

    def __init__(self):
        super().__init__()
        self._credentials_cache = {}  # Cache both username and password
        self._logger = logging.getLogger(__name__)

    def _is_cgr_dev_service(self, service):
        """Check if the service is a cgr.dev HTTPS URL."""
        url = urlparse(service)

        # Only handle HTTPS URLs for domains ending with cgr.dev
        if not url.scheme == "https":
            return False

        # Check if the domain ends with cgr.dev
        if not url.hostname or not url.hostname.endswith(".cgr.dev"):
            return False

        return True

    def get_password(self, service, username):
        """Get password (auth token) for the given service."""
        if not self._is_cgr_dev_service(service):
            return None

        # Check cache first
        if service in self._credentials_cache:
            cached_token = self._credentials_cache[service]
            # Return the cached token
            return cached_token

        try:
            # Fetch auth token using chainctl
            token = self._get_chainctl_token()
            if token:
                # Cache the token
                self._credentials_cache[service] = token
                # Return the token
                return token
        except Exception as e:
            self._logger.error(f"Failed to get chainctl pull token: {e}")

        return None

    def _get_chainctl_token(self):
        """Execute chainctl command to get auth token."""
        try:
            # Build the chainctl command
            cmd = [
                "chainctl",
                "auth",
                "token",
                "--audience=libraries.cgr.dev",
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

            # Parse the output to extract token
            output_lines = result.stdout.strip().split("\n")
            # The token is in the first line
            token = output_lines[0]
            return token

        except subprocess.CalledProcessError as e:
            self._logger.error(f"chainctl command failed: {e.stderr}")
            msg = (
                f"chainctl command exited with status "
                f"{e.returncode}: {e.stderr}"
            )
            raise Exception(msg)
        except subprocess.TimeoutExpired:
            raise Exception("chainctl command timed out")
        except FileNotFoundError:
            msg = (
                "chainctl command not found. "
                "Please ensure chainctl is installed and in PATH"
            )
            raise Exception(msg)

    def set_password(self, service, username, password):
        """Setting passwords is not supported."""
        raise NotImplementedError(
            "Setting passwords is not supported for chainctl auth"
        )

    def delete_password(self, service, username):
        """Deleting passwords is not supported."""
        raise NotImplementedError(
            "Deleting passwords is not supported for chainctl auth"
        )

    def get_credential(self, service, username):
        """Get credential object for the service."""
        if not self._is_cgr_dev_service(service):
            return None

        # Check cache for credentials
        if service in self._credentials_cache:
            cached_token = self._credentials_cache[service]
            # Return credentials with the username from chainctl
            return credentials.SimpleCredential("_token", cached_token)

        # If not cached, fetch via get_password (which will cache it)
        password = self.get_password(service, username)
        if password and service in self._credentials_cache:
            cached_token = self._credentials_cache[service]
            return credentials.SimpleCredential("_token", cached_token)

        return None
