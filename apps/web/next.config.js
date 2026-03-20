/** @type {import('next').NextConfig} */
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
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
