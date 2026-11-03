"""Setup helper: check which Moodle Web Service functions your token can use.

Reads `moodle_url` and `moodle_token` from lambda/config.json (git-ignored)
and prints the site name and the available functions. The token is never printed.

Usage:  python3 scripts/check_moodle_api.py
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "lambda" / "config.json"
INTERESTING = [
    "core_enrol_get_users_courses",
    "core_course_get_contents",
    "core_calendar_get_action_events_by_timesort",
    "mod_assign_get_assignments",
    "gradereport_user_get_grade_items",
    "mod_forum_get_forum_discussions",
]


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    url, token = config.get("moodle_url"), config.get("moodle_token")
    if not url or not token:
        print(f"Add 'moodle_url' and 'moodle_token' to {CONFIG}")
        return 1

    if not url.startswith("https://"):
        print("moodle_url must use https://")
        return 1

    # The token goes in the POST body, never in the URL.
    body = urllib.parse.urlencode(
        {"wstoken": token, "wsfunction": "core_webservice_get_site_info", "moodlewsrestformat": "json"}
    ).encode()
    endpoint = f"{url.rstrip('/')}/webservice/rest/server.php"
    with urllib.request.urlopen(urllib.request.Request(endpoint, data=body), timeout=10) as r:  # noqa: S310
        info = json.load(r)

    if "exception" in info:
        print("Moodle refused the request:", info.get("errorcode"), "-", info.get("message"))
        return 1

    available = {f["name"] for f in info.get("functions", [])}
    print(f"Site: {info.get('sitename')}  |  User: {info.get('fullname')}")
    print(f"Functions available: {len(available)}\n")
    for name in INTERESTING:
        print(("  ✅ " if name in available else "  ❌ ") + name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
