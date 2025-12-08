"""Tests for the chainctl keyring backend."""

import subprocess
from unittest.mock import Mock, patch

import pytest
from keyring import credentials

from keyrings.chainctl_auth import ChainctlAuth


class TestChainctlAuth:
    """Test cases for ChainctlAuth keyring backend."""

    def setup_method(self):
        """Set up test fixtures."""
        self.backend = ChainctlAuth()
        # Clear any cached credentials
        self.backend._credentials_cache = {}

    def test_priority(self):
        """Test that the backend has the correct priority."""
        assert self.backend.priority == 9

    def test_cgr_dev_service_validation(self):
        """Test _is_cgr_dev_service method."""
        # Valid cgr.dev URLs
        assert self.backend._is_cgr_dev_service("https://libraries.cgr.dev") is True
        assert self.backend._is_cgr_dev_service("https://foo.cgr.dev/path") is True
        assert (
            self.backend._is_cgr_dev_service("https://subdomain.libraries.cgr.dev")
            is True
        )

        # Invalid URLs
        assert self.backend._is_cgr_dev_service("http://libraries.cgr.dev") is False
        assert self.backend._is_cgr_dev_service("https://example.com") is False
        assert self.backend._is_cgr_dev_service("https://cgr.dev.fake.com") is False
        assert self.backend._is_cgr_dev_service("ftp://libraries.cgr.dev") is False

    def test_get_password_non_cgr_dev(self):
        """Test get_password returns None for non-cgr.dev domains."""
        assert self.backend.get_password("https://pypi.org", "user") is None
        assert self.backend.get_password("http://libraries.cgr.dev", "user") is None

    @patch("subprocess.run")
    def test_get_password_success(self, mock_run):
        """Test successful password retrieval."""
        # Mock subprocess output
        mock_run.return_value = Mock(
            stdout="token\n",
            stderr=(
                "Opening browser to "
                "https://issuer.enforce.dev/oauth?audience=libraries.cgr.dev\n"
            ),
            returncode=0,
        )

        password = self.backend.get_password("https://libraries.cgr.dev", "user")
        assert password == "token"
        # Verify the command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == [
            "chainctl",
            "auth",
            "token",
            "--audience=libraries.cgr.dev",
        ]

    @patch("subprocess.run")
    def test_get_password_caching(self, mock_run):
        """Test that credentials are cached after first retrieval."""
        mock_run.return_value = Mock(
            stdout="token\n",
            stderr=(
                "Opening browser to "
                "https://issuer.enforce.dev/oauth?audience=libraries.cgr.dev\n"
            ),
            returncode=0,
        )

        service = "https://libraries.cgr.dev"
        # First call
        password1 = self.backend.get_password(service, "user")
        # Second call should use cache
        password2 = self.backend.get_password(service, "user")

        assert password1 == "token"
        assert password2 == "token"
        # Should only call subprocess once due to caching
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_password_command_failure(self, mock_run):
        """Test handling of chainctl command failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["chainctl"], stderr="Error: authentication failed"
        )

        password = self.backend.get_password("https://libraries.cgr.dev", "user")

        assert password is None

    @patch("subprocess.run")
    def test_get_password_command_not_found(self, mock_run):
        """Test handling when chainctl is not installed."""
        mock_run.side_effect = FileNotFoundError("chainctl not found")

        password = self.backend.get_password("https://libraries.cgr.dev", "user")

        assert password is None

    @patch("subprocess.run")
    def test_get_password_empty(self, mock_run):
        """Test handling of empty chainctl output."""
        mock_run.return_value = Mock(
            stdout="",
            stderr=(
                "Opening browser to "
                "https://issuer.enforce.dev/oauth?audience=libraries.cgr.dev\n"
            ),
            returncode=0,
        )

        password = self.backend.get_password("https://libraries.cgr.dev", "user")

        assert password is None

    def test_set_password_not_implemented(self):
        """Test that set_password raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.backend.set_password("https://libraries.cgr.dev", "user", "pass")

    def test_delete_password_not_implemented(self):
        """Test that delete_password raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            self.backend.delete_password("https://libraries.cgr.dev", "user")

    @patch("subprocess.run")
    def test_get_credential_success(self, mock_run):
        """Test successful credential retrieval."""
        mock_run.return_value = Mock(
            stdout="token\n",
            stderr=(
                "Opening browser to "
                "https://issuer.enforce.dev/oauth?audience=libraries.cgr.dev\n"
            ),
            returncode=0,
        )

        cred = self.backend.get_credential("https://libraries.cgr.dev", "user")

        assert isinstance(cred, credentials.SimpleCredential)
        assert cred.username == "_token"
        assert cred.password == "token"

    def test_get_credential_non_cgr_dev(self):
        """Test get_credential returns None for non-cgr.dev domains."""
        assert self.backend.get_credential("https://pypi.org", "user") is None
