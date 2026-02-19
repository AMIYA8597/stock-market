import type { Metadata } from "next";
import { ResearchContent } from "@/components/research/research-content";

export const metadata: Metadata = { title: "Research" };

export default function ResearchPage() {
  return <ResearchContent />;
}
