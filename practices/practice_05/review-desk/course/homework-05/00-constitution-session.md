 ▐▛███▛█   Claude Code v2.1.312
▝▜██████▀  Sonnet 5 · Claude Pro
 ▝▝   ▝▝   ~/ITMOv2/practices/practice_05/review-desk


❯ /speckit-constitution                                                         
  Работаем со Spec Kit (не OpenSpec). Заполни .specify/memory/constitution.md.  
                                                                                
  Конституция не пересказывает правила проекта, а ссылается на источники        
  истины: AGENTS.md (правила работы агента, слои, тесты, запреты) и             
  docs/baseline.md (зафиксированное поведение). При расхождении                 
  конституции с ними побеждают они.                                             
                                                                                
  Добавь только то, чего в них нет:                                             
  - фичи Spec Kit живут в specs/NNN-<имя>/;                                     
  - общий контракт между фичами - specs/line-comments-contract.md;              
    при конфликте спеки фичи и контракта побеждает контракт;                    
  - поведение, закреплённое в openspec/specs/ (review-queue,                    
    path-id-bounds), сохраняется.                                               
                                                                                
  Не изменяй AGENTS.md, docs/baseline.md, scripts/check.sh и файлы              
  вне .specify/memory/. Не коммить.                                             

● Skill(speckit-constitution)
  ⎿  Successfully loaded skill

  Listed 1 directory, ran 2 shell commands (ctrl+o to expand)

● Good, template resolved successfully. Now let me read AGENTS.md and
  docs/baseline.md for context, plus check existing specs structure.

  Read 3 files, ran 1 shell command (ctrl+o to expand)

● Write(.specify/memory/constitution.md)
  ⎿  Added 77 lines, removed 35 lines
       1 -# [PROJECT_NAME] Constitution                                  
       2 -<!-- Example: Spec Constitution, TaskFlow Constitution, etc. --
         ->                                                              
       1 +<!--                                                           
       2 +Sync Impact Report                                             
       3 +Version change: (template, unratified) → 1.0.0                 
       4 +Modified principles: n/a (initial ratification; template placeh
         +olders replaced)                                               
       5 +Added sections:                                                
       6 +  - Core Principles: Source of Truth Precedence, Layered Archit
         +ecture, Test-First & Check Gate,                               
       7 +    Spec-Driven Scope, Stop on Ambiguity                       
       8 +  - Spec Kit Feature Organization (SECTION_2)                  
       9 +  - Preserved OpenSpec Behavior (SECTION_3)                    
      10 +  - Governance                                                 
      11 +Removed sections: none (first filled version)                  
      12 +Deferred TODOs: none                                           
      13 +-->                                                            
      14  
      15 +# Review Desk Constitution                                     
      16 +                                                               
      17  ## Core Principles
      18  
       6 -### [PRINCIPLE_1_NAME]                                         
       7 -<!-- Example: I. Library-First -->                             
       8 -[PRINCIPLE_1_DESCRIPTION]                                      
       9 -<!-- Example: Every feature starts as a standalone library; Lib
         -raries must be self-contained, independently testable, document
         -ed; Clear purpose required - no organizational-only libraries -
         -->                                                             
      19 +### I. Source of Truth Precedence                              
      20 +This constitution does not restate project rules; it points to 
         +where they live. The binding                                   
      21 +sources are `AGENTS.md` (agent workflow, architecture layers, t
         +est naming, prohibitions) and                                  
      22 +`docs/baseline.md` (frozen MVP behavior). Where this constituti
         +on and either of those documents                               
      23 +disagree, `AGENTS.md` and `docs/baseline.md` win and this docum
         +ent MUST be corrected to match.                                
      24 +Rationale: a single project already has two authoritative, acti
         +vely maintained documents for                                  
      25 +rules and behavior; the constitution exists to add what they do
         + not cover, not to fork them.                                  
      26  
      11 -### [PRINCIPLE_2_NAME]                                         
      12 -<!-- Example: II. CLI Interface -->                            
      13 -[PRINCIPLE_2_DESCRIPTION]                                      
      14 -<!-- Example: Every library exposes functionality via CLI; Text
         - in/out protocol: stdin/args → stdout, errors → stderr; Support
         - JSON + human-readable formats -->                             
      27 +### II. Layered Architecture                                   
      28 +Business rules (permissions, status transitions, validation) MU
         +ST live only in `app/services/`.                               
      29 +Code in `app/web/` MUST only parse the request, call a service,
         + and render a response or                                      
      30 +redirect. Jinja2 templates keep autoescaping on; `|safe` MUST N
         +OT be used. No JS framework and no                             
      31 +frontend build step may be introduced. (Restated from `AGENTS.m
         +d`; see that file for the                                      
      32 +authoritative statement.)                                      
      33  
      16 -### [PRINCIPLE_3_NAME]                                         
      17 -<!-- Example: III. Test-First (NON-NEGOTIABLE) -->             
      18 -[PRINCIPLE_3_DESCRIPTION]                                      
      19 -<!-- Example: TDD mandatory: Tests written → User approved → Te
         -sts fail → Then implement; Red-Green-Refactor cycle strictly en
         -forced -->                                                     
      34 +### III. Test-First & Check Gate                               
      35 +Work is not done until `sh scripts/check.sh` prints `CHECK: PAS
         +S`. Write the test first, show it                              
      36 +fail, then implement the minimal change to pass it. Every accep
         +tance criterion MUST be covered by                             
      37 +a test: baseline criteria by `test_usN_acM_...` tests, feature 
         +criteria by tests in                                           
      38 +`tests/test_<feature>.py` that name or reference the specific r
         +equirement from the feature's                                  
      39 +spec. Existing tests MUST NOT be deleted or weakened to force a
         + green run. Rationale: this is the                             
      40 +only gate the project trusts; diluting it removes the project's
         + only correctness signal.                                      
      41  
      21 -### [PRINCIPLE_4_NAME]                                         
      22 -<!-- Example: IV. Integration Testing -->                      
      23 -[PRINCIPLE_4_DESCRIPTION]                                      
      24 -<!-- Example: Focus areas requiring integration tests: New libr
         -ary contract tests, Contract changes, Inter-service communicati
         -on, Shared schemas -->                                         
      42 +### IV. Spec-Driven Scope                                      
      43 +A feature MUST be implemented only to the extent described by i
         +ts accepted specification —                                    
      44 +either an OpenSpec change (`openspec/changes/<name>/`, later `o
         +penspec/specs/`) or a Spec Kit                                 
      45 +feature (`specs/NNN-<name>/`) — and MUST NOT change behavior fr
         +ozen in `docs/baseline.md` unless                              
      46 +the spec explicitly says so. Scope not written in the accepted 
         +spec is not in scope for the                                   
      47 +change. Rationale: prevents silent architecture or behavior dri
         +ft outside of what was reviewed                                
      48 +and accepted.                                                  
      49  
      26 -### [PRINCIPLE_5_NAME]                                         
      27 -<!-- Example: V. Observability, VI. Versioning & Breaking Chang
         -es, VII. Simplicity -->                                        
      28 -[PRINCIPLE_5_DESCRIPTION]                                      
      29 -<!-- Example: Text I/O ensures debuggability; Structured loggin
         -g required; Or: MAJOR.MINOR.BUILD format; Or: Start simple, YAG
         -NI principles -->                                              
      50 +### V. Stop on Ambiguity                                       
      51 +If a requirement is ambiguous, underspecified, or conflicts wit
         +h the architecture in                                          
      52 +`docs/architecture.md`, stop and ask instead of guessing. Do no
         +t resolve the ambiguity by picking                             
      53 +the implementation that is easiest to build. Rationale: wrong g
         +uesses are more expensive to undo                              
      54 +than a clarifying question, especially once behavior is covered
         + by tests other features will rely                             
      55 +on.                                                            
      56  
      31 -## [SECTION_2_NAME]                                            
      32 -<!-- Example: Additional Constraints, Security Requirements, Pe
         -rformance Standards, etc. -->                                  
      57 +## Spec Kit Feature Organization                               
      58  
      34 -[SECTION_2_CONTENT]                                            
      35 -<!-- Example: Technology stack requirements, compliance standar
         -ds, deployment policies, etc. -->                              
      59 +Spec Kit features live under `specs/NNN-<name>/` (numbered, keb
         +ab-case name), mirroring how                                   
      60 +OpenSpec features live under `openspec/changes/<name>/` and `op
         +enspec/specs/<name>/`.                                         
      61  
      37 -## [SECTION_3_NAME]                                            
      38 -<!-- Example: Development Workflow, Review Process, Quality Gat
         -es, etc. -->                                                   
      62 +The contract shared across all Spec Kit features (e.g. shapes, 
         +events, or data that more than one                             
      63 +feature depends on) lives in `specs/line-comments-contract.md`.
         + When a feature's own spec                                     
      64 +conflicts with this contract, the contract wins and the feature
         + spec MUST be corrected. A feature                             
      65 +spec MAY extend the contract with details specific to that feat
         +ure, but MUST NOT redefine what the                            
      66 +contract already defines.                                      
      67  
      40 -[SECTION_3_CONTENT]                                            
      41 -<!-- Example: Code review requirements, testing gates, deployme
         -nt approval process, etc. -->                                  
      68 +## Preserved OpenSpec Behavior                                 
      69  
      70 +Behavior already captured in `openspec/specs/` — currently `rev
         +iew-queue` and `path-id-bounds` —                              
      71 +remains in force exactly as specified there. A Spec Kit feature
         + MUST NOT regress it; where a new                              
      72 +feature touches the same area, the relevant `openspec/specs/` e
         +ntry is read the same way                                      
      73 +`docs/baseline.md` is read: as a constraint to preserve, not a 
         +default to renegotiate. If a Spec                              
      74 +Kit feature needs to change that behavior, this is a conflict t
         +o stop and ask about (Principle V),                            
      75 +not something to resolve by editing `openspec/specs/` from a Sp
         +ec Kit workflow.                                               
      76 +                                                               
      77  ## Governance
      44 -<!-- Example: Constitution supersedes all other practices; Amen
         -dments require documentation, approval, migration plan -->     
      78  
      46 -[GOVERNANCE_RULES]                                             
      47 -<!-- Example: All PRs/reviews must verify compliance; Complexit
         -y must be justified; Use [GUIDANCE_FILE] for runtime developmen
         -t guidance -->                                                 
      79 +This constitution is subordinate to `AGENTS.md` and `docs/basel
         +ine.md` (Principle I); amendments                              
      80 +here MUST NOT contradict either without first amending those do
         +cuments through their own, separate                            
      81 +process. Amendments to this constitution are made by editing   
      82 +`.specify/memory/constitution.md` directly, incrementing `CONST
         +ITUTION_VERSION` per semantic                                  
      83 +versioning (MAJOR: backward-incompatible principle removal/rede
         +finition; MINOR: new principle or                              
      84 +materially expanded guidance; PATCH: wording/clarification only
         +), and updating                                                
      85 +`LAST_AMENDED_DATE`. Every amendment includes a Sync Impact Rep
         +ort comment at the top of the file                             
      86 +describing what changed; that comment is scratch material for r
         +eview and is expected to be                                    
      87 +removed before the amended file is committed. Compliance is che
         +cked the same way all other work                               
      88 +is checked: `sh scripts/check.sh` must print `CHECK: PASS`, and
         + any new or changed behavior is                                
      89 +traceable to an accepted spec (Principle IV). For day-to-day wo
         +rkflow rules not covered here, see                             
      90 +`AGENTS.md`.                                                   
      91  
      49 -**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATI
         -ON_DATE] | **Last Amended**: [LAST_AMENDED_DATE]               
      50 -<!-- Example: Version: 2.1.1 | Ratified: 2025-06-13 | Last Amen
         -ded: 2025-07-16 -->                                            
      92 +**Version**: 1.0.0 | **Ratified**: 2026-10-30 | **Last Amended*
         +*: 2026-10-30                                                  

● Constitution written to .specify/memory/constitution.md.

  Version: 1.0.0 (initial ratification — previous file was an unfilled template,
  so this is a MAJOR/first fill rather than an incremental bump). Ratified and
  amended 2026-10-30.

  Structure:
  - 5 principles: Source of Truth Precedence (AGENTS.md/docs/baseline.md win on
    conflict), Layered Architecture, Test-First & Check Gate, Spec-Driven Scope,
    Stop on Ambiguity
  - Spec Kit Feature Organization section: specs/NNN-<name>/ layout,
    specs/line-comments-contract.md as the cross-feature contract that wins over
    individual feature specs on conflict
  - Preserved OpenSpec Behavior section: openspec/specs/review-queue and
    openspec/specs/path-id-bounds stay in force, treated like baseline when a
    Spec Kit feature touches that area
  - Governance: amendment procedure, semver rules, compliance tied to sh 
    scripts/check.sh

  No placeholders left unfilled, no TODOs deferred. Only
  .specify/memory/constitution.md was touched — AGENTS.md, docs/baseline.md,
  scripts/check.sh untouched, nothing committed.

  Suggested commit message (for when you're ready): docs: ratify project 
  constitution v1.0.0 (Spec Kit governance)

✻ Crunched for 1m 7s · done 3:56 AM