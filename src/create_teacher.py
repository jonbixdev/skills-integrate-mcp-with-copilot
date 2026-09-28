import getpass
import hashlib
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path


TEACHERS_FILE = Path(__file__).with_name("teachers.json")
PASSWORD_HASH_ITERATIONS = 600_000


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print(f"Usage: python {Path(sys.argv[0]).name} <username>", file=sys.stderr)
        return 2

    username = sys.argv[1].strip()
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"teachers": []}
    except (OSError, json.JSONDecodeError) as error:
        print(f"Could not read teacher credentials: {error}", file=sys.stderr)
        return 1

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        print("Teacher credentials must contain a teachers list.", file=sys.stderr)
        return 1
    if any(
        isinstance(teacher, dict) and teacher.get("username") == username
        for teacher in teachers
    ):
        print(f"Teacher account {username!r} already exists.", file=sys.stderr)
        return 1

    password = getpass.getpass("Teacher password (at least 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 1
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    teachers.append(
        {
            "username": username,
            "salt": salt.hex(),
            "password_hash": password_hash.hex(),
        }
    )

    TEACHERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=TEACHERS_FILE.parent,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump({"teachers": teachers}, temporary_file, indent=2)
            temporary_file.write("\n")
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(TEACHERS_FILE)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    print(f"Created teacher account {username!r}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())