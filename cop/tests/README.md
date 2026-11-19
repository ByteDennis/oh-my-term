# Local verification

These tests use a local mock chat page and temporary browser profiles. They do
not sign in to Microsoft or establish real Copilot compatibility.

```bash
python -m pip install playwright prompt_toolkit pytest
python -m pytest cop/tests lab/tests -q
```

Chrome on PATH is used for browser tests; otherwise install Chromium with
`python -m playwright install chromium`.

For the Linux terminal/CDP integration test:

```bash
python -m pip install pexpect
python cop/tests/terminal_smoke.py
```

This drives actual terminal keystrokes through chat, multiline editing,
attachments, live output, interruption/recovery, history, export and the GitLab
prompt. `TEST_BROWSER=/path/to/chromium` overrides its browser executable.
Its evidence is written to the repository's ignored `plans/evidence/` directory.
The GitLab workflow tests use real temporary Git repositories and a recording
`glab` substitute, never company repositories or remote pipelines.
