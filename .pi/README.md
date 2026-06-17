# Pi Agent Setup

This project uses Pi to generate the daily Hacker News digest.

## Local Run

Install Pi:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Provide credentials for your chosen provider. The default project settings use Anthropic:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Generate the default target date, which is today:

```bash
pi --provider anthropic --model claude-sonnet-4-5 --thinking high --no-session \
  --prompt-template .pi/prompts/daily.md \
  --skill .pi/skills/chinese-writing \
  -p "/daily"
```

Generate a specific date:

```bash
pi --provider anthropic --model claude-sonnet-4-5 --thinking high --no-session \
  --prompt-template .pi/prompts/daily.md \
  --skill .pi/skills/chinese-writing \
  -p "/daily 2026-04-22"
```

## GitHub Actions

The scheduled workflow installs `@earendil-works/pi-coding-agent` and runs the `/daily` prompt from `.pi/prompts/daily.md`.

Recommended repository secrets and variables:

- Secret `ANTHROPIC_API_KEY`: Anthropic API key for Pi.
- Secret `ANTHROPIC_BASE_URL`: optional Anthropic-compatible proxy base URL.
- Variable `PI_PROVIDER`: optional provider override, defaults to `anthropic`.
- Variable `PI_MODEL`: optional model override, defaults to `claude-sonnet-4-5`.

For compatibility with the old Claude Code workflow, `ANTHROPIC_AUTH_TOKEN` is also accepted as a fallback for `ANTHROPIC_API_KEY`.
