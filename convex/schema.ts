import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";
import {
  artifactKind,
  confidence,
  evidenceType,
  findingKind,
  findingStatus,
  publicStatus,
  submissionStatus,
  taskScope,
  taskStatus,
} from "./validators";

export default defineSchema({
  churches: defineTable({
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
    sourceRecordJson: v.optional(v.string()),
  }).index("by_slug", ["slug"]),

  pastors: defineTable({
    churchId: v.id("churches"),
    normalizedName: v.string(),
    name: v.string(),
    role: v.string(),
    active: v.boolean(),
    bioUrl: v.optional(v.string()),
    lastReviewed: v.optional(v.string()),
    reviewedBy: v.optional(v.string()),
    notes: v.optional(v.string()),
  })
    .index("by_churchId", ["churchId"])
    .index("by_churchId_and_normalizedName", ["churchId", "normalizedName"]),

  sermons: defineTable({
    churchId: v.id("churches"),
    pastorId: v.optional(v.id("pastors")),
    externalKey: v.string(),
    title: v.string(),
    mediaUrl: v.string(),
    deliveredAt: v.optional(v.string()),
    series: v.optional(v.string()),
    scripturePassage: v.optional(v.string()),
    speakerVerification: v.union(
      v.literal("confirmed"),
      v.literal("probable"),
      v.literal("unverified"),
    ),
    createdBy: v.string(),
  })
    .index("by_churchId", ["churchId"])
    .index("by_externalKey", ["externalKey"]),

  transcripts: defineTable({
    sermonId: v.id("sermons"),
    storageId: v.id("_storage"),
    source: v.union(v.literal("captions"), v.literal("manual"), v.literal("speech_to_text")),
    language: v.string(),
    completeness: v.union(v.literal("complete"), v.literal("partial"), v.literal("unknown")),
    wordCount: v.optional(v.number()),
    createdBy: v.string(),
  }).index("by_sermonId", ["sermonId"]),

  findings: defineTable({
    pastorId: v.id("pastors"),
    kind: findingKind,
    status: findingStatus,
    confidence: v.optional(confidence),
    summary: v.optional(v.string()),
    sermonsReviewed: v.number(),
    periodFrom: v.optional(v.string()),
    periodTo: v.optional(v.string()),
    methods: v.array(v.string()),
    metricsJson: v.string(),
    sourceSubmissionId: v.optional(v.id("submissions")),
    publishedAt: v.optional(v.number()),
    updatedAt: v.number(),
  }).index("by_pastorId_and_kind", ["pastorId", "kind"]),

  researchTasks: defineTable({
    taskKey: v.string(),
    churchSlug: v.string(),
    pastorName: v.optional(v.string()),
    scope: taskScope,
    status: taskStatus,
    priority: v.number(),
    instructions: v.optional(v.string()),
    claimedBy: v.optional(v.string()),
    claimedAt: v.optional(v.number()),
    leaseExpiresAt: v.optional(v.number()),
    submissionId: v.optional(v.id("submissions")),
    createdAt: v.number(),
  })
    .index("by_taskKey", ["taskKey"])
    .index("by_status_and_priority", ["status", "priority"])
    .index("by_status_and_leaseExpiresAt", ["status", "leaseExpiresAt"])
    .index("by_claimedBy_and_status", ["claimedBy", "status"]),

  submissions: defineTable({
    submissionKey: v.string(),
    payloadHash: v.string(),
    schemaVersion: v.string(),
    taskId: v.optional(v.id("researchTasks")),
    churchSlug: v.string(),
    pastorName: v.string(),
    pastorRole: v.optional(v.string()),
    agentId: v.string(),
    status: submissionStatus,
    findingKind,
    findingStatus,
    findingConfidence: v.optional(confidence),
    summary: v.string(),
    sermonsReviewed: v.number(),
    periodFrom: v.optional(v.string()),
    periodTo: v.optional(v.string()),
    methods: v.array(v.string()),
    metricsJson: v.string(),
    notes: v.optional(v.string()),
    submittedAt: v.number(),
    reviewedAt: v.optional(v.number()),
    reviewedBy: v.optional(v.string()),
    reviewNotes: v.optional(v.string()),
  })
    .index("by_submissionKey", ["submissionKey"])
    .index("by_status", ["status"])
    .index("by_taskId", ["taskId"])
    .index("by_agentId_and_submittedAt", ["agentId", "submittedAt"]),

  submittedSources: defineTable({
    submissionId: v.id("submissions"),
    findingId: v.optional(v.id("findings")),
    author: v.string(),
    title: v.string(),
    url: v.optional(v.string()),
    attributedInSermon: v.optional(v.union(v.boolean(), v.null())),
  }).index("by_submissionId", ["submissionId"]),

  evidenceItems: defineTable({
    submissionId: v.id("submissions"),
    findingId: v.optional(v.id("findings")),
    type: evidenceType,
    description: v.string(),
    sermonTitle: v.optional(v.string()),
    sermonDate: v.optional(v.string()),
    sermonUrl: v.optional(v.string()),
    sermonExcerpt: v.optional(v.string()),
    sermonTimestamp: v.optional(v.string()),
    sourceAuthor: v.optional(v.string()),
    sourceTitle: v.optional(v.string()),
    sourceUrl: v.optional(v.string()),
    sourceExcerpt: v.optional(v.string()),
    matchedWords: v.optional(v.number()),
    metricName: v.optional(v.string()),
    metricValue: v.optional(v.union(v.number(), v.string())),
    scriptureExcluded: v.optional(v.boolean()),
    attributionStatus: v.optional(
      v.union(v.literal("found"), v.literal("not_found"), v.literal("not_checked")),
    ),
  })
    .index("by_submissionId", ["submissionId"])
    .index("by_findingId", ["findingId"]),

  artifacts: defineTable({
    submissionId: v.id("submissions"),
    findingId: v.optional(v.id("findings")),
    storageId: v.id("_storage"),
    kind: artifactKind,
    fileName: v.string(),
    contentType: v.string(),
    sermonUrl: v.optional(v.string()),
    description: v.optional(v.string()),
  }).index("by_submissionId", ["submissionId"]),

  reviewEvents: defineTable({
    submissionId: v.id("submissions"),
    event: v.union(
      v.literal("submitted"),
      v.literal("approved"),
      v.literal("changes_requested"),
      v.literal("rejected"),
    ),
    actor: v.string(),
    notes: v.optional(v.string()),
    createdAt: v.number(),
  }).index("by_submissionId", ["submissionId"]),
});
