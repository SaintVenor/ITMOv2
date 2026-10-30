# Specification Quality Checklist: Построчные комментарии ментора — данные и правила

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-30
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No unresolved-question markers remain (0 осталось: FR-016 и FR-017 сняты на шаге clarify)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Перепроверено против спеки, приведённой к общему контракту `specs/line-comments-contract.md`: все пункты по-прежнему выполнены; открытых вопросов не осталось (0): FR-016 (статусы сдачи — любой) и FR-017 (видимость ученику — сразу) сняты на шаге clarify, см. раздел Clarifications в spec.md.
- FR-003 переписан через `split_code_lines` (LC-04), FR-005 - через правила разбора номера (LC-15), FR-006 - лимит `LINE_COMMENT_MAX` (LC-06), FR-018 - маршрут, фильтр очереди и контекст (LC-09…LC-13); пустой код и одиночный `\r` добавлены в Edge Cases.
- Упоминания `\n`, `\r\n`, 403/404/400 и id вне диапазона SQLite — ссылки на уже действующее поведение (baseline, `openspec/specs/path-id-bounds`), а не выбор реализации.
- Общий контракт `specs/line-comments-contract.md` записан и указан в Assumptions; он главнее спеки.
