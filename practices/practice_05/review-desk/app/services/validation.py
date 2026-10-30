def clean_text(value: str | None, max_length: int, label: str) -> tuple[str, str | None]:
    """strip() и проверка длины 1..max_length. Возвращает (значение, ошибка)."""
    cleaned = (value or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return cleaned, f"{label}: поле не может быть пустым"
    if len(cleaned) > max_length:
        return cleaned, f"{label}: не длиннее {max_length:,} символов (сейчас {len(cleaned):,})".replace(",", " ")
    return cleaned, None


# Границы SQLite INTEGER (знаковое 64-битное целое): за ними db.get упал бы
# с OverflowError (500) вместо обычного "строки нет" (404).
SQLITE_INT_MIN = -(2**63)
SQLITE_INT_MAX = 2**63 - 1


def fits_sqlite_int(value: int) -> bool:
    return SQLITE_INT_MIN <= value <= SQLITE_INT_MAX
