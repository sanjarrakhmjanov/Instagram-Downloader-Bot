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
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] in {"p", "reel", "tv"}:
            clean_path = f"/{path_parts[0]}/{path_parts[1]}"
        else:
            clean_path = parsed.path.rstrip("/") or parsed.path
        new_query = ""
        return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", new_query, ""))

    clean_path = parsed.path.rstrip("/") or parsed.path
    new_query = urlencode(query, doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", new_query, ""))
