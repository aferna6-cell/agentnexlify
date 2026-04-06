"use strict";

const { execSync, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const TEST_FILE_PATTERN =
  /(^|\/)(__tests__\/.+\.(js|jsx|ts|tsx)$|.+\.(test|spec)\.(js|jsx|ts|tsx)$)/;

function getStagedFiles() {
  const output = execSync("git diff --cached --name-only --diff-filter=ACM", {
    encoding: "utf8",
  });
  return output
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function resolveEslintBinary(repoRoot) {
  const binaryName = process.platform === "win32" ? "eslint.cmd" : "eslint";
  return path.join(repoRoot, "node_modules", ".bin", binaryName);
}

function main() {
  const repoRoot = process.cwd();
  const stagedFiles = getStagedFiles();
  const stagedTestFiles = stagedFiles.filter((filePath) =>
    TEST_FILE_PATTERN.test(filePath.replace(/\\/g, "/")),
  );

  if (stagedTestFiles.length === 0) {
    console.log("No staged JS/TS test files found for test-quality lint.");
    return 0;
  }

  const eslintBinary = resolveEslintBinary(repoRoot);
  if (!fs.existsSync(eslintBinary)) {
    console.error(
      "ESLint test-quality gate is configured but dependencies are missing. Run `npm install` in repo root.",
    );
    return 1;
  }

  const result = spawnSync(
    eslintBinary,
    ["--config", "eslint.test-quality.config.cjs", ...stagedTestFiles],
    { stdio: "inherit", shell: false },
  );

  if (typeof result.status === "number") {
    return result.status;
  }
  return 1;
}

process.exit(main());
