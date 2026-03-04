from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def detect_platform(url: str) -> str | None:
    netloc = urlparse(url).netloc.lower()
    if "instagram.com" in netloc:
        return "instagram"
    return None


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    platform = detect_platform(url)
    query = parse_qsl(parsed.query, keep_blank_values=False)

    if platform == "instagram":
        # Drop tracking/share params that often break extraction stability.
        query = []

    clean_path = parsed.path.rstrip("/") or parsed.path
    new_query = urlencode(query, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", new_query, ""))
