 ▐▛███▛█   Claude Code v2.1.312
▝▜██████▀  Sonnet 5 · Claude Pro
 ▝▝   ▝▝   ~/ITMOv2/practices/practice_05/review-desk


❯ Ты - независимый ревьюер спецификации. Изменение уже спроектировано другим    
  агентом; твоя задача - найти в нём ошибки до того, как по нему напишут код.   
  Ничего не меняй и не создавай, только читай и отвечай.                        
                                                                                
  Что ревьюим: openspec/changes/review-queue-task-filter/ (proposal.md,         
  specs/review-queue/spec.md, design.md, tasks.md).                             
  Требования заказчика (главнее всего остального):                              
  course/practice-05/01-decisions.md.                                           
  Правила и текущее поведение: AGENTS.md, docs/baseline.md,                     
  docs/architecture.md,                                                         
  код в app/ и тесты в tests/. Переписку, в которой создавалось изменение,      
  не ищи и не читай - оцениваем только артефакты.                               
                                                                                
  Проверь:                                                                      
  1. Соответствие решениям: каждое решение Q1-Q8 и B отражено в спеке, нигде    
  нет                                                                           
     противоречия или молчаливого отступления.                                  
  2. Проверяемость: каждое требование RQF-N однозначно, сценарий WHEN/THEN      
  можно                                                                         
     превратить в тест без догадок (конкретные URL, коды ответов, тексты).      
  3. Противоречия между артефактами: proposal vs spec vs design vs tasks.       
  4. Противоречия с кодом и baseline: какие существующие тесты сломаются, если  
     реализовать ровно по спеке (проверь по tests/test_us4_review.py и          
     tests/test_us5_my_attempts.py), и что в design не сходится с реальными     
     сигнатурами и импортами в app/.                                            
  5. Пропущенные границы и ошибки: значения параметра, порядок проверок         
     (аноним / студент / ментор), open redirect, экранирование, пустые          
  состояния,                                                                    
     409/404 после POST.                                                        
  6. tasks.md: порядок "тест -> падение -> реализация" соблюдён, у каждой       
  задачи                                                                        
     есть проверка, ничего не требует трогать docs/baseline.md,                 
  scripts/check.sh                                                              
     или добавлять зависимости.                                                 
  7. Запусти openspec validate review-queue-task-filter --strict и              
     openspec status --change review-queue-task-filter, приложи вывод.          
                                                                                
  Формат ответа:                                                                
  - Таблица замечаний: id (R1, R2...), серьёзность (blocker / major / minor),   
    файл и место, что не так, почему это проблема, предлагаемая правка.         
  - Отдельно: что проверено и замечаний не дало (одной строкой на пункт 1-6).   
  - Вердикт: можно ли запускать apply после правок blocker и major.             
    Не выдумывай замечаний ради количества: если пункт чист, так и напиши.      

● I'll review the spec artifacts against the decisions, code, and baseline. Let
  me gather everything first.

  Read 1 file (ctrl+o to expand)

● Now let me check the baseline/US4/US5 tests and the submissions service
  (get_submission_for) for role-check ordering.

  Read 4 files, ran 3 shell commands (ctrl+o to expand)

● Результат ревью спецификации review-queue-task-filter

  Запуски

  $ openspec validate review-queue-task-filter --strict
  Change 'review-queue-task-filter' is valid

  $ openspec status --change review-queue-task-filter
  Change: review-queue-task-filter
  Schema: spec-driven
  Progress: 4/4 artifacts complete
  [x] proposal  [x] specs  [x] design  [x] tasks
  All planning artifacts complete!

  Таблица замечаний

  id: R1
  серьёзность: minor
  файл / место: proposal.md, раздел Impact: «app/web/review.py (параметр
  /review,
  скрытое поле в POST, сборка URL)»
  что не так: Proposal приписывает сборку URL (review_queue_url) файлу
  app/web/review.py. Но design.md (D4) и tasks.md (4.2) явно и обоснованно (во
  избежание циклического импорта: review.py уже импортирует render_submission
  из submissions.py) размещают хелпер в app/web/submissions.py; review.py
  только импортирует и вызывает его. Это подтверждается и реальным кодом
  (app/web/review.py импортирует render_submission из app.web.submissions).
  почему это проблема: Формальное противоречие между proposal и design/tasks (п.

  3 чек-листа). Риск для реализации низкий — исполнитель идёт по tasks.md, где
  всё верно, — но несостыковка мешает использовать proposal как достоверную
  карту изменений.
  предлагаемая правка: В Impact-разделе proposal.md уточнить: «app/web/review.py

  (параметр /review, скрытое поле в POST) ... app/web/submissions.py
  (render_submission, страница сдачи, хелпер review_queue_url — сборка URL)».

  Других расхождений, нарушений границ или пропущенных кейсов не найдено — см.
  ниже по пунктам.

  Что проверено и чисто

  1. Соответствие Q1–Q8 и B: все восемь решений и находка B однозначно отражены
     — единый 404 (Q1), регекс/границы/повтор параметра (Q2), порядок 403→разбор
     (Q3), слой сервиса + сборка URL из проверенного id (Q4), мягкая передача
     через ?assignment_id= только при активном фильтре + потеря фильтра на
     409/404 (Q5), форма/заголовок/«Сбросить фильтр» (Q6), имя параметра
     assignment_id (Q7), текст ошибки (Q8), баг B вынесен в «Вне рамок» и явно
     не повторяется новым парсером. Противоречий или тихих отступлений нет.
  2. Проверяемость RQF-N: все 12 требований и сценарии S1–S20 дают конкретные
     URL/коды/тексты (404 «Задача не найдена», 303 Location: /review /
     /review?assignment_id=<N>, точные href-паттерны, конкретный список
     невалидных значений в S7b/S17). Тест можно написать без догадок.
  3. Противоречия между артефактами: кроме R1 — чисто. Proposal, spec, design и
     tasks говорят об одном и том же поведении; design.md и tasks.md взаимно
     согласованы (сигнатуры, порядок вызовов, список тестов и сценариев).
  4. Противоречия с кодом/baseline: проверено по tests/test_us4_review.py и
     tests/test_us5_my_attempts.py — ни один актуальный ассерт не ломается
     (пустая очередь без фильтра не содержит /submissions/, href без фильтра
     совпадает с прежним, Location: /review без скрытого поля, студенческие и
     ментор-сценарии не меняются). Сигнатуры pending_queue, render_submission,
     get_assignment, импорты в review.py/submissions.py — design D3–D5 совпадают
     с реальным кодом. Эмпирически перепроверено поведение FastAPI/Starlette
     для повторного query-параметра (str | None, не list) — действительно
     возвращается последнее значение, как требует Q2/S8.
  5. Границы и ошибки: порядок анон→403→разбор (RQF-5/S9/S10) корректен через
     Depends(require_mentor), выполняющийся раньше тела роута; open redirect
     невозможен (review_queue_url строит URL только из Assignment.id: int);
     экранирование названия задачи через стандартный autoescape Jinja2 без
     |safe; пустые состояния (S4/S5) разведены; 409/404 после POST — осознанно
     теряют фильтр (RQF-11), задокументировано. Граница 2^63-1 проверяется до
     обращения к БД, что исключает OverflowError (находка B не повторяется).
  6. tasks.md: порядок «тест → показать падение → минимальная реализация»
     соблюдён во всех секциях (2→5), у каждой задачи реализации есть шаг
     «Проверка:», ничего не требует трогать
     docs/baseline.md/scripts/check.sh/зависимости (явно проверяется в 6.2).
     Корректно и точно указано, какие сценарии уже проходят сейчас «бесплатно»
     (S3, S9, S10, S14/S14b/S14c, S16, S17, S18b) и какие должны упасть до
     реализации (S1, S6–S8, S13/S13b, S15, S18, S19) — я перепроверил это по
     текущему коду, расхождений не нашёл.

  Вердикт

  Блокеров и major-замечаний нет. Единственное замечание R1 — minor и
  косметическое (несостыковка в описательном разделе proposal, не влияющая на
  то, что фактически будет реализовано по tasks.md/design.md). Можно запускать 
  openspec apply без правок; R1 стоит поправить по ходу или заодно, но ждать
  этого не обязательно.

✻ Brewed for 6m 14s · done 12:57 AM

※ recap: Independent review of the review-queue-task-filter OpenSpec change found no blockers or majors, just one minor proposal/design file-attribution mismatch. Next: optionally fix that one-line note in proposal.md, then apply is clear to run. (disable recaps in /config)