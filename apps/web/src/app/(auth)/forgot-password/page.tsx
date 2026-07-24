/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, AlertTriangle } from "lucide-react";

import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter, Input } from "@neuroquant/ui";
import { forgotPasswordSchema, type ForgotPasswordInput } from "@/lib/validations/auth";
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

export default function ForgotPasswordPage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [status, setStatus] = useState<"idle" | "error" | "success">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordInput>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordInput) => {
    setStatus("idle");
    setErrorMessage("");

    try {
      await authApi.forgotPassword(data.email);
      setStatus("success");
      pushToast({ tone: "success", title: "Email sent", message: "Check your inbox for reset instructions." });
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to send reset link.");
      }
    }
  };

  return (
    <Card className="border-white/10 bg-[rgba(255,255,255,0.06)]">
      <CardHeader className="mb-5">
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>Enter your email and we'll send you instructions to reset your password.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === "error" ? <StatusBanner type="error" message={errorMessage || "Something went wrong."} /> : null}
        {status === "success" ? (
          <StatusBanner type="success" message="Instructions sent! Please check your email inbox." />
        ) : (
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
            <Button className="w-full" type="submit" isLoading={isSubmitting}>
              Send Reset Link
            </Button>
          </form>
        )}
        <CardFooter className="mt-5 flex justify-center border-white/10 pt-4">
          <Link
            href="/login"
            className="text-xs text-[var(--ds-color-primary-300)] transition hover:text-[var(--nq-accent-hover)]"
          >
            &larr; Back to login
          </Link>
        </CardFooter>
      </CardContent>
    </Card>
  );
}
