import type { Metadata } from "next";
import { SignalsFeedPage } from "@/modules/signals/SignalsFeedPage";
import { AuthGuard } from "@/components/auth/AuthGuard";

export const metadata: Metadata = { title: "AI Signal Feed" };

export default function SignalsRoutePage() {
  return (
    <AuthGuard>
      <SignalsFeedPage />
    </AuthGuard>
  );
}
