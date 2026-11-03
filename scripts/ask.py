"""Setup helper: ask the assistant a question from the terminal, without Alexa.

Uses the same code and lambda/config.json as the skill, so it is the quickest way to
check that Moodle and the LLM are configured before deploying.

Usage:  python3 scripts/ask.py "o que tenho amanhã?"
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lambda"))

from assistant.skill import assistant_from_config  # noqa: E402 (needs the path above)


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/ask.py "o que tenho amanhã?"')
        return 1
    question = " ".join(sys.argv[1:])
    started = time.monotonic()
    answer = assistant_from_config().answer(question)
    print(answer)
    print(f"\n({time.monotonic() - started:.1f} s; Alexa allows about 8 s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
