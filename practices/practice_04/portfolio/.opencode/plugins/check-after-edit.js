// OpenCode 2 plugin: после каждой успешной правки файла запускает scripts/check.sh
// и дописывает его вывод к результату инструмента, чтобы агент сразу видел PASS/FAIL.
// Каждый запуск пишется в .opencode/hook-log.jsonl (время, инструмент, файл, код выхода)
// - это доказательство срабатывания hook для отчёта.
//
// Формат V2: default export с id и setup(ctx); хук регистрируется через ctx.tool.hook.
// V1-плагины (tool.execute.after) в OpenCode 2 не исполняются.

import { spawnSync } from "node:child_process"
import { appendFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

// Корень проекта = папка, где лежит .opencode/ с этим плагином.
// Не берём ctx.location.directory: проект живёт в подпапке форка курса,
// и OpenCode может считать корнем весь git-репозиторий.
const PROJECT_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..")

const EDIT_TOOLS = new Set(["write", "edit", "patch", "apply_patch", "multiedit"])

function appendText(result, text) {
  if (!result) return { content: text }
  if (typeof result.content === "string") return { ...result, content: result.content + text }
  if (Array.isArray(result.content)) return { ...result, content: [...result.content, { type: "text", text }] }
  if (typeof result.output === "string") return { ...result, output: result.output + text }
  return { ...result, metadata: { ...(result.metadata ?? {}), check: text } }
}

export default {
  id: "portfolio.check-after-edit",
  async setup(ctx) {
    const root = PROJECT_ROOT

    await ctx.tool.hook("execute.after", (event) => {
      if (event.status !== "completed" || !EDIT_TOOLS.has(event.tool)) return

      const run = spawnSync("sh", ["scripts/check.sh"], { cwd: root, encoding: "utf8", timeout: 120_000 })
      const code = run.status ?? -1
      const output = `${run.stdout ?? ""}${run.stderr ?? ""}`.trim().split("\n").slice(-40).join("\n")
      const file = event.input?.filePath ?? event.input?.path ?? null

      try {
        mkdirSync(join(root, ".opencode"), { recursive: true })
        appendFileSync(
          join(root, ".opencode", "hook-log.jsonl"),
          JSON.stringify({ time: new Date().toISOString(), tool: event.tool, file, exit_code: code }) + "\n",
        )
      } catch {}

      event.result = appendText(
        event.result,
        `\n\n[hook check-after-edit] sh scripts/check.sh -> exit ${code}\n${output}\n` +
          (code === 0 ? "" : "Проверка не прошла: исправь причину, не ослабляя тесты и runner.\n"),
      )
    })
  },
}
