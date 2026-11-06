import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.PACE_E2E === "1" ? ".next-e2e" : ".next",
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),
};

export default nextConfig;
