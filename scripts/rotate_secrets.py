import os
import secrets
from pathlib import Path


def replace_or_add(lines: list[str], key: str, value: str) -> list[str]:
    prefix = f"{key}="
    if any(line.startswith(prefix) for line in lines):
        return [f"{prefix}{value}\n" if line.startswith(prefix) else line for line in lines]
    return [*lines, f"{prefix}{value}\n"]


def main() -> None:
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = replace_or_add(lines, "APP_SECRET_KEY", secrets.token_urlsafe(48))
    lines = replace_or_add(lines, "LMS_KEY_PEPPER", secrets.token_urlsafe(48))
    env_path.write_text("".join(lines), encoding="utf-8")
    os.chmod(env_path, 0o600)
    print("APP_SECRET_KEY и LMS_KEY_PEPPER обновлены; .env защищён правами 0600")


if __name__ == "__main__":
    main()
