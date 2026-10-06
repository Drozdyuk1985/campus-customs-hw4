"""Privacy filter for customer text, enforced in code (not left to the model).

redact() runs on every chat message before it is sent to the model, kept in
guest memory or saved to chat history, and (through audit.scrub) on every
string written to the audit trail.

What it removes:
- Card-like numbers: 13-19 digits, optionally separated by spaces or dashes.
- Explicitly shared credentials: a credential word followed by a value. The
  credential words are password, passcode, PIN, card code (CVV/CVC/CVV2),
  API key, access key, secret, token, OTP and verification code. A value
  counts when it comes after a connector ("is", "was", ":", "=", "-") or
  directly after the word if it looks like a secret (it contains a digit or
  symbol and is at least 4 characters). Quoted values are removed whole.
- Values that look like secrets anywhere: "sk-..." API-key style strings and
  PBKDF2 password hashes.

What it can't do: it recognises these patterns only. A password typed with
no cue ("here you go: Tr0ub4dor"), a secret split over several messages, or
personal details such as an address are not detected. See output/harness.md.
"""

import re

CARD_PLACEHOLDER = "[card number removed]"
SECRET_PLACEHOLDER = "[credential removed]"

# 13-19 digits, optionally separated by spaces or dashes.
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")

_CRED_WORD = (
    r"(?:pass(?:word|wd|code|phrase)|pwd|\bpw\b|\bpin(?:\s*(?:code|number))?\b|"
    r"\bcvv2?\b|\bcvc\b|security\s+code|verification\s+code|one[- ]time\s+code|\botp\b|"
    r"api[\s_-]?key|access[\s_-]?key|secret(?:[\s_-]?key)?|(?:auth|access|session|bearer)?[\s_-]?token)"
)
# "<word> is/was/:/=/- <value>"  (value may be quoted)
_CRED_WITH_CONNECTOR = re.compile(
    rf"(?P<lead>{_CRED_WORD}\s*(?:\bis\b|\bwas\b|:|=|-)\s*)(?P<value>\"[^\"]+\"|'[^']+'|“[^”]+”|\S+)",
    re.IGNORECASE,
)
# "<word> <value>" with no connector: only when the value looks like a secret
_CRED_BARE = re.compile(
    rf"(?P<lead>{_CRED_WORD}\s+)(?P<value>(?=\S*[\d!@#$%^&*_+=?~])\S{{4,}})",
    re.IGNORECASE,
)
_SECRET_LOOKING = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}|pbkdf2_sha256\$\S+", re.IGNORECASE)


def _strip_punct(value: str) -> tuple[str, str]:
    """Keep sentence punctuation (", . ;") outside the removed value."""
    m = re.match(r"^(.*?)([.,;)]*)$", value, re.S)
    return (m.group(1), m.group(2)) if m and m.group(1) else (value, "")


def _replace(m: re.Match) -> str:
    value, tail = _strip_punct(m.group("value"))
    if not value or value.startswith("["):  # already redacted
        return m.group(0)
    return m.group("lead") + SECRET_PLACEHOLDER + tail


def redact(text: str) -> str:
    """Remove card numbers and explicitly shared credentials from customer text."""
    if not text:
        return text
    text = _CARD.sub(CARD_PLACEHOLDER, text)
    text = _SECRET_LOOKING.sub(SECRET_PLACEHOLDER, text)
    text = _CRED_WITH_CONNECTOR.sub(_replace, text)
    text = _CRED_BARE.sub(_replace, text)
    return text


def redact_deep(value):
    """Apply redact() to every string inside nested dicts and lists (keys are left as they are)."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: redact_deep(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_deep(v) for v in value]
    return value
