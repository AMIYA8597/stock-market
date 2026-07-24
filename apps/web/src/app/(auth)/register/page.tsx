"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, AlertTriangle } from "lucide-react";

import { Button, Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter, Input } from "@neuroquant/ui";
import { registerSchema, type RegisterInput } from "@/lib/validations/auth";
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

export default function RegisterPage(): JSX.Element {
  const router = useRouter();
  const pushToast = useToastStore((state) => state.pushToast);
  const [status, setStatus] = useState<"idle" | "error" | "success">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput>({
    resolver: zodResolver(registerSchema),
  });

  const passwordValue = watch("password", "");

  const onSubmit = async (data: RegisterInput) => {
    setStatus("idle");
    setErrorMessage("");

    try {
      await authApi.register({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });
      setStatus("success");
      pushToast({ tone: "success", title: "Account created", message: "You can now sign in." });
      
      // Delay slightly to show success state before redirecting
      setTimeout(() => {
        router.push("/login");
      }, 2000);
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to create account. Email may already be in use.");
      }
    }
  };

  return (
    <Card className="border-white/10 bg-[rgba(255,255,255,0.06)]">
      <CardHeader className="mb-5">
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Set up your organization workspace in under two minutes.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status === "error" ? <StatusBanner type="error" message={errorMessage || "Something went wrong."} /> : null}
        {status === "success" ? <StatusBanner type="success" message="Account created. Redirecting to login..." /> : null}
        
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-[var(--ds-text-secondary)]">
              Full name
            </label>
            <Input
              {...register("full_name")}
              placeholder="Your name"
              className={errors.full_name ? "border-red-500" : ""}
            />
            {errors.full_name && (
              <p className="mt-1 text-[10px] text-red-500">{errors.full_name.message}</p>
            )}
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.12em] text-[var(--ds-text-secondary)]">
              Work email
            </label>
            <Input
              {...register("email")}
              type="email"
              placeholder="you@company.com"
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
              placeholder="Create a password"
              className={errors.password ? "border-red-500" : ""}
            />
            {errors.password ? (
              <p className="mt-1 text-[10px] text-red-500">{errors.password.message}</p>
            ) : (
              <div className="mt-2 flex gap-1">
                <div className={`h-1 flex-1 rounded ${passwordValue.length >= 8 ? 'bg-green-500' : 'bg-white/20'}`} />
                <div className={`h-1 flex-1 rounded ${/[A-Z]/.test(passwordValue) ? 'bg-green-500' : 'bg-white/20'}`} />
                <div className={`h-1 flex-1 rounded ${/[a-z]/.test(passwordValue) ? 'bg-green-500' : 'bg-white/20'}`} />
                <div className={`h-1 flex-1 rounded ${/[0-9]/.test(passwordValue) ? 'bg-green-500' : 'bg-white/20'}`} />
              </div>
            )}
          </div>
          <Button className="w-full" type="submit" isLoading={isSubmitting}>
            Create account
          </Button>
        </form>
        <CardFooter className="mt-5 flex-col items-start justify-start border-white/10 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-[var(--ds-text-secondary)]">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[var(--ds-color-primary-300)] transition hover:text-[var(--nq-accent-hover)]"
            >
              Sign in
            </Link>
          </p>
          <p className="text-xs text-[var(--ds-text-secondary)] mt-3 sm:mt-0 text-right sm:text-left">
            By creating an account you agree to the platform terms.
          </p>
        </CardFooter>
      </CardContent>
    </Card>
  );
}
