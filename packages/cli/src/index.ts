#!/usr/bin/env node
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

// Unix pipelines commonly close stdout early (for example, `| head`). Treat
// that normal CLI condition as a clean exit instead of an uncaught EPIPE.
process.stdout.on("error", (error: NodeJS.ErrnoException) => {
  if (error.code === "EPIPE") process.exit(0);
  throw error;
});

type Action = "create" | "skip" | "overwrite";

const TEMPLATE_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "templates", "nextjs");

export function parseArgs(argv: string[]) {
  const args = { framework: "nextjs", dir: process.cwd(), dryRun: false, force: false, help: false };
  const rest = argv.slice(2);
  if (rest[0] !== "init" && rest[0] !== undefined) {
    if (rest[0] === "--help" || rest[0] === "-h") args.help = true;
  }
  for (let i = 0; i < rest.length; i += 1) {
    const token = rest[i];
    if (token === "init") continue;
    if (token === "--help" || token === "-h") args.help = true;
    else if (token === "--dry-run") args.dryRun = true;
    else if (token === "--force") args.force = true;
    else if (token === "--framework" || token === "--dir") {
      const value = rest[++i];
      if (!value || value.startsWith("--")) throw new Error(`Missing value for ${token}`);
      if (token === "--framework") args.framework = value;
      else args.dir = value;
    } else {
      throw new Error(`Unknown argument: ${token}`);
    }
  }
  return args;
}

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

export function planCopy(templateRoot: string, destRoot: string, force: boolean): { from: string; to: string; action: Action }[] {
  return walk(templateRoot).map((from) => {
    const rel = relative(templateRoot, from);
    const to = join(destRoot, rel);
    if (!existsSync(to)) return { from, to, action: "create" as const };
    return { from, to, action: force ? "overwrite" as const : "skip" as const };
  });
}

export function updatePackageJson(pkgPath: string): void {
  const pkg = JSON.parse(readFileSync(pkgPath, "utf8")) as {
    dependencies?: Record<string, string>;
    devDependencies?: Record<string, string>;
  };
  pkg.dependencies ??= {};
  for (const name of ["@authkit/client", "@authkit/react", "@authkit/nextjs"]) {
    pkg.dependencies[name] ??= "^1.0.0";
  }
  pkg.dependencies["qrcode.react"] ??= "^4.2.0";
  pkg.devDependencies ??= {};
  pkg.devDependencies.tailwindcss ??= "^4.1.13";
  pkg.devDependencies["@tailwindcss/postcss"] ??= "^4.1.13";
  writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`);
}

function main(): void {
  const args = parseArgs(process.argv);
  if (args.help || process.argv[2] !== "init") {
    process.stdout.write(
      "Usage: authkit-ui init --framework nextjs [--dir .] [--dry-run] [--force]\n",
    );
    process.exit(process.argv[2] === "init" ? 0 : 1);
  }
  if (args.framework !== "nextjs") {
    throw new Error(`Unsupported framework: ${args.framework}`);
  }
  if (!existsSync(TEMPLATE_ROOT)) {
    throw new Error(`Templates not found at ${TEMPLATE_ROOT}`);
  }
  const planned = planCopy(TEMPLATE_ROOT, args.dir, args.force);
  const pkgPath = join(args.dir, "package.json");
  if (!existsSync(pkgPath)) {
    process.stderr.write("warning: package.json not found; scaffolded files but dependencies were not added\n");
  } else {
    const existing = JSON.parse(readFileSync(pkgPath, "utf8")) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    if (!(existing.dependencies?.next || existing.devDependencies?.next)) {
      process.stderr.write("warning: Next.js was not detected in package.json\n");
    }
  }
  for (const item of planned) {
    process.stdout.write(`${item.action}\t${relative(args.dir, item.to) || item.to}\n`);
    if (args.dryRun || item.action === "skip") continue;
    mkdirSync(dirname(item.to), { recursive: true });
    cpSync(item.from, item.to);
  }
  if (existsSync(pkgPath) && !args.dryRun) {
    updatePackageJson(pkgPath);
  }
}

export function isMainModule(
  argvPath: string | undefined,
  modulePath = fileURLToPath(import.meta.url),
): boolean {
  if (!argvPath || !existsSync(argvPath) || !existsSync(modulePath)) return false;
  return realpathSync(argvPath) === realpathSync(modulePath);
}

if (isMainModule(process.argv[1])) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : error}\n`);
    process.exit(1);
  }
}
