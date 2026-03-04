import re


def safe_basename(name: str, fallback: str = "media") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned[:120] or fallback

