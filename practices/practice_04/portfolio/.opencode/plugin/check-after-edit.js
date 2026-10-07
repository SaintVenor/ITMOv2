// Plugin OpenCode: после каждой успешной правки файла запускает scripts/check.sh
// и дописывает его вывод к результату инструмента, чтобы агент сразу видел PASS/FAIL.
// Каждый запуск пишется в .opencode/hook-log.jsonl (время, инструмент, файл, код выхода)
// - это доказательство срабатывания hook для отчёта.
//
// Один файл работает в обеих версиях OpenCode:
// - 1.18.29+ (V1) вызывает server() и берёт hook "tool.execute.after";
// - 2.x (V2) читает id и setup(ctx) и регистрирует hook через ctx.tool.hook("execute.after").
// Папка .opencode/plugin/ (единственное число) обнаруживается и 1.x, и 2.x.

import { spawnSync } from "node:child_process"
import { appendFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

// Корень проекта = папка, где лежит .opencode/ с этим плагином.
// Не берём рабочий каталог OpenCode: проект живёт в подпапке форка курса.
const PROJECT_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..")

const EDIT_TOOLS = new Set(["write", "edit", "patch", "apply_patch", "multiedit"])

function runCheck(tool, file) {
  const run = spawnSync("sh", ["scripts/check.sh"], { cwd: PROJECT_ROOT, encoding: "utf8", timeout: 120_000 })
  const code = run.status ?? -1
  const output = `${run.stdout ?? ""}${run.stderr ?? ""}`.trim().split("\n").slice(-40).join("\n")

  try {
    mkdirSync(join(PROJECT_ROOT, ".opencode"), { recursive: true })
    appendFileSync(
      join(PROJECT_ROOT, ".opencode", "hook-log.jsonl"),
      JSON.stringify({ time: new Date().toISOString(), tool, file: file ?? null, exit_code: code }) + "\n",
    )
  } catch {}

  return (
    `\n\n[hook check-after-edit] sh scripts/check.sh -> exit ${code}\n${output}\n` +
    (code === 0 ? "" : "Проверка не прошла: исправь причину, не ослабляя тесты и runner.\n")
  )
}

function appendText(result, text) {
  if (!result) return { content: text }
  if (typeof result.content === "string") return { ...result, content: result.content + text }
  if (Array.isArray(result.content)) return { ...result, content: [...result.content, { type: "text", text }] }
  if (typeof result.output === "string") return { ...result, output: result.output + text }
  return { ...result, metadata: { ...(result.metadata ?? {}), check: text } }
}

export default {
  id: "portfolio.check-after-edit",

  // OpenCode 2.x
  async setup(ctx) {
    await ctx.tool.hook("execute.after", (event) => {
      if (event.status !== "completed" || !EDIT_TOOLS.has(event.tool)) return
      const file = event.input?.filePath ?? event.input?.path
      event.result = appendText(event.result, runCheck(event.tool, file))
    })
  },

  // OpenCode 1.18.29+
  async server() {
    return {
      "tool.execute.after": async (input, output) => {
        if (!EDIT_TOOLS.has(input.tool)) return
        const file = input.args?.filePath ?? output?.metadata?.filepath ?? output?.metadata?.filePath
        const text = runCheck(input.tool, file)
        if (output && typeof output.output === "string") output.output += text
        else if (output) output.output = text
      },
    }
  },
}
