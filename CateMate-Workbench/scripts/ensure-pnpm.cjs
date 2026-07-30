/**
 * Cross-platform preinstall guard: require pnpm and remove npm/yarn lockfiles.
 */
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
for (const name of ["package-lock.json", "yarn.lock"]) {
  const file = path.join(root, name);
  try {
    fs.unlinkSync(file);
  } catch (err) {
    if (err && err.code !== "ENOENT") throw err;
  }
}

const ua = process.env.npm_config_user_agent || "";
if (!ua.startsWith("pnpm/")) {
  console.error("Use pnpm instead of npm/yarn. Example: corepack pnpm install");
  process.exit(1);
}
