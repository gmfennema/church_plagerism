#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");

function localEnv(name) {
  const text = readFileSync(resolve(root, ".env.local"), "utf8");
  const match = text.match(new RegExp(`^${name}=(.+)$`, "m"));
  return match?.[1]?.trim();
}

function keychain(service) {
  return execFileSync("security", ["find-generic-password", "-w", "-s", service], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "ignore"],
  }).trim();
}

const apiUrl = process.env.CONVEX_SITE_URL ?? localEnv("CONVEX_SITE_URL");
const adminKey = process.env.ADMIN_API_KEY ?? keychain("tucson-sermon-integrity-admin-dev");
const snapshot = JSON.parse(readFileSync(resolve(root, "site/data/churches.json"), "utf8"));

let imported = 0;
for (const church of snapshot.churches) {
  const response = await fetch(`${apiUrl}/api/v1/admin/import-church`, {
    method: "POST",
    headers: {
      authorization: `Bearer admin:${adminKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(church),
  });
  if (!response.ok) {
    throw new Error(`Import failed for ${church.slug}: ${response.status} ${await response.text()}`);
  }
  imported += 1;
  if (imported % 20 === 0) process.stdout.write(`Imported ${imported}/${snapshot.churches.length}\n`);
}

process.stdout.write(`Imported ${imported} churches into ${apiUrl}\n`);
