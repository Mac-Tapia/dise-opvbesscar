# Codex Terminal Bridge

Local VS Code extension that lets Codex send approved commands to a VS Code integrated terminal for the current workspace.

The extension watches:

```text
.vscode/codex-terminal-bridge/commands.json
```

When the file changes, it runs the JSON payload in an integrated terminal:

```json
{
  "id": "unique-command-id",
  "name": "Codex Bridge",
  "cwd": "D:\\diseñopvbesscar",
  "command": "docker compose --progress=plain -f docker-compose.dev.yml --env-file .env.local build a2c-api"
}
```

The `cwd` must stay inside the open workspace. The extension writes status to:

```text
.vscode/codex-terminal-bridge/status.json
```

Commands:

- `Codex: Start Terminal Bridge`
- `Codex: Stop Terminal Bridge`
- `Codex: Run Command in Integrated Terminal`
- `Codex: Run Docker A2C Build`
