import { defineApp } from "convex/server";
import { v } from "convex/values";

export default defineApp({
  env: {
    RESEARCH_API_KEYS: v.optional(v.string()),
    ADMIN_API_KEY: v.optional(v.string()),
  },
});
