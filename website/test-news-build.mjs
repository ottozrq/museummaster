#!/usr/bin/env node
/**
 * 新闻站构建冒烟测试：运行 build-news.mjs，并检查多语言列表页与示例文章输出是否存在。
 *
 * 用法（仓库根目录）：
 *   node website/scripts/test-news-build.mjs
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(SCRIPT_DIR, "../..");
const BUILD_SCRIPT = path.join(SCRIPT_DIR, "build-news.mjs");

function main() {
  const build = spawnSync(process.execPath, [BUILD_SCRIPT], {
    cwd: REPO_ROOT,
    encoding: "utf-8",
    env: process.env,
  });

  if (build.status !== 0) {
    console.error(build.stderr || build.stdout || "build-news.mjs failed");
    process.exit(build.status ?? 1);
  }

  const requiredRelPaths = [
    "website/news/index.html",
    "website/en/news/index.html",
    "website/fr/news/index.html",
    "website/news/cacaou-news-launch/index.html",
    "website/en/news/cacaou-news-launch/index.html",
    "website/fr/news/cacaou-news-launch/index.html",
    "website/sitemap.xml",
  ];

  const missing = [];
  for (const rel of requiredRelPaths) {
    const abs = path.join(REPO_ROOT, rel);
    if (!fs.existsSync(abs)) {
      missing.push(rel);
    }
  }

  if (missing.length > 0) {
    console.error("Missing expected files:\n", missing.join("\n"));
    process.exit(1);
  }

  const sitemap = fs.readFileSync(path.join(REPO_ROOT, "website/sitemap.xml"), "utf-8");
  if (!sitemap.includes("https://www.cacaou.net/news/")) {
    console.error("sitemap.xml does not contain Chinese news index URL");
    process.exit(1);
  }
  if (!sitemap.includes("https://www.cacaou.net/en/news/")) {
    console.error("sitemap.xml does not contain English news index URL");
    process.exit(1);
  }

  console.log("test-news-build: OK");
}

main();
