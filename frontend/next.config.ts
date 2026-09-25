import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['*.trycloudflare.com'],
  // A stray package.json/lockfile in a parent folder (e.g. ~) makes Turbopack
  // pick that folder as the root, and then it can't find tailwindcss.
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
