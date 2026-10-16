# Замер скорости itmo-agent (qwen3.5:4b, ctx 65536)

Промпт: "Напиши одно короткое предложение про тестирование."
Опции: num_ctx=65536, seed=42, think=false.

## 1) Холодный старт
- load_duration: 5.1276964 с (5127696400 нс)
- total_duration: 5.696566335 с (5696566335 нс)

## 2) Подтверждение прогрева
- Модель загружена: `ollama ps` показывает itmo-agent 100% GPU, CONTEXT 65536 (07-speed.txt).
- Первый прогретый запрос (warm0) total_duration: 0.865342262 с. Он считается прогревом и в повторы не входит.

## 3) Повторы (прогретые), пересчёт по исходным JSON — 07-speed-recalc.txt, часть A
- warm1: eval_count=26, eval_duration=0.445038 с → 58.42 tok/s
- warm2: eval_count=26, eval_duration=0.457401 с → 56.84 tok/s
- warm3: запрос упал — `option "seed" must be of type integer` (speed-raw/ollama_gen_warm3.json); повторён как warm3_fix
- warm3_fix: eval_count=26, eval_duration=0.468571 с → 55.49 tok/s

Медиана tokens/sec по 3 повторам (warm1, warm2, warm3_fix): 56.84.
Исправление: в прошлой версии повторами ошибочно считались warm0–warm2, а tok/s были округлены неверно (56.96 / 58.44 / 56.85, медиана 56.96).

## 4) Режим агента (thinking включён) — 07-speed-recalc.txt, часть B
Замер выше сделан с think=false, а агентные прогоны шли с thinking (у itmo-agent `thinking default true`).
Тот же промпт без поля think, stream=false, 4 запроса (run0 — прогрев):
- eval_count=3985 в каждом из 4 запросов (длина thinking 15046 символов); total_duration повторов 72.9–73.8 с, прогрева 72.5 с
- tokens/sec повторов run1–run3: 54.63, 54.75, 54.09; медиана 54.63
Вывод: скорость декодирования почти та же, но в режиме thinking на одно короткое предложение уходит ~4 тыс. токенов и ~73 с.

## 5) Исходные JSON
- results/speed-raw/ollama_gen_{cold,warm0,warm1,warm2,warm3,warm3_fix}.json — замер с think=false
- results/speed-raw/thinking-default/run{0..3}.json и ollama-ps.txt — замер в режиме thinking
- results/speed-raw/recalc.py — пересчёт: `python3 speed-raw/recalc.py speed-raw <файлы>`

Примечание: метрики TTFT без потокового времени не заявляются; оцениваем только суммарные длительности и скорость декодирования по eval_count/eval_duration.
