import type { Metadata } from "next";
import { PortfolioContent } from "@/components/portfolio/portfolio-content";

export const metadata: Metadata = { title: "Portfolio" };

export default function PortfolioPage() {
  return <PortfolioContent />;
}
