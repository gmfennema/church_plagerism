import { internalQuery } from "./_generated/server";
import { v } from "convex/values";

type JsonObject = Record<string, unknown>;

function attachReportUrls(record: JsonObject) {
  const slug = String(record.slug ?? "");
  const addUrls = (reports: unknown) => {
    if (!Array.isArray(reports)) return [];
    return reports.map((value) => {
      const report = value as JsonObject;
      const path = String(report.path ?? "");
      const prefix = `research/${slug}/`;
      return {
        ...report,
        url: path.startsWith(prefix) ? `reports/${slug}/${path.slice(prefix.length)}` : path,
        size_bytes: Number(report.size_bytes ?? 0),
      };
    });
  };
  record.reports = addUrls(record.reports);
  if (Array.isArray(record.pastors)) {
    record.pastors = (record.pastors as JsonObject[]).map((pastor) => ({
      ...pastor,
      reports: addUrls(pastor.reports),
    }));
  }
  return record;
}

export const snapshot = internalQuery({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(Math.floor(args.limit ?? 200), 1), 500);
    const docs = await ctx.db.query("churches").take(limit);
    const churches = docs
      .filter((doc) => doc.inScope)
      .map((doc) => {
        let record: JsonObject;
        try {
          record = JSON.parse(doc.sourceRecordJson ?? "{}") as JsonObject;
        } catch {
          record = {};
        }
        return attachReportUrls({
          ...record,
          slug: doc.slug,
          name: doc.name,
          status: doc.status,
          plagiarism_status: doc.plagiarismStatus,
          ai_status: doc.aiStatus,
          plotted: doc.latitude !== undefined && doc.longitude !== undefined,
        });
      })
      .sort((a, b) => String(a.name).localeCompare(String(b.name)));
    const counts = { unchecked: 0, partial: 0, in_progress: 0, cleared: 0, flagged: 0 };
    for (const church of churches) {
      const status = String(church.status) as keyof typeof counts;
      if (status in counts) counts[status] += 1;
    }
    return {
      generated_at: new Date(Math.max(0, ...docs.map((doc) => doc._creationTime))).toISOString(),
      church_count: churches.length,
      plotted_count: churches.filter((church) => church.plotted).length,
      pastor_count: churches.reduce(
        (sum, church) => sum + (Array.isArray(church.pastors) ? church.pastors.length : 0),
        0,
      ),
      counts,
      churches,
    };
  },
});
