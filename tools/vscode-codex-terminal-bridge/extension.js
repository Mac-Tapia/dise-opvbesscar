const vscode = require("vscode");
const fs = require("fs");
const path = require("path");

let watcher;
let statusBar;
let lastCommandId;

function getWorkspaceFolder() {
  const folders = vscode.workspace.workspaceFolders;
  return folders && folders.length > 0 ? folders[0] : undefined;
}

function getBridgePaths() {
  const folder = getWorkspaceFolder();
  if (!folder) {
    return undefined;
  }

  const root = folder.uri.fsPath;
  const dir = path.join(root, ".vscode", "codex-terminal-bridge");
  return {
    folder,
    root,
    dir,
    commandsFile: path.join(dir, "commands.json"),
    statusFile: path.join(dir, "status.json")
  };
}

function writeJson(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
}

function updateStatus(state, details = {}) {
  const paths = getBridgePaths();
  if (!paths) {
    return;
  }

  writeJson(paths.statusFile, {
    state,
    updatedAt: new Date().toISOString(),
    ...details
  });
}

function setStatusBar(state) {
  if (!statusBar) {
    return;
  }

  statusBar.text = state === "on" ? "$(terminal) Codex Bridge: ON" : "$(terminal) Codex Bridge: OFF";
  statusBar.tooltip = "Codex Terminal Bridge";
  statusBar.command = state === "on" ? "codexTerminalBridge.stop" : "codexTerminalBridge.start";
  statusBar.show();
}

function isInsideWorkspace(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === "" || (!!relative && !relative.startsWith("..") && !path.isAbsolute(relative));
}

function resolveCwd(root, requestedCwd) {
  if (!requestedCwd || typeof requestedCwd !== "string") {
    return root;
  }

  const resolved = path.isAbsolute(requestedCwd)
    ? path.resolve(requestedCwd)
    : path.resolve(root, requestedCwd);

  if (!isInsideWorkspace(root, resolved)) {
    vscode.window.showWarningMessage("Codex Terminal Bridge ignored cwd outside the workspace.");
    return root;
  }

  return resolved;
}

function getOrCreateTerminal(name, cwd) {
  const terminalName = typeof name === "string" && name.trim() ? name.trim() : "Codex Bridge";
  const existing = vscode.window.terminals.find((terminal) => terminal.name === terminalName);
  if (existing) {
    existing.show(true);
    return existing;
  }

  const terminal = vscode.window.createTerminal({ name: terminalName, cwd });
  terminal.show(true);
  return terminal;
}

function runPayload(payload) {
  const paths = getBridgePaths();
  if (!paths || !payload || typeof payload.command !== "string" || payload.command.trim() === "") {
    return;
  }

  const id = String(payload.id || payload.command);
  if (id === lastCommandId) {
    return;
  }

  lastCommandId = id;
  const cwd = resolveCwd(paths.root, payload.cwd);
  const terminal = getOrCreateTerminal(payload.name, cwd);
  terminal.sendText(payload.command, true);

  updateStatus("ran", {
    id,
    command: payload.command,
    cwd,
    terminal: terminal.name
  });
}

function readAndRunCommandFile() {
  const paths = getBridgePaths();
  if (!paths || !fs.existsSync(paths.commandsFile)) {
    return;
  }

  try {
    const raw = fs.readFileSync(paths.commandsFile, "utf8").trim();
    if (!raw) {
      return;
    }
    runPayload(JSON.parse(raw));
  } catch (error) {
    updateStatus("error", { message: error.message });
    vscode.window.showErrorMessage(`Codex Terminal Bridge: ${error.message}`);
  }
}

function ensureBridgeFiles() {
  const paths = getBridgePaths();
  if (!paths) {
    return undefined;
  }

  fs.mkdirSync(paths.dir, { recursive: true });
  if (!fs.existsSync(paths.commandsFile)) {
    writeJson(paths.commandsFile, {});
  }
  updateStatus("ready", {
    commandsFile: paths.commandsFile
  });
  return paths;
}

function startBridge(context) {
  if (watcher) {
    setStatusBar("on");
    updateStatus("watching");
    return;
  }

  const paths = ensureBridgeFiles();
  if (!paths) {
    vscode.window.showErrorMessage("Codex Terminal Bridge needs an opened workspace folder.");
    return;
  }

  watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(paths.folder, ".vscode/codex-terminal-bridge/commands.json")
  );

  watcher.onDidChange(readAndRunCommandFile, null, context.subscriptions);
  watcher.onDidCreate(readAndRunCommandFile, null, context.subscriptions);
  context.subscriptions.push(watcher);

  setStatusBar("on");
  updateStatus("watching", {
    commandsFile: paths.commandsFile
  });
}

function stopBridge() {
  if (watcher) {
    watcher.dispose();
    watcher = undefined;
  }
  setStatusBar("off");
  updateStatus("stopped");
}

async function runCommandFromInput() {
  const paths = getBridgePaths();
  if (!paths) {
    vscode.window.showErrorMessage("Open a workspace folder before running a Codex command.");
    return;
  }

  const command = await vscode.window.showInputBox({
    prompt: "Command to run in the VS Code integrated terminal"
  });

  if (command) {
    runPayload({
      id: Date.now().toString(),
      command,
      cwd: paths.root,
      name: "Codex Bridge"
    });
  }
}

function runDockerBuild() {
  const paths = getBridgePaths();
  if (!paths) {
    vscode.window.showErrorMessage("Open a workspace folder before running the Docker build.");
    return;
  }

  runPayload({
    id: Date.now().toString(),
    name: "Codex Docker Build",
    cwd: paths.root,
    command: "docker compose --progress=plain -f docker-compose.dev.yml --env-file .env.local build a2c-api"
  });
}

function activate(context) {
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  context.subscriptions.push(statusBar);
  setStatusBar("off");

  context.subscriptions.push(vscode.commands.registerCommand("codexTerminalBridge.start", () => startBridge(context)));
  context.subscriptions.push(vscode.commands.registerCommand("codexTerminalBridge.stop", stopBridge));
  context.subscriptions.push(vscode.commands.registerCommand("codexTerminalBridge.runCommand", runCommandFromInput));
  context.subscriptions.push(vscode.commands.registerCommand("codexTerminalBridge.runDockerBuild", runDockerBuild));

  const config = vscode.workspace.getConfiguration("codexTerminalBridge");
  if (config.get("autoStart", true)) {
    startBridge(context);
  }
}

function deactivate() {
  stopBridge();
}

module.exports = {
  activate,
  deactivate
};
