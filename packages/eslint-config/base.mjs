import js from "@eslint/js";
import tseslint from "typescript-eslint";

export const base = [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
    },
  },
];

export default base;
