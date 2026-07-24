"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, AlertTriangle } from "lucide-react";

import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter, Input } from "@neuroquant/ui";
import { loginSchema, type LoginInput } from "@/lib/validations/auth";
import { useAuthStore } from "@/stores/authStore";
import { authApi } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";

function StatusBanner({ type, message }: { type: "success" | "error"; message: string }): JSX.Element {
  return (
    <div
      className={`mb-4 flex items-center gap-2 rounded-[var(--ds-radius-lg)] border px-3 py-2 text-xs ${
        type === "success"
          ? "border-[var(--ds-color-success-500)]/40 bg-[var(--ds-color-success-500)]/10 text-[var(--ds-color-success-500)]"
          : "border-[var(--ds-color-danger-500)]/40 bg-[var(--ds-color-danger-500)]/10 text-[var(--ds-color-danger-500)]"
      }`}
    >
      {type === "success" ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
      <span>{message}</span>
    </div>
  );
}

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";

  const pushToast = useToastStore((state) => state.pushToast);
  const setTokens = useAuthStore((state) => state.setTokens);
  const [status, setStatus] = useState<"idle" | "error" | "success">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    setStatus("idle");
    setErrorMessage("");

    try {
      const tokens = await authApi.login(data.email, data.password);
      setTokens(tokens);
      setStatus("success");
      pushToast({ tone: "success", title: "Signed in", message: "Redirecting..." });
      router.push(callbackUrl);
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Invalid credentials or server error.");
      }
    }
  };

  return (
    <Card className="border-white/10 bg-[rgba(255,255,255,0.06)]">
      <CardHeader className="mb-5">
        <CardTitle>Welcome back</CardTitle>
        <CardDescription>Sign in to your workspace and continue where your team left off.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === "error" ? <StatusBanner type="error" message={errorMessage || "Please provide a valid email and password."} /> : null}
        {status === "success" ? <StatusBanner type="success" message="Signed in successfully. Redirecting..." /> : null}
        
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-[var(--ds-text-secondary)]">
              Email
            </label>
            <Input
              {...register("email")}
              placeholder="you@company.com"
              type="email"
              className={errors.email ? "border-red-500" : ""}
            />
            {errors.email && (
              <p className="mt-1 text-[10px] text-red-500">{errors.email.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-[var(--ds-text-secondary)]">
              Password
            </label>
            <Input
              {...register("password")}
              type="password"
              placeholder="Enter your password"
              className={errors.password ? "border-red-500" : ""}
            />
            {errors.password && (
              <p className="mt-1 text-[10px] text-red-500">{errors.password.message}</p>
            )}
          </div>
          <Button className="w-full" type="submit" isLoading={isSubmitting}>
            Sign in
          </Button>
        </form>
        <CardFooter className="mt-5 flex-col items-start justify-start border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/forgot-password"
            className="text-xs text-[var(--ds-color-primary-300)] transition hover:text-[var(--nq-accent-hover)]"
          >
            Forgot password?
          </Link>
          <p className="text-xs text-[var(--ds-text-secondary)] mt-3 sm:mt-0">
            New to NeuroQuant?{" "}
            <Link
              href="/register"
              className="text-[var(--ds-color-primary-300)] transition hover:text-[var(--nq-accent-hover)]"
            >
              Create an account
            </Link>
          </p>
        </CardFooter>
      </CardContent>
    </Card>
  );
}

export default function LoginPage(): JSX.Element {
  return (
    <Suspense fallback={<div className="h-full w-full animate-pulse rounded bg-white/5" />}>
      <LoginFormContent />
    </Suspense>
  );
}
