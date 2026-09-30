import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // NOTE: hi and bn locale files are untranslated English stubs — only "en" has real translations
  locales: ["en", "hi", "bn"],
  defaultLocale: "en",
});
