from __future__ import annotations

from halludomainbench.legacy_cli import run_legacy_verify


def main() -> int:
    return run_legacy_verify()


if __name__ == "__main__":
    raise SystemExit(main())
