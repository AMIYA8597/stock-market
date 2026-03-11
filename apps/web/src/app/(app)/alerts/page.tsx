import type { Metadata } from "next";
import { AlertsContent } from "@/components/alerts/alerts-content";

export const metadata: Metadata = { title: "Alerts" };

export default function AlertsPage() {
  return <AlertsContent />;
}
