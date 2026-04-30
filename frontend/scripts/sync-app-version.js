#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const nextVersion = process.argv[2];

if (!nextVersion) {
  console.error("Missing version argument, usage: node scripts/sync-app-version.js <version>");
  process.exit(1);
}

const rootDir = path.resolve(__dirname, "..");
const appJsonPath = path.join(rootDir, "app.json");
const infoPlistPath = path.join(rootDir, "ios", "Artiou", "Info.plist");

function updateAppJsonVersion(version) {
  const raw = fs.readFileSync(appJsonPath, "utf8");
  const appConfig = JSON.parse(raw);

  if (!appConfig.expo) {
    throw new Error("app.json is missing expo field");
  }

  appConfig.expo.version = version;
  fs.writeFileSync(appJsonPath, `${JSON.stringify(appConfig, null, 2)}\n`, "utf8");
}

function updateInfoPlistVersion(version) {
  const raw = fs.readFileSync(infoPlistPath, "utf8");
  const pattern = /(<key>CFBundleShortVersionString<\/key>\s*<string>)([^<]*)(<\/string>)/;

  if (!pattern.test(raw)) {
    throw new Error("CFBundleShortVersionString not found in Info.plist");
  }

  const updated = raw.replace(pattern, `$1${version}$3`);
  fs.writeFileSync(infoPlistPath, updated, "utf8");
}

updateAppJsonVersion(nextVersion);
updateInfoPlistVersion(nextVersion);

console.log(`Synced app versions to ${nextVersion}`);
