# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| latest  | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please send a description of the vulnerability to the repository maintainers via email or through GitHub's private vulnerability reporting feature:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Provide a detailed description including steps to reproduce.

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Practices

This project follows these security practices:

- **No secrets in code**: All credentials are loaded from environment variables; the `.env` file is excluded from version control via `.gitignore`.
- **Parameterized queries**: Cosmos DB queries use parameterized values to prevent injection.
- **Path traversal prevention**: File system operations use `os.path.realpath()` to resolve symlinks and validate all paths stay within the target directory.
- **Sandboxed report rendering**: The HTML report is rendered in a sandboxed `<iframe>` with `sandbox="allow-same-origin"` to prevent script execution.
- **CORS configuration**: CORS should be restricted to known origins in production deployments.
- **Container security**: The Docker image uses `python:3.12-slim` as a minimal base and does not run as root by default in Azure Container Apps.
- **Azure authentication**: Uses `DefaultAzureCredential` which supports managed identity in production, avoiding key-based auth for Azure OpenAI.
