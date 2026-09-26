'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from '@/i18n/navigation';
import { onboardingApi } from '@/lib/api-client';

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [isMounted, setIsMounted] = useState(false);
  const [formData, setFormData] = useState({
    profile: {
      fullName: '',
      timezone: 'UTC',
      language: 'en',
      experienceLevel: 'beginner',
    },
    organization: {
      companyName: '',
      inviteCode: '',
    },
    marketPrefs: {
      primaryExchange: 'NYSE',
      watchlistPrefs: 'tech',
      chartInterval: '1D',
      chartStyle: 'candlestick',
    },
    workspace: {
      watchlistItems: '',
    },
  });

  // Load from sessionStorage on mount
  useEffect(() => {
    setIsMounted(true);
    const saved = sessionStorage.getItem('onboardingState');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.step) setStep(parsed.step);
        if (parsed.formData) setFormData(parsed.formData);
      } catch (e) {
        console.error('Failed to load onboarding state', e);
      }
    }
  }, []);

  // Save to sessionStorage on change
  useEffect(() => {
    if (isMounted) {
      sessionStorage.setItem('onboardingState', JSON.stringify({ step, formData }));
    }
  }, [step, formData, isMounted]);

  const updateFormData = (section: keyof typeof formData, field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
  };

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    } else {
      handleFinish();
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleFinish = async () => {
    console.log('Saving onboarding data to backend...', formData);
    await onboardingApi.completeOnboarding(formData);
    
    // Clear session storage upon successful completion
    sessionStorage.removeItem('onboardingState');
    
    // Redirect to dashboard
    router.push('/dashboard');
  };

  // Prevent hydration mismatch by not rendering until mounted
  if (!isMounted) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Set up your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Step {step} of 4
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form onSubmit={(e) => e.preventDefault()} className="space-y-6">
            
            {/* Step 1: Profile */}
            {step === 1 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Profile Information</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    type="text"
                    value={formData.profile.fullName}
                    onChange={(e) => updateFormData('profile', 'fullName', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Timezone</label>
                  <select
                    value={formData.profile.timezone}
                    onChange={(e) => updateFormData('profile', 'timezone', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="UTC">UTC</option>
                    <option value="EST">EST</option>
                    <option value="PST">PST</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Language</label>
                  <select
                    value={formData.profile.language}
                    onChange={(e) => updateFormData('profile', 'language', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Experience Level</label>
                  <select
                    value={formData.profile.experienceLevel}
                    onChange={(e) => updateFormData('profile', 'experienceLevel', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>
              </div>
            )}

            {/* Step 2: Organization */}
            {step === 2 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Organization</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Company Name (to create)</label>
                  <input
                    type="text"
                    value={formData.organization.companyName}
                    onChange={(e) => updateFormData('organization', 'companyName', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  />
                </div>
                <div className="text-sm text-center text-gray-500">OR</div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Invite Code (to join)</label>
                  <input
                    type="text"
                    value={formData.organization.inviteCode}
                    onChange={(e) => updateFormData('organization', 'inviteCode', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  />
                </div>
              </div>
            )}

            {/* Step 3: Market Preferences */}
            {step === 3 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Market Preferences</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Primary Exchange</label>
                  <select
                    value={formData.marketPrefs.primaryExchange}
                    onChange={(e) => updateFormData('marketPrefs', 'primaryExchange', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="NYSE">NYSE</option>
                    <option value="NASDAQ">NASDAQ</option>
                    <option value="LSE">LSE</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Watchlist Preferences</label>
                  <select
                    value={formData.marketPrefs.watchlistPrefs}
                    onChange={(e) => updateFormData('marketPrefs', 'watchlistPrefs', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="tech">Technology</option>
                    <option value="finance">Finance</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="crypto">Crypto</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Default Chart Interval</label>
                  <select
                    value={formData.marketPrefs.chartInterval}
                    onChange={(e) => updateFormData('marketPrefs', 'chartInterval', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="1m">1 Minute</option>
                    <option value="5m">5 Minutes</option>
                    <option value="1H">1 Hour</option>
                    <option value="1D">1 Day</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Default Chart Style</label>
                  <select
                    value={formData.marketPrefs.chartStyle}
                    onChange={(e) => updateFormData('marketPrefs', 'chartStyle', e.target.value)}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  >
                    <option value="candlestick">Candlestick</option>
                    <option value="line">Line</option>
                    <option value="bar">Bar</option>
                  </select>
                </div>
              </div>
            )}

            {/* Step 4: Workspace Setup */}
            {step === 4 && (
              <div className="space-y-4">
                <h3 className="text-lg font-medium text-gray-900">Workspace Setup</h3>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Initial Watchlist Items (comma separated symbols)</label>
                  <textarea
                    value={formData.workspace.watchlistItems}
                    onChange={(e) => updateFormData('workspace', 'watchlistItems', e.target.value)}
                    rows={4}
                    placeholder="AAPL, MSFT, TSLA"
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-black"
                  />
                </div>
              </div>
            )}

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-6">
              <button
                type="button"
                onClick={handleBack}
                disabled={step === 1}
                className={`py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${step === 1 ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                Back
              </button>
              <button
                type="button"
                onClick={handleNext}
                className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                {step === 4 ? 'Finish' : 'Next'}
              </button>
            </div>
            
          </form>
        </div>
      </div>
    </div>
  );
}
