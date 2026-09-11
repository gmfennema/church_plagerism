import { v } from "convex/values";
import { internalMutation, internalQuery } from "./_generated/server";
import type { Id } from "./_generated/dataModel";
import {
  findingKind,
  importedFinding,
  publicStatus,
  submissionStatus,
} from "./validators";

type FindingStatus = "unchecked" | "in_progress" | "cleared" | "flagged" | "inconclusive";
type PublicStatus = "unchecked" | "partial" | "in_progress" | "cleared" | "flagged";
type JsonObject = Record<string, unknown>;

function normalizedName(name: string) {
  return name.trim().toLocaleLowerCase("en-US").replace(/\s+/g, " ");
}

function aggregateKind(statuses: FindingStatus[]): PublicStatus {
  if (!statuses.length || statuses.every((status) => status === "unchecked")) return "unchecked";
  if (statuses.includes("flagged")) return "flagged";
  if (statuses.includes("in_progress")) return "in_progress";
  if (statuses.every((status) => status === "cleared")) return "cleared";
  return "partial";
}

function aggregateOverall(plagiarism: PublicStatus, ai: PublicStatus): PublicStatus {
  if (plagiarism === "flagged" || ai === "flagged") return "flagged";
  if (plagiarism === "in_progress" || ai === "in_progress") return "in_progress";
  if (plagiarism === "cleared" && ai === "cleared") return "cleared";
  if (plagiarism === "unchecked" && ai === "unchecked") return "unchecked";
  return "partial";
}

const importedPastor = v.object({
  name: v.string(),
  role: v.string(),
  active: v.boolean(),
  bioUrl: v.optional(v.string()),
  lastReviewed: v.optional(v.string()),
  reviewedBy: v.optional(v.string()),
  notes: v.optional(v.string()),
  plagiarism: importedFinding,
  aiWriting: importedFinding,
});

export const importChurch = internalMutation({
  args: {
    slug: v.string(),
    name: v.string(),
    aliases: v.array(v.string()),
    inScope: v.boolean(),
    tradition: v.string(),
    traditionLabel: v.string(),
    denomination: v.optional(v.string()),
    website: v.optional(v.string()),
    youtubeChannelUrl: v.optional(v.string()),
    sermonPlaylistUrls: v.array(v.string()),
    address: v.string(),
    city: v.string(),
    state: v.string(),
    postalCode: v.optional(v.string()),
    latitude: v.optional(v.number()),
    longitude: v.optional(v.number()),
    geocode: v.union(v.literal("verified"), v.literal("approximate"), v.literal("missing")),
    summary: v.optional(v.string()),
    notes: v.optional(v.string()),
    status: publicStatus,
    plagiarismStatus: publicStatus,
    aiStatus: publicStatus,
    updatedAt: v.string(),
    updatedBy: v.string(),
    sourceRecordJson: v.string(),
    pastors: v.array(importedPastor),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("churches")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .unique();
    const { pastors, ...churchFields } = args;
    let churchId: Id<"churches">;
    if (existing) {
      churchId = existing._id;
      await ctx.db.patch("churches", churchId, churchFields);
    } else {
      churchId = await ctx.db.insert("churches", churchFields);
    }

    for (const pastor of pastors) {
      const key = normalizedName(pastor.name);
      const existingPastor = await ctx.db
        .query("pastors")
        .withIndex("by_churchId_and_normalizedName", (q) =>
          q.eq("churchId", churchId).eq("normalizedName", key),
        )
        .unique();
      const { plagiarism, aiWriting, ...pastorFields } = pastor;
      let pastorId: Id<"pastors">;
      if (existingPastor) {
        pastorId = existingPastor._id;
        await ctx.db.patch("pastors", pastorId, { ...pastorFields, normalizedName: key });
      } else {
        pastorId = await ctx.db.insert("pastors", {
          churchId,
          normalizedName: key,
          ...pastorFields,
        });
      }
      for (const finding of [plagiarism, aiWriting]) {
        const current = await ctx.db
          .query("findings")
          .withIndex("by_pastorId_and_kind", (q) =>
            q.eq("pastorId", pastorId).eq("kind", finding.kind),
          )
          .unique();
        const fields = { pastorId, ...finding, updatedAt: Date.now() };
        if (current) await ctx.db.patch("findings", current._id, fields);
        else await ctx.db.insert("findings", fields);
      }
    }
    return { churchId, imported: true };
  },
});

export const listSubmissions = internalQuery({
  args: { status: v.optional(submissionStatus), limit: v.number() },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(Math.floor(args.limit), 1), 100);
    if (args.status) {
      return await ctx.db
        .query("submissions")
        .withIndex("by_status", (q) => q.eq("status", args.status!))
        .order("desc")
        .take(limit);
    }
    return await ctx.db.query("submissions").order("desc").take(limit);
  },
});

export const reviewSubmission = internalMutation({
  args: {
    submissionId: v.id("submissions"),
    decision: v.union(
      v.literal("approved"),
      v.literal("changes_requested"),
      v.literal("rejected"),
    ),
    reviewer: v.string(),
    notes: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const submission = await ctx.db.get("submissions", args.submissionId);
    if (!submission) throw new Error("submission not found");
    if (submission.status === "approved") throw new Error("approved submissions are immutable");
    const now = Date.now();

    if (args.decision !== "approved") {
      await ctx.db.patch("submissions", submission._id, {
        status: args.decision,
        reviewedAt: now,
        reviewedBy: args.reviewer,
        reviewNotes: args.notes,
      });
      await ctx.db.insert("reviewEvents", {
        submissionId: submission._id,
        event: args.decision,
        actor: args.reviewer,
        notes: args.notes,
        createdAt: now,
      });
      return { submissionId: submission._id, status: args.decision };
    }

    const church = await ctx.db
      .query("churches")
      .withIndex("by_slug", (q) => q.eq("slug", submission.churchSlug))
      .unique();
    if (!church) throw new Error("church must be imported before a finding can be approved");
    const pastorKey = normalizedName(submission.pastorName);
    let pastor = await ctx.db
      .query("pastors")
      .withIndex("by_churchId_and_normalizedName", (q) =>
        q.eq("churchId", church._id).eq("normalizedName", pastorKey),
      )
      .unique();
    if (!pastor) {
      const pastorId = await ctx.db.insert("pastors", {
        churchId: church._id,
        normalizedName: pastorKey,
        name: submission.pastorName,
        role: submission.pastorRole ?? "Preaching pastor",
        active: true,
        lastReviewed: new Date(now).toISOString().slice(0, 10),
        reviewedBy: args.reviewer,
      });
      pastor = await ctx.db.get("pastors", pastorId);
    }
    if (!pastor) throw new Error("pastor could not be created");

    const existingFinding = await ctx.db
      .query("findings")
      .withIndex("by_pastorId_and_kind", (q) =>
        q.eq("pastorId", pastor!._id).eq("kind", submission.findingKind),
      )
      .unique();
    const findingFields = {
      pastorId: pastor._id,
      kind: submission.findingKind,
      status: submission.findingStatus,
      confidence: submission.findingConfidence,
      summary: submission.summary,
      sermonsReviewed: submission.sermonsReviewed,
      periodFrom: submission.periodFrom,
      periodTo: submission.periodTo,
      methods: submission.methods,
      metricsJson: submission.metricsJson,
      sourceSubmissionId: submission._id,
      publishedAt: now,
      updatedAt: now,
    };
    let findingId: Id<"findings">;
    if (existingFinding) {
      findingId = existingFinding._id;
      await ctx.db.replace("findings", findingId, findingFields);
    } else {
      findingId = await ctx.db.insert("findings", findingFields);
    }

    const evidence = await ctx.db
      .query("evidenceItems")
      .withIndex("by_submissionId", (q) => q.eq("submissionId", submission._id))
      .take(100);
    const sources = await ctx.db
      .query("submittedSources")
      .withIndex("by_submissionId", (q) => q.eq("submissionId", submission._id))
      .take(40);
    const artifacts = await ctx.db
      .query("artifacts")
      .withIndex("by_submissionId", (q) => q.eq("submissionId", submission._id))
      .take(30);
    for (const item of evidence) await ctx.db.patch("evidenceItems", item._id, { findingId });
    for (const item of sources) await ctx.db.patch("submittedSources", item._id, { findingId });
    for (const item of artifacts) await ctx.db.patch("artifacts", item._id, { findingId });

    const allPastors = await ctx.db
      .query("pastors")
      .withIndex("by_churchId", (q) => q.eq("churchId", church._id))
      .take(100);
    const plagiarismStatuses: FindingStatus[] = [];
    const aiStatuses: FindingStatus[] = [];
    for (const person of allPastors.filter((item) => item.active)) {
      const findings = await ctx.db
        .query("findings")
        .withIndex("by_pastorId_and_kind", (q) => q.eq("pastorId", person._id))
        .take(4);
      plagiarismStatuses.push(findings.find((item) => item.kind === "plagiarism")?.status ?? "unchecked");
      aiStatuses.push(findings.find((item) => item.kind === "ai_writing")?.status ?? "unchecked");
    }
    const plagiarismStatus = aggregateKind(plagiarismStatuses);
    const aiStatus = aggregateKind(aiStatuses);
    const status = aggregateOverall(plagiarismStatus, aiStatus);

    let record: JsonObject = {};
    try {
      record = JSON.parse(church.sourceRecordJson ?? "{}") as JsonObject;
    } catch {
      record = {};
    }
    const rawPastors = Array.isArray(record.pastors) ? (record.pastors as JsonObject[]) : [];
    let rawPastor = rawPastors.find(
      (item) => typeof item.name === "string" && normalizedName(item.name) === pastorKey,
    );
    if (!rawPastor) {
      rawPastor = { name: submission.pastorName, role: submission.pastorRole ?? "Preaching pastor", active: true };
      rawPastors.push(rawPastor);
    }
    const findingKey = submission.findingKind === "ai_writing" ? "ai_writing" : "plagiarism";
    rawPastor[findingKey] = {
      status: submission.findingStatus,
      confidence: submission.findingConfidence,
      summary: submission.summary,
      sermons_reviewed: submission.sermonsReviewed,
      review_period: submission.periodFrom || submission.periodTo
        ? { from: submission.periodFrom, to: submission.periodTo }
        : undefined,
      methods: submission.methods,
      metrics: JSON.parse(submission.metricsJson),
      sources_compared: sources.map((source) => ({
        author: source.author,
        title: source.title,
        url: source.url,
        attributed_in_sermon: source.attributedInSermon,
      })),
      evidence: evidence.map((item) => ({
        type: item.type,
        description: item.description,
        sermon_title: item.sermonTitle,
        sermon_date: item.sermonDate,
        sermon_url: item.sermonUrl,
        sermon_excerpt: item.sermonExcerpt,
        timestamp: item.sermonTimestamp,
        source_author: item.sourceAuthor,
        source_title: item.sourceTitle,
        source_url: item.sourceUrl,
        source_excerpt: item.sourceExcerpt,
        matched_words: item.matchedWords,
        scripture_excluded: item.scriptureExcluded,
        attribution_status: item.attributionStatus,
        metric: item.metricName ? { name: item.metricName, value: item.metricValue } : undefined,
      })),
    };
    rawPastor.last_reviewed = new Date(now).toISOString().slice(0, 10);
    rawPastor.reviewed_by = args.reviewer;
    record.pastors = rawPastors;
    record.status = status;
    record.plagiarism_status = plagiarismStatus;
    record.ai_status = aiStatus;
    record.updated_at = new Date(now).toISOString().slice(0, 10);
    record.updated_by = args.reviewer;

    await ctx.db.patch("churches", church._id, {
      status,
      plagiarismStatus,
      aiStatus,
      sourceRecordJson: JSON.stringify(record),
      updatedAt: new Date(now).toISOString().slice(0, 10),
      updatedBy: args.reviewer,
    });
    await ctx.db.patch("submissions", submission._id, {
      status: "approved",
      reviewedAt: now,
      reviewedBy: args.reviewer,
      reviewNotes: args.notes,
    });
    if (submission.taskId) {
      const task = await ctx.db.get("researchTasks", submission.taskId);
      if (task?.scope === "both") {
        const siblings = await ctx.db
          .query("submissions")
          .withIndex("by_taskId", (q) => q.eq("taskId", submission.taskId))
          .take(10);
        const approvedKinds = new Set(
          siblings
            .filter((item) => item.status === "approved" || item._id === submission._id)
            .map((item) => item.findingKind),
        );
        await ctx.db.patch("researchTasks", submission.taskId, {
          status: approvedKinds.has("plagiarism") && approvedKinds.has("ai_writing") ? "complete" : "submitted",
        });
      } else {
        await ctx.db.patch("researchTasks", submission.taskId, { status: "complete" });
      }
    }
    await ctx.db.insert("reviewEvents", {
      submissionId: submission._id,
      event: "approved",
      actor: args.reviewer,
      notes: args.notes,
      createdAt: now,
    });
    return { submissionId: submission._id, findingId, status: "approved" as const };
  },
});
