# .github/workflows/ci.yml
name: CI
on:
  pull_request:
  push:
    branches: [ master ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m venv .venv
      - run: . .venv/bin/activate && pip install -U pip pytest requests
      - run: . .venv/bin/activate && pytest -q
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          API_URL: ${{ secrets.API_URL }}
          TRAEFIK_DASHBOARD_USER: ${{ secrets.TRAEFIK_DASHBOARD_USER }}
          TRAEFIK_DASHBOARD_PASS: ${{ secrets.TRAEFIK_DASHBOARD_PASS }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
          NEXTAUTH_URL: ${{ secrets.NEXTAUTH_URL }}
          NEXTAUTH_SECRET: ${{ secrets.NEXTAUTH_SECRET }}
          POSTGRES_HOST: ${{ secrets.POSTGRES_HOST }}
          POSTGRES_USER: ${{ secrets.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
          POSTGRES_DB: ${{ secrets.POSTGRES_DB }}
