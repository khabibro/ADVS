import { existsSync, readFileSync } from "node:fs";
import { execSync } from "node:child_process";

const errors = [];
const allFiles = execSync("git ls-files --others --cached --exclude-standard", {
  encoding: "utf8",
}).split(/\r?\n/).filter(Boolean);

if (allFiles.some((file) => /^\.env($|\.)/.test(file) && file !== ".env.example")) {
  errors.push(".env files must not be tracked or staged");
}

for (const file of allFiles.filter((file) => file.startsWith("apps/web") || file.startsWith("apps/admin"))) {
  const text = readFileSync(file, "utf8");
  if (text.includes("OCR_SECRET") || text.includes("NEXT_PUBLIC_OCR_SECRET")) {
    errors.push(`OCR secret reference found in frontend file: ${file}`);
  }
}

const storage = readFileSync("apps/api/app/services/storage/local.py", "utf8");
if (!storage.includes("ALLOWED_MIME")) errors.push("Upload MIME validation not found");
if (!storage.includes("ALLOWED_EXT")) errors.push("Upload extension validation not found");
if (!storage.includes("max_upload_size_bytes")) errors.push("Upload size validation not found");
if (!storage.includes("sanitize_filename")) errors.push("Filename sanitization not found");
if (!storage.includes(".resolve()")) errors.push("Storage path traversal guard not found");

const provider = readFileSync("apps/api/app/document_intelligence/ocr/providers.py", "utf8");
if (provider.includes("print(")) errors.push("OCR provider should not print raw data");

if (!existsSync(".gitignore") || !readFileSync(".gitignore", "utf8").includes(".env")) {
  errors.push(".env ignore rule missing");
}

if (errors.length) {
  console.error(`Security audit failed:\n- ${errors.join("\n- ")}`);
  process.exit(1);
}

console.log("Security audit passed.");
