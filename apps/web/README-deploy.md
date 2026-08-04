# Deploying the web app

Vercel builds this directory (`apps/web`) and serves `dist/`.

## Why vercel.json exists

This is a single-page app: React Router owns every path, and only `index.html`
exists on disk. Without a rewrite, Vercel looks for a file at `/signup`, finds
none, and returns its own 404 **before any JavaScript loads** — so the router
never gets the chance to handle it.

That breaks every route except `/`, but only when a URL is *typed, refreshed,
bookmarked or shared*. Clicking through the app works fine, because navigation
then happens in the browser without a server request — which is exactly why the
bug is easy to ship without noticing.

The rewrite sends every path to `index.html` and lets the router decide. It is
checked *after* the filesystem, so real files (`/assets/*.js`, `/favicon.ico`)
still serve normally.

It matters beyond convenience: `/auth/callback` is where Google and Microsoft
redirect after sign-in. A 404 there would break OAuth outright.

## Environment variables

Set in the Vercel dashboard, not here:

    VITE_API_URL = https://codejourney-api.duckdns.org

Vite bakes these in at **build** time, so changing the value requires a redeploy
— saving it alone leaves the running build with the old value compiled in.
