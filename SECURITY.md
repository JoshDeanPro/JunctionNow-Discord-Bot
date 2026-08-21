# Security

## Never Commit Secrets

Do not commit:

- Discord bot tokens
- Discord webhook secrets
- passwords
- private keys
- `.env` files
- personal server details
- private IP or host details when they are not needed

Use environment variables for secrets.

Use `.env.example` only to show which settings exist.

## If a Secret Is Exposed

Do not only delete the file.

A secret may still exist in Git history.

First:

1. Revoke or rotate the secret.
2. Remove it from the project.
3. Check Git history.
4. Rewrite history only when needed.

Treat an exposed secret as unsafe even if the repository is private.

## Report a Security Problem

Do not place real secrets in a GitHub issue.

Explain the problem without including the secret itself.
