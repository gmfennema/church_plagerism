import { v } from "convex/values";
import { internalMutation, internalQuery } from "./_generated/server";
import {
  submissionFinding,
  submittedArtifact,
  submittedEvidence,
  submittedSource,
  taskScope,
} from "./validators";

const MAX_EVIDENCE_ITEMS = 100;
const MAX_SOURCES = 40;
const MAX_ARTIFACTS = 30;

function validateFinding(
  finding: {
    kind: "plagiarism" | "ai_writing";
    status: "unchecked" | "in_progress" | "cleared" | "flagged" | "inconclusive";
    confidence?: "low" | "medium" | "high";
    summary: string;
    sermonsReviewed: number;
    methods: string[];
  },
  evidence: Array<{
    type: string;
    matchedWords?: number;
    scriptureExcluded?: boolean;
  }>,
) {
  if (!Number.isInteger(finding.sermonsReviewed) || finding.sermonsReviewed < 0) {
    throw new Error("sermons_reviewed must be a non-negative integer");
  }
  if (finding.summary.trim().length < 30) {
    throw new Error("summary must explain the finding in at least 30 characters");
  }
  if (finding.status === "unchecked" || finding.status === "in_progress") {
    throw new Error("final submissions must be cleared, flagged, or inconclusive");
  }
  if ((finding.status === "cleared" || finding.status === "flagged") && !finding.confidence) {
    throw new Error("confidence is required for cleared and flagged findings");
  }
  if (finding.status === "flagged" && finding.confidence === "low") {
    throw new Error("low confidence cannot be published as flagged; use inconclusive");
  }
  if (finding.kind === "plagiarism" && finding.status === "cleared" && finding.sermonsReviewed < 8) {
    throw new Error("a plagiarism finding needs at least 8 sermons to be cleared");
  }
  if (finding.kind === "plagiarism" && finding.status === "flagged") {
    const qualifying = evidence.filter(
      (item) =>
        (item.type === "verbatim_overlap" || item.type === "paraphrase_overlap") &&
        item.scriptureExcluded !== true &&
        (item.matchedWords ?? 0) >= 20,
    );
    if (finding.sermonsReviewed < 2 || qualifying.length < 2) {
      throw new Error(
        "a flagged plagiarism proposal needs at least 2 sermons and 2 non-Scripture evidence items with 20+ matched words",
      );
    }
  }
  if (finding.kind === "ai_writing" && finding.status === "flagged") {
    const shiftedSignals = evidence.filter((item) => item.type === "stylometric_shift").length;
    const corroborated = evidence.some((item) =>
      ["manuscript_published", "structural_similarity", "other"].includes(item.type),
    );
    if (shiftedSignals < 2 || !corroborated) {
      throw new Error(
        "a flagged AI-writing proposal needs at least 2 stylometric shifts and corroborating evidence",
      );
    }
  }
}

export const listTasks = internalQuery({
  args: { agentId: v.string(), limit: v.number(), now: v.number() },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(Math.floor(args.limit), 1), 100);
    const open = await ctx.db
      .query("researchTasks")
      .withIndex("by_status_and_priority", (q) => q.eq("status", "open"))
      .order("desc")
      .take(limit);
    const claimed = await ctx.db
      .query("researchTasks")
      .withIndex("by_claimedBy_and_status", (q) => q.eq("claimedBy", args.agentId))
      .order("desc")
      .take(limit);
    const expired = await ctx.db
      .query("researchTasks")
      .withIndex("by_status_and_leaseExpiresAt", (q) =>
        q.eq("status", "claimed").lt("leaseExpiresAt", args.now),
      )
      .take(limit);
    return [...claimed, ...open, ...expired].slice(0, limit);
  },
});

export const claimTask = internalMutation({
  args: {
    taskId: v.id("researchTasks"),
    agentId: v.string(),
    leaseMinutes: v.number(),
  },
  handler: async (ctx, args) => {
    const task = await ctx.db.get("researchTasks", args.taskId);
    if (!task) throw new Error("task not found");
    const now = Date.now();
    const leaseExpired = task.status === "claimed" && (task.leaseExpiresAt ?? 0) < now;
    const alreadyOwned = task.status === "claimed" && task.claimedBy === args.agentId;
    if (task.status !== "open" && !leaseExpired && !alreadyOwned) {
      throw new Error("task is not available");
    }
    const leaseMinutes = Math.min(Math.max(Math.floor(args.leaseMinutes), 5), 720);
    await ctx.db.patch("researchTasks", task._id, {
      status: "claimed",
      claimedBy: args.agentId,
      claimedAt: now,
      leaseExpiresAt: now + leaseMinutes * 60_000,
    });
    return { taskId: task._id, leaseExpiresAt: now + leaseMinutes * 60_000 };
  },
});

export const createUploadUrl = internalMutation({
  args: { agentId: v.string() },
  handler: async (ctx) => ({ uploadUrl: await ctx.storage.generateUploadUrl() }),
});

export const submit = internalMutation({
  args: {
    agentId: v.string(),
    submissionKey: v.string(),
    payloadHash: v.string(),
    schemaVersion: v.string(),
    rubricVersion: v.string(),
    taskId: v.optional(v.id("researchTasks")),
    churchSlug: v.string(),
    pastorName: v.string(),
    pastorRole: v.optional(v.string()),
    finding: submissionFinding,
    sources: v.array(submittedSource),
    evidence: v.array(submittedEvidence),
    artifacts: v.array(submittedArtifact),
    notes: v.optional(v.string()),
    attested: v.boolean(),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("submissions")
      .withIndex("by_submissionKey", (q) => q.eq("submissionKey", args.submissionKey))
      .unique();
    if (existing) {
      if (existing.agentId !== args.agentId) throw new Error("submission_key is already in use");
      if (existing.payloadHash !== args.payloadHash) {
        throw new Error("submission_key was already used with a different payload");
      }
      return { submissionId: existing._id, status: existing.status, duplicate: true };
    }
    if (!args.attested) {
      throw new Error("the agent must attest that the rubric and Scripture/liturgy exclusions were reviewed");
    }
    if (args.sources.length > MAX_SOURCES || args.evidence.length > MAX_EVIDENCE_ITEMS || args.artifacts.length > MAX_ARTIFACTS) {
      throw new Error("submission exceeds the allowed number of sources, evidence items, or artifacts");
    }
    validateFinding(args.finding, args.evidence);
    JSON.parse(args.finding.metricsJson);

    if (args.taskId) {
      const task = await ctx.db.get("researchTasks", args.taskId);
      if (!task) throw new Error("task not found");
      const acceptsAnotherFinding = task.scope === "both" && task.status === "submitted";
      if (task.claimedBy !== args.agentId || (task.status !== "claimed" && !acceptsAnotherFinding)) {
        throw new Error("task must be claimed by this agent before submission");
      }
      if ((task.leaseExpiresAt ?? 0) < Date.now()) throw new Error("task lease has expired");
      if (task.churchSlug !== args.churchSlug) throw new Error("submission does not match the claimed church");
    }

    for (const artifact of args.artifacts) {
      const metadata = await ctx.db.system.get("_storage", artifact.storageId);
      if (!metadata) throw new Error(`uploaded artifact ${artifact.fileName} was not found`);
      if (metadata.size > 50 * 1024 * 1024) throw new Error(`${artifact.fileName} exceeds the 50 MB artifact limit`);
      if (!artifact.contentType.startsWith("text/") && !["application/json", "application/pdf"].includes(artifact.contentType)) {
        throw new Error(`${artifact.fileName} has an unsupported content type`);
      }
    }

    const now = Date.now();
    const submissionId = await ctx.db.insert("submissions", {
      submissionKey: args.submissionKey,
      payloadHash: args.payloadHash,
      schemaVersion: `${args.schemaVersion}; rubric=${args.rubricVersion}`,
      taskId: args.taskId,
      churchSlug: args.churchSlug,
      pastorName: args.pastorName,
      pastorRole: args.pastorRole,
      agentId: args.agentId,
      status: "pending",
      findingKind: args.finding.kind,
      findingStatus: args.finding.status,
      findingConfidence: args.finding.confidence,
      summary: args.finding.summary,
      sermonsReviewed: args.finding.sermonsReviewed,
      periodFrom: args.finding.periodFrom,
      periodTo: args.finding.periodTo,
      methods: args.finding.methods,
      metricsJson: args.finding.metricsJson,
      notes: args.notes,
      submittedAt: now,
    });
    for (const source of args.sources) {
      await ctx.db.insert("submittedSources", { submissionId, ...source });
    }
    for (const item of args.evidence) {
      await ctx.db.insert("evidenceItems", { submissionId, ...item });
    }
    for (const artifact of args.artifacts) {
      await ctx.db.insert("artifacts", { submissionId, ...artifact });
    }
    await ctx.db.insert("reviewEvents", {
      submissionId,
      event: "submitted",
      actor: args.agentId,
      createdAt: now,
    });
    if (args.taskId) {
      await ctx.db.patch("researchTasks", args.taskId, { status: "submitted", submissionId });
    }
    return { submissionId, status: "pending" as const, duplicate: false };
  },
});

export const getSubmission = internalQuery({
  args: { submissionId: v.id("submissions"), agentId: v.string() },
  handler: async (ctx, args) => {
    const submission = await ctx.db.get("submissions", args.submissionId);
    if (!submission || submission.agentId !== args.agentId) return null;
    return submission;
  },
});

export const createTask = internalMutation({
  args: {
    taskKey: v.string(),
    churchSlug: v.string(),
    pastorName: v.optional(v.string()),
    scope: taskScope,
    priority: v.number(),
    instructions: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("researchTasks")
      .withIndex("by_taskKey", (q) => q.eq("taskKey", args.taskKey))
      .unique();
    if (existing) return { taskId: existing._id, duplicate: true };
    const taskId = await ctx.db.insert("researchTasks", {
      ...args,
      status: "open",
      createdAt: Date.now(),
    });
    return { taskId, duplicate: false };
  },
});
