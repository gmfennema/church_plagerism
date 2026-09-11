import { v } from "convex/values";

export const findingKind = v.union(
  v.literal("plagiarism"),
  v.literal("ai_writing"),
);

export const taskScope = v.union(
  v.literal("church_profile"),
  v.literal("plagiarism"),
  v.literal("ai_writing"),
  v.literal("both"),
);

export const findingStatus = v.union(
  v.literal("unchecked"),
  v.literal("in_progress"),
  v.literal("cleared"),
  v.literal("flagged"),
  v.literal("inconclusive"),
);

export const publicStatus = v.union(
  v.literal("unchecked"),
  v.literal("partial"),
  v.literal("in_progress"),
  v.literal("cleared"),
  v.literal("flagged"),
);

export const confidence = v.union(
  v.literal("low"),
  v.literal("medium"),
  v.literal("high"),
);

export const submissionStatus = v.union(
  v.literal("pending"),
  v.literal("approved"),
  v.literal("changes_requested"),
  v.literal("rejected"),
);

export const taskStatus = v.union(
  v.literal("open"),
  v.literal("claimed"),
  v.literal("submitted"),
  v.literal("complete"),
  v.literal("cancelled"),
);

export const evidenceType = v.union(
  v.literal("verbatim_overlap"),
  v.literal("paraphrase_overlap"),
  v.literal("structural_similarity"),
  v.literal("attribution_present"),
  v.literal("attribution_absent"),
  v.literal("ai_phrase_density"),
  v.literal("stylometric_shift"),
  v.literal("low_disfluency"),
  v.literal("manuscript_published"),
  v.literal("other"),
);

export const artifactKind = v.union(
  v.literal("transcript"),
  v.literal("source_transcript"),
  v.literal("comparison_report"),
  v.literal("ai_signal_report"),
  v.literal("research_notes"),
  v.literal("other"),
);

export const submissionFinding = v.object({
  kind: findingKind,
  status: findingStatus,
  confidence: v.optional(confidence),
  summary: v.string(),
  sermonsReviewed: v.number(),
  periodFrom: v.optional(v.string()),
  periodTo: v.optional(v.string()),
  methods: v.array(v.string()),
  metricsJson: v.string(),
});

export const importedFinding = v.object({
  kind: findingKind,
  status: findingStatus,
  confidence: v.optional(confidence),
  summary: v.optional(v.string()),
  sermonsReviewed: v.number(),
  periodFrom: v.optional(v.string()),
  periodTo: v.optional(v.string()),
  methods: v.array(v.string()),
  metricsJson: v.string(),
});

export const submittedSource = v.object({
  author: v.string(),
  title: v.string(),
  url: v.optional(v.string()),
  attributedInSermon: v.optional(v.union(v.boolean(), v.null())),
});

export const submittedEvidence = v.object({
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
});

export const submittedArtifact = v.object({
  storageId: v.id("_storage"),
  kind: artifactKind,
  fileName: v.string(),
  contentType: v.string(),
  sermonUrl: v.optional(v.string()),
  description: v.optional(v.string()),
});
