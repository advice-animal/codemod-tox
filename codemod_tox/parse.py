import re

TOX_ENV_TOKEN_RE = re.compile(
    r"(?P<comma>,[ \t]*)|(?P<newline>\n)|(?P<space>[ \t]+)|(?P<literal>[A-Za-z0-9-_]+)|(?P<options>\{[^{}\s]+\})"
)
PY_FACTOR_RE = re.compile(r"^py(3\d+)")
