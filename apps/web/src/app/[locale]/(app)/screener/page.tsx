import type { Metadata } from "next";
import { ScreenerContent } from "@/components/screener/screener-content";
import { AuthGuard } from "@/components/auth/AuthGuard";

export const metadata: Metadata = { title: "Screener" };

export default function ScreenerPage() {
  return (
    <AuthGuard>
      <ScreenerContent />
    </AuthGuard>
  );
}
