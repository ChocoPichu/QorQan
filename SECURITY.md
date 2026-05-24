# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in QorQan, please report it by email to **albert.akhylbekov@gmail.com**.

We will acknowledge receipt within 48 hours and work on a fix. Please do not disclose vulnerabilities publicly until they have been addressed.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |

## Security Best Practices

- Never commit `.env` or `TOKENS.txt` to the repository
- Change the default operator passwords in `admins.json` before deployment
- Use HTTPS when deploying the dashboard in production
- Regularly backup `qorqan.db` for auditing purposes