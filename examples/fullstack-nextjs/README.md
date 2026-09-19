# Full-stack AuthKit example

FastAPI AuthKit backend + Next.js UI generated from AuthKit templates.

## Run

From the repository root, the quickest path is:

```bash
make setup
make dev
```

Open http://localhost:3000. Press `Ctrl+C` once to stop both servers.

`make dev` releases ports `8000` and `3000` before starting. To release a port
manually, run `make free-port PORT=8000` (or use another configured port).

The equivalent two-terminal workflow is shown below.

Terminal 1:

```bash
cd ../..
uv run uvicorn main:app --app-dir examples/fullstack-nextjs/backend --reload --port 8000
```

Terminal 2:

```bash
pnpm install
pnpm --filter @authkit/client --filter @authkit/react --filter @authkit/nextjs build
pnpm --filter authkit-fullstack-nextjs-example dev
```

Open http://localhost:3000, register, then open the dashboard documents list
(`documents.read` is assigned to new users as example application data).

The browser suite starts isolated servers on ports 3011 and 8011, gives access
tokens a two-second lifetime, and verifies refresh-cookie restoration:

```bash
# Install Playwright Chromium once when a system Chrome is unavailable
pnpm --filter authkit-fullstack-nextjs-example exec playwright install chromium
pnpm --filter authkit-fullstack-nextjs-example test:e2e

# This workstation can instead use its installed Chrome
AUTHKIT_E2E_BROWSER_CHANNEL=chrome \
  pnpm --filter authkit-fullstack-nextjs-example test:e2e
```
