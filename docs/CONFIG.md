# CONFIG.md — โครงสร้างคอนฟิกที่ editor จัดการ

## ไฟล์เป้าหมาย

โปรเจกต์นี้แก้ `opencode.json` ของผู้ใช้ (หลายตำแหน่ง):

| ขอบเขต | ตำแหน่ง |
|---|---|
| Global (ค่าเริ่มต้นของแอป) | `~/.config/opencode/opencode.json` หรือ `.jsonc` |
| Project | `./opencode.json`, `./opencode.jsonc`, หรือ `.opencode/opencode.json` |

ค่าเริ่มต้นของ editor → `~/.config/opencode/opencode.json` (ผ่าน `ConfigModel.DEFAULT_CONFIG_PATH`)

## ตัวอย่างคอนฟิกเต็ม (ที่ editor อ่าน/เขียน)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "provider/model-id",
  "small_model": "provider/model-id",
  "instructions": ["AGENTS.md", "docs/style.md"],

  "agent": {
    "build": { "model": "provider/model-id", "mode": "primary", "prompt": "..." }
  },
  "skills": {
    "paths": ["D:\\MyCode\\skills"],
    "urls": ["https://example.com/.well-known/skills/"]
  },
  "permission": {
    "bash": "allow",
    "webfetch": { "ask": "ยืนยัน" }
  },

  "provider": {
    "my-provider": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "ชื่อ provider",
      "options": { "baseURL": "...", "apiKey": "..." },
      "whitelist": ["model-id-1", "model-id-2"],
      "models": {
        "model-key": {
          "id": "provider/model-id",
          "name": "ชื่อแสดงผล",
          "reasoning": true,
          "tool_call": true,
          "limit": { "context": 1000000, "output": 65536 },
          "cost": { "input": 0.1, "output": 0.2, "cache_read": 0.01, "cache_write": 0.5 },
          "options": { "image": true },
          "interleaved": { "field": "reasoning_content" }
        }
      }
    }
  },

  "mcp": {
    "playwright": {
      "type": "local",
      "command": ["npx", "-y", "@playwright/mcp@latest"],
      "enabled": true,
      "environment": {}
    },
    "local-server": {
      "type": "local",
      "command": ["x64dbg-automate-mcp"],
      "enabled": true,
      "env": { "X64DBG_PATH": "D:\\..." }
    },
    "remote-thing": {
      "type": "remote",
      "url": "https://...",
      "headers": { "Authorization": "Bearer ..." },
      "enabled": true
    }
  }
}
```

## ช่องที่ editor ครอบคลุม

| กลุ่ม | ช่อง | รูปแบบ |
|---|---|---|
| Global (แท็บ Global) | `model`, `small_model` | string |
| Global | `instructions` | list of path |
| Global | `compaction.auto` / `.prune` | boolean |
| Global | `compaction.tail_turns` / `.preserve_recent_tokens` / `.reserved` | uint |
| Global | `enabled_providers` (whitelist) / `disabled_providers` (blacklist) | list of string |
| Agent | `model`, `mode` (subagent/primary/all), `color`, `disable`, `hidden`, `temperature`, `top_p`, `steps`, `description`, `prompt` | ตาม schema |
| Skill | `skills.paths`, `skills.urls` | list editor |
| Permission | `permission.[tool]` (read/edit/bash/task/...) | ask / allow / deny หรือ object |
| Provider | `npm` | string |
| Provider | `name` | string |
| Provider | `options.baseURL` | string |
| Provider | `options.apiKey` | string (ซ่อนการพิมพ์, ปุ่มแสดง/ซ่อน) |
| Provider | `whitelist` | one-model-per-line |
| Model | `id` | string |
| Model | `name` | string |
| Model | `reasoning` | boolean |
| Model | `tool_call` | boolean |
| Model | `limit.context` | uint (tokens) |
| Model | `limit.output` | uint (tokens) |
| Model | `cost.input` / `.output` / `.cache_read` / `.cache_write` | float ต่อ 1M tokens |
| Model | `options` | JSON block |
| Model | `extra keys` (เช่น `interleaved`) | JSON block (merge, ไม่ลบ) |
| MCP | `type` | `local` / `remote` |
| MCP | `command` | parse ด้วย `shlex` → array (รองรับ arg มีช่องว่าง) |
| MCP | `url` | string |
| MCP | `headers` | JSON block |
| MCP | `environment` / `env` | JSON block (preserve key เดิม) |
| MCP | `enabled` | boolean |

## เครื่องมืออัตโนมัติ (`app/model_registry.py`)

- **ดึงค่าอัตโนมัติ (models.dev)** — ในฟอร์ม model: เติม `limit`/`cost`/`reasoning`/`tool_call`/`name`/`interleaved` จาก registry `https://models.dev/api.json` (cached ต่อ session, offline คืนค่าเดิม)
- **ทดสอบ API** — ในฟอร์ม provider: `GET {baseURL}/models` (Bearer apiKey ถ้ามี) → แจงผล + เสนอเติม whitelist จาก response
- **ดึง whitelist (registry)** — เติม `whitelist` ทั้งหมดที่ registry มีของ provider นี้

## กฎการ validate

- **ไม่ commit nested ให้ผิด**: `skills` เป็น object, `plugin` เป็น array, `agent` เป็น object keyed-by-name
- **`mcp[name].command` ต้องเป็น array** — ตัว editor transform ส่วน space-separated → array
- **`type` ของ mcp จำเป็น** — ตัว editor บังคับมีเสมอ (`local` | `remote`)

## สถานการณ์ที่ schema flag ผิด (false alarm ที่ควรรู้)

- `model`/`small_model` ที่เป็น **custom provider** จะถูก schema ทางการตีว่า invalid เพราะ schema มี enum เฉพาะ model ในตัว ไม่ใช่ความผิดของ config จริง
- mcp ที่ใช้ key `env` (ไม่ใช่ `environment`) อาจถูก schema ตีว่า invalid — `ConfigModel.schema_errors()` เตือน แต่ไม่บล็อก save

## หมายเหตุความปลอดภัย

- apiKey เก็บ plaintext ในไฟล์ — editor แสดงด้วย `QLineEdit.Password`
- อย่า commit `opencode.json` จริง — หากต้องแชร์ตัวอย่าง ใช้ `{env:VAR}` แทน
