/** @type {import('next').NextConfig} */
function normalizeApiBase(url) {
  const candidate = (url || "http://localhost:8000").replace(/\/+$/, "");
  return candidate.replace(/\/api\/v1\/?$/i, "");
}

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@neuroquant/ui", "@neuroquant/types"],
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
    ],
  },
  experimental: {
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "d3",
      "framer-motion",
    ],
  },
  async redirects() {
    return [
      {
        source: "/backtesting",
        destination: "/backtest-lab",
        permanent: false,
      },
      {
        source: "/market",
        destination: "/markets",
        permanent: false,
      },
      {
        source: "/market/:symbol",
        destination: "/markets/stocks/:symbol",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const apiBase = normalizeApiBase(process.env.NEXT_PUBLIC_API_URL);
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiBase}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
