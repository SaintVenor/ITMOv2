summary:
- Добавлен HTTP endpoint POST /api/reviews, который принимает payload с полем diff и проксирует его в сервис обзора.
- В ReviewService добавлен метод review: формирует prompt с сырым diff, вызывает LLM.generate и возвращает {"comment": answer}.
- Незначительное форматное изменение сигнатуры протокола LLM.generate (перенос многоточия на новую строку).
risks:
- file: app/review_service.py, line: 20, evidence: 'prompt = f"Review this pull request and find problems:\n{diff}"', risk: SEC-1 нарушено — сырое содержимое diff передается во внешний LLM без маскирования токенов/паролей/приватных ключей.
- file: app/api.py, line: 37, evidence: 'return review_service.review(payload"diff")', risk: API-1 нарушено — отсутствует проверка длины diff и возврат HTTP 413 для >20 000 символов.
- file: app/review_service.py, line: 21, evidence: 'answer = self.llm.generate(prompt)', risk: REL-1 нарушено — вызов внешнего LLM без таймаута 10 секунд и без контролируемой обработки ошибки.
checks:
- Что сделать: Написать unit‑тест на ReviewService.review с мок‑LLM, передав в diff строки вида '-----BEGIN PRIVATE KEY-----\nABC...' или 'password=SuperSecret123'. -> Что получим: Мок зафиксирует, что секреты прошли в prompt без редакции (подтверждение нарушения SEC-1).
- Что сделать: Вызвать POST /api/reviews с payload, где diff содержит 20001+ символов (например, "A" * 20001). -> Что получим: Ответ не 413 (скорее 200), что подтверждает отсутствие лимита по API-1.
- Что сделать: Заменить LLM на тестовый двойник, который спит >10 секунд или бросает исключение; вызвать ReviewService.review и эндпойнт /api/reviews. -> Что получим: Зависание >10 секунд или проброс/500 вместо контролируемого ответа — нарушение REL-1.
Список рисков:
- Файл app/review_service.py, строки 20 (по TRAINING_PR.diff): SEC-1 — отправка сырых секретов во внешний LLM
Доказательство: 'prompt = f"Review this pull request and find problems:\n{diff}"'
Проверка: Мок LLM с diff, содержащим секреты -> секреты присутствуют в зафиксированном prompt
- Файл app/api.py, строка 37 (по TRAINING_PR.diff): API-1 — нет отклонения слишком длинного diff
Доказательство: 'return review_service.review(payload"diff")'
Проверка: POST /api/reviews с diff > 20000 символов -> статус не 413
- Файл app/review_service.py, строка 21 (по TRAINING_PR.diff): REL-1 — нет таймаута 10с и graceful fallback
Доказательство: 'answer = self.llm.generate(prompt)'
Проверка: Тестовый LLM с задержкой >10с/исключением -> зависание/500 вместо контролируемого ответа