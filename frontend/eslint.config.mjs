import { globalIgnores } from "eslint/config";
import nextVitalsModule from "eslint-config-next/core-web-vitals.js";

const nextVitals = Array.isArray(nextVitalsModule)
  ? nextVitalsModule
  : nextVitalsModule?.default ?? [nextVitalsModule];

export default [
  ...nextVitals,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
];
