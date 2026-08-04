# Deploying CodeJourney with grading

The frontend is on Vercel. This directory is for the API, which Vercel cannot
host, because **grading needs Docker**.

## Why not Render, Railway or Vercel

Grading runs each submission in its own hardened container (`--network=none`,
`--memory=128m`, `--pids-limit=64`, `--read-only`, `-u nobody`). That needs a
real Docker daemon, and managed platforms do not hand one out.

The alternative is not "run it without the sandbox". `LocalRunner` raises rather
than execute untrusted code unsandboxed, deliberately — on a public URL,
skipping the sandbox means anyone on the internet can run arbitrary Python on
your server. If a grading error tempts you to set `ENVIRONMENT=development` to
make it go away, that is what you would be turning off.

So: a small VM you control. Roughly $5/month at DigitalOcean, Hetzner or Linode.
The smallest tier is enough.

## The trade-off, stated plainly

The API container mounts the host's Docker socket, because that is how it starts
sandbox containers. **Access to that socket is equivalent to root on the host.**
A remote-code-execution bug in the API would mean the whole machine, not just a
container.

That is why this stack belongs on a VM that holds nothing else — no other
projects, no personal data, nothing you would mind rebuilding. Bounding the
blast radius is the mitigation.

The proper fix, noted in `docker-compose.yml` at the repo root, is to move the
sandbox behind its own runner service so the API never holds the socket. Worth
doing before this is ever more than a demo.

## Steps

**1. A VM.** Ubuntu 24.04, smallest size. Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

**2. A domain pointing at it.** An `A` record for something like
`api.yourdomain.com` → the VM's IP. **A bare IP will not work**: your Vercel site
is `https`, browsers refuse to let an `https` page call `http`, and Let's Encrypt
only issues certificates for domain names. A free subdomain from any registrar or
DNS provider is fine.

**3. The code.**

```bash
git clone https://github.com/BAlwisNU/CodeJourney.git
cd CodeJourney
```

**4. The sandbox image.** Built on the host, because the API invokes it through
the host's Docker rather than running it inside itself:

```bash
docker build -t codejourney-sandbox:3.12 packages/harness
```

**5. Settings.**

```bash
cp deploy/.env.example deploy/.env
openssl rand -hex 32          # for SECRET_KEY
openssl rand -hex 32          # for POSTGRES_PASSWORD
nano deploy/.env              # fill in both, plus your domain and Vercel URL
```

**6. Start it.**

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

Caddy gets a certificate on first boot; give it a minute, then check
`https://api.yourdomain.com/health` returns JSON.

**7. Seed the exercises.** Without this the demo buttons open nothing:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env \
  exec api python -m app.seed
```

**8. Point Vercel at it.** Project → Settings → Environment Variables:

```
VITE_API_URL = https://api.yourdomain.com
```

Then **Deployments → Redeploy**. Vite bakes environment variables in at build
time, so setting the variable without redeploying changes nothing — the existing
build keeps `http://localhost:8000`.

**9. Check grading actually works.** Open a lesson on the live site and press
**Submit**, not just Run. Run executes in the browser via Pyodide and will pass
whether or not any of this worked; Submit is the one that proves the sandbox is
reachable.

## If Submit fails

```bash
docker compose -f deploy/docker-compose.prod.yml logs api | tail -50
```

- `FileNotFoundError: docker` — the API image lacks the Docker CLI. It is
  installed in `apps/api/Dockerfile`; rebuild with `--build`.
- `Unable to find image 'codejourney-sandbox:3.12'` — step 4 was skipped, or was
  run somewhere other than the host's Docker.
- `permission denied ... docker.sock` — the socket mount is missing or the
  daemon is not running.

## Afterwards

OAuth redirect URIs are still registered against `localhost`. To use the
Google/Microsoft buttons on the live site, re-register them as
`https://api.yourdomain.com/auth/oauth/<provider>/callback` and set the client
credentials in `deploy/.env`.
