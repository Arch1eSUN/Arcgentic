#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const root = path.resolve(__dirname, "..");
const ownRealpath = fs.realpathSync(process.argv[1]);

function printHelp() {
  process.stdout.write(`Arcgentic npm bundle v2.2.0

Usage:
  arcgentic install-codex-local [--home PATH] [--skip-validate]
  arcgentic bundle-root
  arcgentic python -- <arcgentic-cli-args>
  arcgentic --help

This npm package is a release bundle for Arcgentic plugin assets. It includes
skills, agents, scripts, schemas, templates, and platform manifests.

The Python CLI is still published separately on PyPI:
  pipx install arcgentic

`);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: "inherit",
    ...options,
  });
  if (result.error) {
    process.stderr.write(`${result.error.message}\n`);
    process.exit(1);
  }
  process.exit(result.status === null ? 1 : result.status);
}

function findPythonArcgentic() {
  const pathEntries = (process.env.PATH || "").split(path.delimiter).filter(Boolean);
  const seen = new Set();

  for (const dir of pathEntries) {
    const candidate = path.join(dir, "arcgentic");
    if (seen.has(candidate) || !fs.existsSync(candidate)) {
      continue;
    }
    seen.add(candidate);

    try {
      if (fs.realpathSync(candidate) === ownRealpath) {
        continue;
      }
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {
      continue;
    }
  }

  return null;
}

const args = process.argv.slice(2);
const command = args[0];

if (!command || command === "-h" || command === "--help") {
  printHelp();
  process.exit(0);
}

if (command === "bundle-root") {
  process.stdout.write(`${root}\n`);
  process.exit(0);
}

if (command === "install-codex-local") {
  run("bash", [
    path.join(root, "scripts", "install-codex-local.sh"),
    "--plugin-root",
    root,
    ...args.slice(1),
  ]);
}

if (command === "python") {
  const pythonArcgentic = findPythonArcgentic();
  if (!pythonArcgentic) {
    process.stderr.write(
      "Python arcgentic CLI not found. Install it with: pipx install arcgentic\n"
    );
    process.exit(1);
  }

  const pythonArgs = args[1] === "--" ? args.slice(2) : args.slice(1);
  run(pythonArcgentic, pythonArgs);
}

printHelp();
process.stderr.write(`Unknown command: ${command}\n`);
process.exit(2);
