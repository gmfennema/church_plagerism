/// <reference types="vite/client" />

import { convexTest } from "convex-test";
import { describe, expect, test } from "vitest";
import { internal } from "./_generated/api";
import schema from "./schema";

const modules = import.meta.glob("./**/*.ts");

describe("research submission workflow", () => {
  test("an agent can claim a task and submit an idempotent proposal", async () => {
    const t = convexTest(schema, modules);
    const created = await t.mutation(internal.research.createTask, {
      taskKey: "example:pastor:both:v1",
      churchSlug: "example-church",
      pastorName: "Example Pastor",
      scope: "both",
      priority: 10,
    });
    await t.mutation(internal.research.claimTask, {
      taskId: created.taskId,
      agentId: "test-agent",
      leaseMinutes: 120,
    });
    const args = {
      agentId: "test-agent",
      submissionKey: "test-agent:example:plagiarism:v1",
      payloadHash: "same-payload",
      schemaVersion: "1.0",
      rubricVersion: "2026-09-10",
      taskId: created.taskId,
      churchSlug: "example-church",
      pastorName: "Example Pastor",
      finding: {
        kind: "plagiarism" as const,
        status: "inconclusive" as const,
        confidence: "low" as const,
        summary: "Only three usable transcripts were available, so the review cannot support a conclusion.",
        sermonsReviewed: 3,
        methods: ["distinctive_phrase_search"],
        metricsJson: "{}",
      },
      sources: [],
      evidence: [],
      artifacts: [],
      attested: true,
    };
    const first = await t.mutation(internal.research.submit, args);
    const replay = await t.mutation(internal.research.submit, args);
    expect(first.status).toBe("pending");
    expect(first.duplicate).toBe(false);
    expect(replay).toMatchObject({ submissionId: first.submissionId, duplicate: true });
  });

  test("the server rejects a plagiarism clearance with too few sermons", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.mutation(internal.research.submit, {
        agentId: "test-agent",
        submissionKey: "test-agent:bad-clearance:v1",
        payloadHash: "bad-clearance",
        schemaVersion: "1.0",
        rubricVersion: "2026-09-10",
        churchSlug: "example-church",
        pastorName: "Example Pastor",
        finding: {
          kind: "plagiarism",
          status: "cleared",
          confidence: "medium",
          summary: "No meaningful overlap was found, but this sample is too small for a clearance.",
          sermonsReviewed: 3,
          methods: ["distinctive_phrase_search"],
          metricsJson: "{}",
        },
        sources: [],
        evidence: [],
        artifacts: [],
        attested: true,
      }),
    ).rejects.toThrow("at least 8 sermons");
  });

  test("the server rejects AI flags without corroboration", async () => {
    const t = convexTest(schema, modules);
    await expect(
      t.mutation(internal.research.submit, {
        agentId: "test-agent",
        submissionKey: "test-agent:bad-ai-flag:v1",
        payloadHash: "bad-ai-flag",
        schemaVersion: "1.0",
        rubricVersion: "2026-09-10",
        churchSlug: "example-church",
        pastorName: "Example Pastor",
        finding: {
          kind: "ai_writing",
          status: "flagged",
          confidence: "medium",
          summary: "Two stylometric signals shifted, but no independent corroborating evidence was submitted.",
          sermonsReviewed: 9,
          methods: ["stylometric_drift"],
          metricsJson: "{}",
        },
        sources: [],
        evidence: [
          { type: "stylometric_shift", description: "Signal one moved by more than two standard deviations." },
          { type: "stylometric_shift", description: "Signal two moved by more than two standard deviations." },
        ],
        artifacts: [],
        attested: true,
      }),
    ).rejects.toThrow("corroborating evidence");
  });
});
