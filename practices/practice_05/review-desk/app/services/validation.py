def clean_text(value: str | None, max_length: int, label: str) -> tuple[str, str | None]:
    """strip() и проверка длины 1..max_length. Возвращает (значение, ошибка)."""
    cleaned = (value or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return cleaned, f"{label}: поле не может быть пустым"
    if len(cleaned) > max_length:
        return cleaned, f"{label}: не длиннее {max_length:,} символов (сейчас {len(cleaned):,})".replace(",", " ")
    return cleaned, None
