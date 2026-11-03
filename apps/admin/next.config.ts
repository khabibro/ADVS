import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@advs/ui", "@advs/contracts"],
};

export default nextConfig;

