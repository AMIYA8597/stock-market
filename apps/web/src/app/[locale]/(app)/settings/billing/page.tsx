"use client";

import React, { useState, useEffect } from "react";
import Script from "next/script";
import { paymentsApi } from "@/lib/api-client";
import { AuthGuard } from "@/components/auth/AuthGuard";

interface Plan {
  id: string;
  name: string;
  description: string;
  price_inr: string;
  features: string[];
}

interface Subscription {
  id: string;
  status: string;
  current_period_end: string;
  plan: {
    name: string;
    features: string[];
  };
}

export default function BillingRoutePage() {
  return (
    <AuthGuard>
      <BillingPage />
    </AuthGuard>
  );
}

function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const fetchData = async () => {
    try {
      setFetching(true);
      const [plansRes, subRes] = await Promise.all([
        paymentsApi.getPlans(),
        paymentsApi.getSubscription(),
      ]);
      setPlans(plansRes.items || []);
      setSubscription(subRes.subscription);
    } catch (err) {
      console.error("Failed to load billing data", err);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubscribe = async (plan: Plan) => {
    setLoading(true);
    try {
      const amount = parseFloat(plan.price_inr);
      const intent = await paymentsApi.createIntent({
        amount: amount,
        method: "RAZORPAY",
        currency: "INR",
        description: `Subscription to ${plan.name} plan`,
      });

      const options = {
        key: process.env.NEXT_PUBLIC_RAZORPAY_KEY || "rzp_test_12345",
        amount: Math.round(amount * 100).toString(), // Razorpay expects amount in paise
        currency: "INR",
        name: "Stock Market App",
        description: plan.description,
        order_id: intent.provider_ref || undefined, 
        handler: async function (response: any) {
          try {
            await paymentsApi.confirmIntent(
              intent.intent_id,
              response.razorpay_payment_id || `txn_${Date.now()}`
            );
            alert("Payment successful! Your subscription is now active.");
            fetchData();
          } catch (err) {
            console.error(err);
            alert("Failed to confirm payment.");
          }
        },
        prefill: {
          name: "User",
          email: "user@example.com",
        },
        theme: {
          color: "#3399cc",
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed", function (response: any) {
        console.error(response.error);
        alert("Payment failed: " + response.error.description);
      });
      rzp.open();
    } catch (error) {
      console.error("Payment initiation error", error);
      alert("Failed to initiate payment.");
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return <div className="p-6">Loading billing information...</div>;
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="lazyOnload" />
      
      <h1 className="text-3xl font-bold mb-8">Billing & Subscription</h1>

      {/* Subscription Status */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 mb-10">
        <h2 className="text-xl font-semibold mb-4">Current Subscription</h2>
        {subscription ? (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-gray-600 dark:text-gray-300">Status:</span>
              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                subscription.status === 'active' 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
              }`}>
                {subscription.status.toUpperCase()}
              </span>
            </div>
            <p className="mb-1 text-gray-600 dark:text-gray-300">
              <span className="font-medium text-gray-900 dark:text-white">Plan:</span> {subscription.plan.name}
            </p>
            {subscription.current_period_end && (
              <p className="text-gray-600 dark:text-gray-300">
                <span className="font-medium text-gray-900 dark:text-white">Renews on:</span> {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">You do not have an active subscription.</p>
        )}
      </div>

      {/* Pricing Tiers */}
      <h2 className="text-2xl font-semibold mb-6">Available Plans</h2>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {plans.length > 0 ? (
          plans.map((plan) => (
            <div 
              key={plan.id} 
              className="flex flex-col bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 hover:border-blue-500 transition-colors"
            >
              <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4 h-12">{plan.description}</p>
              <div className="mb-6">
                <span className="text-3xl font-bold">₹{plan.price_inr}</span>
                <span className="text-gray-500">/month</span>
              </div>
              <ul className="mb-8 space-y-3 flex-1">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="flex items-start text-sm">
                    <svg className="w-5 h-5 text-green-500 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSubscribe(plan)}
                disabled={loading || subscription?.plan?.name === plan.name}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                  subscription?.plan?.name === plan.name
                    ? "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 cursor-not-allowed"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                }`}
              >
                {subscription?.plan?.name === plan.name ? "Current Plan" : "Subscribe"}
              </button>
            </div>
          ))
        ) : (
          <p className="text-gray-500">No pricing plans available.</p>
        )}
      </div>
    </div>
  );
}
