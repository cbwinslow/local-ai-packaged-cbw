#!/usr/bin/env python3
"""Advanced realtime test using Postgres LISTEN/NOTIFY via docker exec psql.

This test will:
- Connect to the Postgres server inside the supabase-db container using psql's LISTEN/NOTIFY
  (via a small Python PG connection using psycopg2)
- Insert a row into `public.smoke_realtime` and ensure the NOTIFY payload is received.

Requires: psycopg2-binary (pip install psycopg2-binary)

Usage:
  python3 scripts/tests/06_realtime_postgres_notify.py
"""
import os
import select
import time

import psycopg2

DB_NAME = os.environ.get('POSTGRES_DB', 'postgres')
DB_USER = os.environ.get('POSTGRES_USER', 'postgres')
DB_PASS = os.environ.get('POSTGRES_PASSWORD', '')
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_PORT = int(os.environ.get('POSTGRES_PORT', '5432'))

# If running from the host where docker is present, we will exec into container
# If env contains DOCKER_SUPABASE_DB=true, assume supabase-db is the container name and connect via docker exec psql command
USE_DOCKER_EXEC = os.environ.get('DOCKER_SUPABASE_DB','true').lower() in ('1','true','yes')
CONTAINER_NAME = os.environ.get('SUPABASE_DB_CONTAINER','supabase-db')


def listen_and_notify():
    if USE_DOCKER_EXEC:
        # Connect using a direct TCP connection to the container's exposed port if available
        # Prefer connecting to host:5432 if mapped; otherwise exec into container
        # We will try docker exec psql LISTEN approach if network isn't available.
        try:
            import docker
            client = docker.from_env()
            # Verify container exists
            _ = client.containers.get(CONTAINER_NAME)
            print('Detected container', CONTAINER_NAME)
        except Exception:
            # ignore - we'll attempt direct DB connection
            pass

    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("LISTEN smoke_channel;")
    print('Listening on smoke_channel...')

    # Insert a row to trigger notify
    cur.execute("INSERT INTO public.smoke_realtime (data) VALUES (%s) RETURNING id;", ('smoke-test-'+str(int(time.time())),))
    inserted = cur.fetchone()[0]
    print('Inserted row id', inserted)

    # Wait for notification
    found = False
    start = time.time()
    while time.time() - start < 10:
        if select.select([conn], [], [], 1) == ([], [], []):
            continue
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            print('Received notification:', notify.payload)
            found = True
            break
        if found:
            break

    if not found:
        raise SystemExit('Did not receive postgres NOTIFY within timeout')


if __name__ == '__main__':
    listen_and_notify()
