import { readFileSync } from "node:fs";

const content = readFileSync(".env.example", "utf8");
const env = Object.fromEntries(
  content
    .split(/\r?\n/)
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => {
      const [key, ...rest] = line.split("=");
      return [key, rest.join("=")];
    }),
);

const errors = [];
const required = [
  "APP_ENV",
  "DATABASE_URL",
  "OCR_PROVIDER",
  "PADDLE_OCR_DEVICE",
  "PADDLE_OCR_LANG",
  "PADDLE_OCR_REC_MODEL_NAME",
  "PADDLE_OCR_DET_MODEL_NAME",
  "STORAGE_PATH",
  "MAX_UPLOAD_SIZE_MB",
  "WEB_URL",
  "ADMIN_URL",
  "API_URL",
  "CORS_ORIGINS",
];

for (const key of required) {
  if (!(key in env)) errors.push(`${key} is missing`);
}

for (const key of ["WEB_URL", "ADMIN_URL", "API_URL"]) {
  try {
    new URL(env[key]);
  } catch {
    errors.push(`${key} must be a valid URL`);
  }
}

if (Number(env.MAX_UPLOAD_SIZE_MB) <= 0) errors.push("MAX_UPLOAD_SIZE_MB must be positive");
if (!["paddle", "mock"].includes(env.OCR_PROVIDER)) {
  errors.push("OCR_PROVIDER must be paddle or mock");
}
if (!["cpu", "gpu"].some((prefix) => env.PADDLE_OCR_DEVICE.toLowerCase().startsWith(prefix))) {
  errors.push("PADDLE_OCR_DEVICE must start with cpu or gpu");
}
if (env.PADDLE_OCR_LANG !== "korean") {
  errors.push("PADDLE_OCR_LANG must be korean for the MVP pipeline");
}
if (env.APP_ENV === "production" && env.CORS_ORIGINS?.includes("*")) {
  errors.push("Wildcard CORS is not allowed in production");
}

if (errors.length) {
  console.error(`Environment validation failed:\n- ${errors.join("\n- ")}`);
  process.exit(1);
}

console.log("Environment validation passed.");
