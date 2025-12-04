# keyrings-chainguard-libraries

Keyring backend for Chainguard Python Libraries

A Python keyring backend that provides seamless authentication to internal PyPI repositories using Chainguard's `chainctl` pull tokens.

## Overview

This package extends Python's keyring library to automatically authenticate with private package repositories using `chainctl` pull tokens. When pip or other Python package managers request credentials for HTTPS repositories ending with `.cgr.dev`, this backend generates short-lived authentication tokens using the `chainctl` CLI tool.

## Features

- **Automatic Authentication**: Seamlessly integrates with pip, poetry, and other Python package managers
- **Token Caching**: Caches credentials to minimize repeated `chainctl` calls
- **Secure Token Generation**: Uses `chainctl` to generate short-lived (8-hour) pull tokens
- **Tox Integration**: Includes a tox plugin for authentication in test environments

## Installation

```bash
pip install keyrings-chainguard-libraries
```

## Prerequisites

- Python 3.7 or higher
- `chainctl` CLI tool installed and configured

## Usage

Once installed, the keyring backend will automatically activate for HTTPS URLs ending with `.cgr.dev`. When pip or other tools request credentials for a private repository on a `*.cgr.dev` domain, the backend will:

1. Check if credentials are cached
2. If not cached, run `chainctl auth pull-token` to generate new credentials
3. Return the credentials to the requesting tool

### Example with pip

```bash
# Install from a private Chainguard repository
pip install package-name --index-url https://libraries.cgr.dev/python/simple/
```

### Manual Testing

You can test the keyring backend directly:

```python
import keyring
from keyrings.chainctl_auth import ChainctlAuth

# Set the backend
keyring.set_keyring(ChainctlAuth())

# Get credentials for a Chainguard service
password = keyring.get_password("https://libraries.cgr.dev", "username")
```

## How It Works

The `ChainctlAuth` backend:

1. Intercepts credential requests for HTTPS services ending with `.cgr.dev`
2. Executes `chainctl auth token --audience=libraries.cgr.dev`
3. Caches the token for the service
5. Returns the token to the requesting application

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/chainguard-dev/keyrings-chainguard-libraries
cd keyrings-chainguard-libraries

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=keyrings.chainctl_auth

# Run linting
flake8
mypy keyrings/
```

### Building

```bash
# Build the package
python -m build
```

### Committing

This repo uses [`pre-commit`](https://pre-commit.com/) to run pre-commit hooks.

```bash
pre-commit install
```

To run at any time:

```bash
pre-commit run --all-files
```

## Troubleshooting

### Common Issues

1. **"chainctl command not found"**
   - Ensure `chainctl` is installed and available in your PATH

2. **Authentication failures**
   - Verify `chainctl` is properly configured and authenticated
   - Check that your organization has access to Chainguard Libraries

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- Credentials are cached in memory only for the duration of the process
- Pull tokens are generated with an 8-hour TTL
- The backend only handles HTTPS URLs for domains ending with `.cgr.dev` to ensure secure transmission

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues and questions:
- Open an issue on the [GitHub repository](https://github.com/chainguard-dev/keyrings-chainguard-libraries)
- Contact the maintainers
