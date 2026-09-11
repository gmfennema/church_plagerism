import { httpRouter } from "convex/server";
import { httpAction, env } from "./_generated/server";
import { internal } from "./_generated/api";
import type { Id } from "./_generated/dataModel";

type JsonObject = Record<string, unknown>;
type FindingStatus = "unchecked" | "in_progress" | "cleared" | "flagged" | "inconclusive";
type PublicStatus = "unchecked" | "partial" | "in_progress" | "cleared" | "flagged";

class RequestError extends Error {
  constructor(
    message: string,
    readonly status = 400,
  ) {
    super(message);
  }
}

function json(value: unknown, status = 200, extraHeaders: Record<string, string> = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      ...extraHeaders,
    },
  });
}

function publicJson(value: unknown) {
  return json(value, 200, {
    "access-control-allow-origin": "*",
    "cache-control": "public, max-age=60, stale-while-revalidate=300",
  });
}

function asObject(value: unknown, label = "request body"): JsonObject {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new RequestError(`${label} must be a JSON object`);
  }
  return value as JsonObject;
}

function requiredString(object: JsonObject, key: string, max = 2_000) {
  const value = object[key];
  if (typeof value !== "string" || !value.trim()) {
    throw new RequestError(`${key} is required and must be a string`);
  }
  if (value.length > max) throw new RequestError(`${key} is too long`);
  return value.trim();
}

function optionalString(object: JsonObject, key: string, max = 10_000) {
  const value = object[key];
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value !== "string") throw new RequestError(`${key} must be a string`);
  if (value.length > max) throw new RequestError(`${key} is too long`);
  return value;
}

function requiredNumber(object: JsonObject, key: string) {
  const value = object[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new RequestError(`${key} is required and must be a finite number`);
  }
  return value;
}

function optionalNumber(object: JsonObject, key: string) {
  const value = object[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new RequestError(`${key} must be a finite number`);
  }
  return value;
}

function optionalBoolean(object: JsonObject, key: string) {
  const value = object[key];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "boolean") throw new RequestError(`${key} must be a boolean`);
  return value;
}

function stringArray(value: unknown, key: string, maxItems = 100) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.length > maxItems || value.some((item) => typeof item !== "string")) {
    throw new RequestError(`${key} must be an array of strings with at most ${maxItems} items`);
  }
  return value as string[];
}

function oneOf<T extends string>(value: unknown, key: string, values: readonly T[]): T {
  if (typeof value !== "string" || !values.includes(value as T)) {
    throw new RequestError(`${key} must be one of: ${values.join(", ")}`);
  }
  return value as T;
}

function compact<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function body(request: Request) {
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  if (contentLength > 512_000) throw new RequestError("JSON request body exceeds 500 KB", 413);
  try {
    return asObject(await request.json());
  } catch (error) {
    if (error instanceof RequestError) throw error;
    throw new RequestError("request body must be valid JSON");
  }
}

async function safeEqual(left: string, right: string) {
  const encoder = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(left)),
    crypto.subtle.digest("SHA-256", encoder.encode(right)),
  ]);
  const aa = new Uint8Array(a);
  const bb = new Uint8Array(b);
  let difference = 0;
  for (let index = 0; index < aa.length; index += 1) difference |= aa[index] ^ bb[index];
  return difference === 0;
}

async function hashJson(value: unknown) {
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(value))));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function bearer(request: Request) {
  const header = request.headers.get("authorization") ?? "";
  if (!header.startsWith("Bearer ")) throw new RequestError("missing bearer token", 401);
  return header.slice(7);
}

async function requireAgent(request: Request) {
  const configured = env.RESEARCH_API_KEYS;
  if (!configured) throw new RequestError("agent API keys are not configured", 503);
  let keys: Record<string, string>;
  try {
    keys = JSON.parse(configured) as Record<string, string>;
  } catch {
    throw new RequestError("agent API key configuration is invalid", 503);
  }
  const token = bearer(request);
  const separator = token.indexOf(":");
  if (separator < 1) throw new RequestError("invalid bearer token", 401);
  const agentId = token.slice(0, separator);
  const secret = token.slice(separator + 1);
  if (typeof keys[agentId] !== "string" || !(await safeEqual(keys[agentId], secret))) {
    throw new RequestError("invalid bearer token", 401);
  }
  return agentId;
}

async function requireAdmin(request: Request) {
  if (!env.ADMIN_API_KEY) throw new RequestError("admin API key is not configured", 503);
  const token = bearer(request);
  const secret = token.startsWith("admin:") ? token.slice(6) : token;
  if (!(await safeEqual(env.ADMIN_API_KEY, secret))) throw new RequestError("invalid bearer token", 401);
  return "admin";
}

const http = httpRouter();

http.route({
  path: "/api/v1/health",
  method: "GET",
  handler: httpAction(async () => publicJson({ ok: true, service: "tucson-sermon-integrity-api", version: "1" })),
});

http.route({
  path: "/api/v1/public/churches",
  method: "GET",
  handler: httpAction(async (ctx) => publicJson(await ctx.runQuery(internal.publicData.snapshot, { limit: 500 }))),
});

http.route({
  path: "/api/v1/tasks",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    try {
      const agentId = await requireAgent(request);
      const url = new URL(request.url);
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const tasks = await ctx.runQuery(internal.research.listTasks, { agentId, limit, now: Date.now() });
      return json({ tasks });
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/tasks/claim",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const agentId = await requireAgent(request);
      const input = await body(request);
      const result = await ctx.runMutation(internal.research.claimTask, {
        taskId: requiredString(input, "task_id") as Id<"researchTasks">,
        agentId,
        leaseMinutes: optionalNumber(input, "lease_minutes") ?? 120,
      });
      return json(result);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/uploads",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const agentId = await requireAgent(request);
      return json(await ctx.runMutation(internal.research.createUploadUrl, { agentId }));
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/submissions",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const agentId = await requireAgent(request);
      const input = await body(request);
      const finding = asObject(input.finding, "finding");
      const period = input.review_period === undefined ? {} : asObject(input.review_period, "review_period");
      const sourceValues = Array.isArray(input.sources_compared) ? input.sources_compared : [];
      const evidenceValues = Array.isArray(input.evidence) ? input.evidence : [];
      const artifactValues = Array.isArray(input.artifacts) ? input.artifacts : [];
      const sources = sourceValues.map((value, index) => {
        const source = asObject(value, `sources_compared[${index}]`);
        const attributed = source.attributed_in_sermon;
        if (attributed !== undefined && attributed !== null && typeof attributed !== "boolean") {
          throw new RequestError(`sources_compared[${index}].attributed_in_sermon must be boolean or null`);
        }
        return compact({
          author: requiredString(source, "author"),
          title: requiredString(source, "title"),
          url: optionalString(source, "url"),
          attributedInSermon: attributed as boolean | null | undefined,
        });
      });
      const evidence = evidenceValues.map((value, index) => {
        const item = asObject(value, `evidence[${index}]`);
        return compact({
          type: oneOf(item.type, `evidence[${index}].type`, [
            "verbatim_overlap", "paraphrase_overlap", "structural_similarity", "attribution_present",
            "attribution_absent", "ai_phrase_density", "stylometric_shift", "low_disfluency",
            "manuscript_published", "other",
          ] as const),
          description: requiredString(item, "description", 4_000),
          sermonTitle: optionalString(item, "sermon_title"),
          sermonDate: optionalString(item, "sermon_date"),
          sermonUrl: optionalString(item, "sermon_url"),
          sermonExcerpt: optionalString(item, "sermon_excerpt", 2_000),
          sermonTimestamp: optionalString(item, "sermon_timestamp"),
          sourceAuthor: optionalString(item, "source_author"),
          sourceTitle: optionalString(item, "source_title"),
          sourceUrl: optionalString(item, "source_url"),
          sourceExcerpt: optionalString(item, "source_excerpt", 2_000),
          matchedWords: optionalNumber(item, "matched_words"),
          metricName: optionalString(item, "metric_name"),
          metricValue: typeof item.metric_value === "number" || typeof item.metric_value === "string"
            ? item.metric_value
            : undefined,
          scriptureExcluded: optionalBoolean(item, "scripture_excluded"),
          attributionStatus: item.attribution_status === undefined
            ? undefined
            : oneOf(item.attribution_status, "attribution_status", ["found", "not_found", "not_checked"] as const),
        });
      });
      const artifacts = artifactValues.map((value, index) => {
        const artifact = asObject(value, `artifacts[${index}]`);
        return compact({
          storageId: requiredString(artifact, "storage_id") as Id<"_storage">,
          kind: oneOf(artifact.kind, "kind", [
            "transcript", "source_transcript", "comparison_report", "ai_signal_report",
            "research_notes", "other",
          ] as const),
          fileName: requiredString(artifact, "file_name"),
          contentType: requiredString(artifact, "content_type"),
          sermonUrl: optionalString(artifact, "sermon_url"),
          description: optionalString(artifact, "description"),
        });
      });
      const metrics = finding.metrics ?? {};
      if (!metrics || typeof metrics !== "object" || Array.isArray(metrics)) {
        throw new RequestError("finding.metrics must be an object");
      }
      const confidence = finding.confidence === undefined || finding.confidence === null
        ? undefined
        : oneOf(finding.confidence, "finding.confidence", ["low", "medium", "high"] as const);
      const attestation = asObject(input.attestation, "attestation");
      const attested = attestation.rubric_reviewed === true && attestation.scripture_liturgy_exclusions_reviewed === true;
      const submissionArgs = compact({
        agentId,
        submissionKey: requiredString(input, "submission_key"),
        schemaVersion: requiredString(input, "schema_version"),
        rubricVersion: requiredString(input, "rubric_version"),
        taskId: optionalString(input, "task_id") as Id<"researchTasks"> | undefined,
        churchSlug: requiredString(input, "church_slug"),
        pastorName: requiredString(input, "pastor_name"),
        pastorRole: optionalString(input, "pastor_role"),
        finding: compact({
          kind: oneOf(finding.kind, "finding.kind", ["plagiarism", "ai_writing"] as const),
          status: oneOf(finding.status, "finding.status", ["cleared", "flagged", "inconclusive"] as const),
          confidence,
          summary: requiredString(finding, "summary", 8_000),
          sermonsReviewed: requiredNumber(finding, "sermons_reviewed"),
          periodFrom: optionalString(period, "from"),
          periodTo: optionalString(period, "to"),
          methods: stringArray(finding.methods, "finding.methods", 30),
          metricsJson: JSON.stringify(metrics),
        }),
        sources,
        evidence,
        artifacts,
        notes: optionalString(input, "notes", 20_000),
        attested,
      });
      const result = await ctx.runMutation(internal.research.submit, {
        ...submissionArgs,
        payloadHash: await hashJson(submissionArgs),
      });
      return json(result, result.duplicate ? 200 : 201);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/submissions/status",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    try {
      const agentId = await requireAgent(request);
      const id = new URL(request.url).searchParams.get("id");
      if (!id) throw new RequestError("id query parameter is required");
      const submission = await ctx.runQuery(internal.research.getSubmission, {
        submissionId: id as Id<"submissions">,
        agentId,
      });
      return submission ? json({ submission }) : json({ error: "submission not found" }, 404);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/admin/tasks",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      await requireAdmin(request);
      const input = await body(request);
      const result = await ctx.runMutation(internal.research.createTask, compact({
        taskKey: requiredString(input, "task_key"),
        churchSlug: requiredString(input, "church_slug"),
        pastorName: optionalString(input, "pastor_name"),
        scope: oneOf(input.scope, "scope", ["church_profile", "plagiarism", "ai_writing", "both"] as const),
        priority: optionalNumber(input, "priority") ?? 0,
        instructions: optionalString(input, "instructions", 20_000),
      }));
      return json(result, result.duplicate ? 200 : 201);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/admin/submissions",
  method: "GET",
  handler: httpAction(async (ctx, request) => {
    try {
      await requireAdmin(request);
      const url = new URL(request.url);
      const rawStatus = url.searchParams.get("status");
      const status = rawStatus
        ? oneOf(rawStatus, "status", ["pending", "approved", "changes_requested", "rejected"] as const)
        : undefined;
      return json({ submissions: await ctx.runQuery(internal.admin.listSubmissions, {
        status,
        limit: Number(url.searchParams.get("limit") ?? 50),
      }) });
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/admin/reviews",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      const reviewer = await requireAdmin(request);
      const input = await body(request);
      const result = await ctx.runMutation(internal.admin.reviewSubmission, compact({
        submissionId: requiredString(input, "submission_id") as Id<"submissions">,
        decision: oneOf(input.decision, "decision", ["approved", "changes_requested", "rejected"] as const),
        reviewer: optionalString(input, "reviewer") ?? reviewer,
        notes: optionalString(input, "notes", 20_000),
      }));
      return json(result);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

http.route({
  path: "/api/v1/admin/import-church",
  method: "POST",
  handler: httpAction(async (ctx, request) => {
    try {
      await requireAdmin(request);
      const input = await body(request);
      const location = asObject(input.location, "location");
      const youtube = input.youtube ? asObject(input.youtube, "youtube") : {};
      const pastorValues = Array.isArray(input.pastors) ? input.pastors : [];
      const aggregate = (statuses: FindingStatus[]): PublicStatus => {
        if (!statuses.length || statuses.every((value) => value === "unchecked")) return "unchecked";
        if (statuses.includes("flagged")) return "flagged";
        if (statuses.includes("in_progress")) return "in_progress";
        if (statuses.every((value) => value === "cleared")) return "cleared";
        return "partial";
      };
      const parseFinding = (value: unknown, kind: "plagiarism" | "ai_writing") => {
        const finding = value ? asObject(value, `${kind} finding`) : { status: "unchecked" };
        const reviewPeriod = finding.review_period ? asObject(finding.review_period, "review_period") : {};
        return compact({
          kind,
          status: oneOf(finding.status, "status", ["unchecked", "in_progress", "cleared", "flagged", "inconclusive"] as const),
          confidence: finding.confidence === undefined || finding.confidence === null
            ? undefined
            : oneOf(finding.confidence, "confidence", ["low", "medium", "high"] as const),
          summary: optionalString(finding, "summary", 20_000),
          sermonsReviewed: optionalNumber(finding, "sermons_reviewed") ?? 0,
          periodFrom: optionalString(reviewPeriod, "from"),
          periodTo: optionalString(reviewPeriod, "to"),
          methods: stringArray(finding.methods, "methods", 30),
          metricsJson: JSON.stringify(finding.metrics ?? {}),
        });
      };
      const pastors = pastorValues.map((value, index) => {
        const pastor = asObject(value, `pastors[${index}]`);
        return compact({
          name: requiredString(pastor, "name"),
          role: requiredString(pastor, "role"),
          active: pastor.active !== false,
          bioUrl: optionalString(pastor, "bio_url"),
          lastReviewed: optionalString(pastor, "last_reviewed"),
          reviewedBy: optionalString(pastor, "reviewed_by"),
          notes: optionalString(pastor, "notes", 20_000),
          plagiarism: parseFinding(pastor.plagiarism, "plagiarism"),
          aiWriting: parseFinding(pastor.ai_writing, "ai_writing"),
        });
      });
      const plagiarismStatus = aggregate(pastors.map((pastor) => pastor.plagiarism.status));
      const aiStatus = aggregate(pastors.map((pastor) => pastor.aiWriting.status));
      const status = oneOf(input.status ?? "unchecked", "status", ["unchecked", "partial", "in_progress", "cleared", "flagged"] as const);
      const result = await ctx.runMutation(internal.admin.importChurch, compact({
        slug: requiredString(input, "slug"),
        name: requiredString(input, "name"),
        aliases: stringArray(input.aka, "aka", 30),
        inScope: input.in_scope !== false,
        tradition: requiredString(input, "tradition"),
        traditionLabel: optionalString(input, "tradition_label") ?? requiredString(input, "tradition"),
        denomination: optionalString(input, "denomination"),
        website: optionalString(input, "website"),
        youtubeChannelUrl: optionalString(youtube, "channel_url"),
        sermonPlaylistUrls: stringArray(youtube.sermon_playlist_urls, "sermon_playlist_urls", 50),
        address: requiredString(location, "address"),
        city: requiredString(location, "city"),
        state: requiredString(location, "state"),
        postalCode: optionalString(location, "postal_code"),
        latitude: optionalNumber(location, "lat"),
        longitude: optionalNumber(location, "lng"),
        geocode: oneOf(location.geocode, "geocode", ["verified", "approximate", "missing"] as const),
        summary: optionalString(input, "summary", 20_000),
        notes: optionalString(input, "notes", 30_000),
        status,
        plagiarismStatus,
        aiStatus,
        updatedAt: requiredString(input, "updated_at"),
        updatedBy: requiredString(input, "updated_by"),
        sourceRecordJson: JSON.stringify(input),
        pastors,
      }));
      return json(result);
    } catch (error) {
      const status = error instanceof RequestError ? error.status : 400;
      return json({ error: error instanceof Error ? error.message : "request failed" }, status);
    }
  }),
});

export default http;
