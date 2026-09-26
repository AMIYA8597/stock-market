import type { Metadata } from "next";
import { AlertsContent } from "@/components/alerts/alerts-content";
import { AuthGuard } from "@/components/auth/AuthGuard";

export const metadata: Metadata = { title: "Alerts" };

export default function AlertsPage() {
  return (
    <AuthGuard>
      <AlertsContent />
    </AuthGuard>
  );
}
