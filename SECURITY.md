# Security Policy

## Supported Versions

Abib is a desktop application that is distributed as a single downloadable
build. Only the **latest released version** receives security fixes. Please
make sure you are on the newest release before reporting an issue.

| Version        | Supported          |
| -------------- | ------------------ |
| Latest release | :white_check_mark: |
| Older releases | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
pull requests, or discussions.**

Instead, use GitHub's **Private Vulnerability Reporting**:

1. Go to this repository's **Security** tab.
2. Click **"Report a vulnerability"**.
3. Fill in the advisory form.

This keeps the report private until a fix is released. If Private Vulnerability
Reporting is not available for you, please contact the maintainers privately
through the repository owner's GitHub profile rather than opening a public
issue.

When reporting, please include as much of the following as you can:

- A description of the vulnerability and its impact.
- The Abib version and operating system (Windows / macOS / Linux) you tested.
- Step-by-step instructions to reproduce the issue (and a proof of concept if
  possible).
- Any relevant logs, screenshots, or crash output.

## What to Expect

- **Acknowledgement:** we aim to acknowledge your report within **3 business
  days**.
- **Assessment:** we will investigate and let you know whether the report is
  accepted, needs more information, or is out of scope.
- **Fix & disclosure:** valid issues will be fixed in a new release; we will
  coordinate a disclosure timeline with you and credit you if you wish.

## Scope

This policy covers the Abib application code in this repository. Note that Abib
bundles third-party materials (e.g. the Pure Cambridge Edition of the KJV and
Spurgeon resources) and depends on third-party Python packages (PySide6,
requests, certifi, etc.). Vulnerabilities in those upstream projects should be
reported to their respective maintainers; we will update our pinned
dependencies when fixes become available.
