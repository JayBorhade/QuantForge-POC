import { defineConfig, globalIgnores } from "eslint/config";
import nextVitalsModule from "eslint-config-next/core-web-vitals.js";
import nextTsModule from "eslint-config-next/typescript.js";

const asConfigArray = (config) => {
  if (Array.isArray(config)) return config;
  if (config && Array.isArray(config.default)) return config.default;
  if (config && config.default) return asConfigArray(config.default);
  return [config];
};

export default defineConfig([
  ...asConfigArray(nextVitalsModule),
  ...asConfigArray(nextTsModule),
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);
