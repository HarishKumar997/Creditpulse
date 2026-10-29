import path from "path";
import { fileURLToPath } from "url";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.dirname(fileURLToPath(import.meta.url)),
  outputFileTracingIncludes: {
    "/*": ["./data/**"],
    "/api/*": ["./data/**"],
  },
};

export default nextConfig;
