#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");

function localEnv(name) {
  const text = readFileSync(resolve(root, ".env.local"), "utf8");
  return text.match(new RegExp(`^${name}=(.+)$`, "m"))?.[1]?.trim();
}

const apiUrl = process.env.CONVEX_SITE_URL ?? localEnv("CONVEX_SITE_URL");
const adminKey = process.env.ADMIN_API_KEY ?? execFileSync(
  "security",
  ["find-generic-password", "-w", "-s", "tucson-sermon-integrity-admin-dev"],
  { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
).trim();
const snapshot = JSON.parse(readFileSync(resolve(root, "site/data/churches.json"), "utf8"));

let created = 0;
let existing = 0;
for (const church of snapshot.churches) {
  for (const pastor of church.pastors.filter((person) => person.active !== false)) {
    const stableName = pastor.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    const task = {
      task_key: `${church.slug}:${stableName}:both:v1`,
      church_slug: church.slug,
      pastor_name: pastor.name,
      scope: "both",
      priority: church.status === "unchecked" ? 10 : 0,
      instructions: "Follow AGENTS.md. Review plagiarism and AI-writing separately; submit one API finding per check. Upload full transcripts and reports as artifacts, but keep public excerpts short. Findings remain private until reviewer approval.",
    };
    const response = await fetch(`${apiUrl}/api/v1/admin/tasks`, {
      method: "POST",
      headers: {
        authorization: `Bearer admin:${adminKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error(`${task.task_key}: ${response.status} ${await response.text()}`);
    const result = await response.json();
    if (result.duplicate) existing += 1;
    else created += 1;
  }
}

process.stdout.write(`Research queue ready: ${created} created, ${existing} already present.\n`);
