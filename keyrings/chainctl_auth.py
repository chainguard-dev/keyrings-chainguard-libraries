"""
Chainctl Keyring Backend for Python Package Repositories

This module provides a keyring backend that authenticates to internal PyPI
repositories using chainctl pull tokens.
"""

import os
import json
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
        """Get password (pull token) for the given service."""
        if not self._is_cgr_dev_service(service):
            return None

        # Check cache first
        if service in self._credentials_cache:
            cached_creds = self._credentials_cache[service]
            # Return the password part of the credentials
            return cached_creds[1]

        # Get parent from environment variable
        parent = os.environ.get("CHAINCTL_PARENT", "")
        if not parent:
            self._logger.warning("CHAINCTL_PARENT environment variable not set")
            return None

        try:
            # Fetch pull token using chainctl (returns username, password tuple)
            credentials = self._get_chainctl_token(parent)
            if credentials:
                # Cache the credentials
                self._credentials_cache[service] = credentials
                # Return just the password
                return credentials[1]
        except Exception as e:
            self._logger.error(f"Failed to get chainctl pull token: {e}")

        return None

    def _get_chainctl_token(self, parent):
        """Execute chainctl command to get pull token."""
        try:
            # Build the chainctl command
            cmd = [
                "chainctl",
                "auth",
                "pull-token",
                "--library-ecosystem=python",
                f"--parent={parent}",
                "--ttl=8h",
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

            # Parse the output to extract username and password
            output_lines = result.stdout.strip().split("\n")
            username = None
            password = None

            for i, line in enumerate(output_lines):
                if line.startswith("Username:"):
                    username = line.split(":", 1)[1].strip()
                elif line.startswith("Password:"):
                    password = line.split(":", 1)[1].strip()

            if not username or not password:
                self._logger.error(f"Failed to parse chainctl output:\n{result.stdout}")
                raise Exception(
                    "Unable to parse username and password from chainctl output"
                )

            # Return the credentials as a tuple
            return (username, password)

        except subprocess.CalledProcessError as e:
            self._logger.error(f"chainctl command failed: {e.stderr}")
            raise Exception(
                f"chainctl command exited with status {e.returncode}: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise Exception("chainctl command timed out")
        except FileNotFoundError:
            raise Exception(
                "chainctl command not found. Please ensure chainctl is installed and in PATH"
            )

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
            cached_creds = self._credentials_cache[service]
            # Return credentials with the username from chainctl
            return credentials.SimpleCredential(cached_creds[0], cached_creds[1])

        # If not cached, fetch via get_password (which will cache it)
        password = self.get_password(service, username)
        if password and service in self._credentials_cache:
            cached_creds = self._credentials_cache[service]
            return credentials.SimpleCredential(cached_creds[0], cached_creds[1])

        return None
