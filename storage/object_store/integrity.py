import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def calculate_sha256(file_path: Path) -> str:
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    checksum = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            checksum.update(chunk)

    return checksum.hexdigest()


def verify_checksum(
    file_path: Path,
    expected_checksum: str,
) -> bool:
    actual_checksum = calculate_sha256(file_path)

    return actual_checksum.lower() == expected_checksum.lower()
