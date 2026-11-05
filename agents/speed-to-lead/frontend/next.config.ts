import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lets a second dev server run beside the main one without sharing the .next lock
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
