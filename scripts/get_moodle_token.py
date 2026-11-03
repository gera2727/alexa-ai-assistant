"""Setup helper: get your personal Moodle Web Service token and save it in lambda/config.json.

Uses the same service as the official Moodle mobile app (`moodle_mobile_app`).
Your password is typed locally, sent only to Moodle over HTTPS (in the request
body, never in the URL), and never stored or printed.

Usage:  python3 scripts/get_moodle_token.py
"""

import getpass
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "lambda" / "config.json"


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    url = config.get("moodle_url", "https://moodle.isep.ipp.pt").rstrip("/")
    if not url.startswith("https://"):
        print("moodle_url must use https://")
        return 1

    username = input(f"Moodle username for {url}: ").strip()
    password = getpass.getpass("Password (not shown): ")

    body = urllib.parse.urlencode({"username": username, "password": password, "service": "moodle_mobile_app"})
    request = urllib.request.Request(f"{url}/login/token.php", data=body.encode())  # noqa: S310 (https checked above)
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        result = json.load(response)

    if "token" not in result:
        print("Moodle did not return a token:", result.get("errorcode"), "-", result.get("error"))
        print("Use the same username and password as the Moodle app (the username is usually not an email).")
        return 1

    config["moodle_token"] = result["token"]
    CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Token saved to lambda/config.json (git-ignored). It was not printed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
