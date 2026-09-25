import sys

with open('apps/web/src/lib/api-client.ts', 'r', encoding='utf-8') as f:
    text = f.read()

if 'onboardingApi' not in text:
    text += '''
export const onboardingApi = {
  completeOnboarding(data: { profile: any; organization: any; marketPrefs: any; workspace: any }): Promise<any> {
    return fetchApi("/onboarding", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
};
'''
with open('apps/web/src/lib/api-client.ts', 'w', encoding='utf-8') as f:
    f.write(text)
