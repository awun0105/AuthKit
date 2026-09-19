import { mkdirSync, readFileSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { isMainModule, parseArgs, planCopy, updatePackageJson } from "./index.js";

describe("planCopy", () => {
  it("does not overwrite unless forced", () => {
    const root = join(tmpdir(), `authkit-cli-${Date.now()}`);
    const template = join(root, "template");
    const dest = join(root, "dest");
    mkdirSync(join(template, "src"), { recursive: true });
    writeFileSync(join(template, "src", "a.txt"), "template");
    mkdirSync(join(dest, "src"), { recursive: true });
    writeFileSync(join(dest, "src", "a.txt"), "existing");
    const skipped = planCopy(template, dest, false);
    expect(skipped[0]?.action).toBe("skip");
    const forced = planCopy(template, dest, true);
    expect(forced[0]?.action).toBe("overwrite");
  });

  it("adds runtime and Tailwind dependencies without replacing existing versions", () => {
    const root = join(tmpdir(), `authkit-cli-package-${Date.now()}`);
    mkdirSync(root, { recursive: true });
    const packagePath = join(root, "package.json");
    writeFileSync(packagePath, JSON.stringify({
      dependencies: { next: "^15.0.0", "@authkit/client": "workspace:*" },
    }));
    updatePackageJson(packagePath);
    const pkg = JSON.parse(readFileSync(packagePath, "utf8")) as {
      dependencies: Record<string, string>;
      devDependencies: Record<string, string>;
    };
    expect(pkg.dependencies["@authkit/client"]).toBe("workspace:*");
    expect(pkg.dependencies["@authkit/react"]).toBe("^1.0.0");
    expect(pkg.dependencies["qrcode.react"]).toBe("^4.2.0");
    expect(pkg.devDependencies.tailwindcss).toBe("^4.1.13");
  });

  it("recognizes a package-manager bin symlink as the executable entrypoint", () => {
    const root = join(tmpdir(), `authkit-cli-bin-${Date.now()}`);
    mkdirSync(root, { recursive: true });
    const target = join(root, "index.js");
    const bin = join(root, "authkit-ui");
    writeFileSync(target, "");
    symlinkSync(target, bin);
    expect(isMainModule(bin, target)).toBe(true);
  });

  it("rejects unknown flags and missing option values", () => {
    expect(() => parseArgs(["node", "authkit-ui", "init", "--wat"])).toThrow("Unknown argument");
    expect(() => parseArgs(["node", "authkit-ui", "init", "--dir"])).toThrow("Missing value");
  });
});
