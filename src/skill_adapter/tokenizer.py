import re
from typing import List

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*|[\u4e00-\u9fff]+")


def tokenize_text(text: str) -> List[str]:
    tokens: List[str] = []
    for chunk in _TOKEN_PATTERN.findall(text or ""):
        if re.fullmatch(r"[A-Za-z0-9_]+(?:['-][A-Za-z0-9_]+)*", chunk):
            tokens.append(chunk.lower())
            continue

        chunk = chunk.strip()
        if not chunk:
            continue

        if len(chunk) == 1:
            tokens.append(chunk)
            continue

        tokens.extend(char for char in chunk if char.strip())
        tokens.extend(chunk[idx : idx + 2] for idx in range(len(chunk) - 1))
        tokens.append(chunk)
    return tokens
