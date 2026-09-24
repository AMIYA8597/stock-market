import type { Metadata } from "next";
import { SignalsFeedPage } from "@/modules/signals/SignalsFeedPage";

export const metadata: Metadata = { title: "AI Signal Feed" };

export default function SignalsRoutePage() {
  return <SignalsFeedPage />;
}
