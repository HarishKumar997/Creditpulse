# Vercel Hobby

Vercel hosts the Next.js site. It does not run Spark, Airflow, or Postgres.

1. Push the repository to GitHub. The demo JSON under `web/data/` must already be in git. Produce it with a local pipeline run before the push.
2. Import the repository at https://vercel.com as a Hobby project.
3. Set the root directory to `web`.
4. Leave the build command as `npm run build` and the output as the Next.js default. Do not add a database URL or a Spark command.
5. After deploy, open `/`, `/portfolio`, `/quality`, `/runs`, `/architecture`, and `/api/health` in a private window.

An invalid call such as `/api/portfolio/daily?from=2024-13-01&to=2024-12-31` must return HTTP 400 and a JSON `error` string.

Hobby limits apply: this is a personal demo, not a production service. If the free tier is unavailable, `npm run dev` inside `web/` is the supported way to view the same pages.
