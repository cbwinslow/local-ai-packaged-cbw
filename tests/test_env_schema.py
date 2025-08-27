#!/usr/bin/env python3
from pathlib import Path
REQ = ['DOMAIN','LETSENCRYPT_EMAIL','SUPABASE_JWT_SECRET','GRAFANA_ADMIN_USER','GRAFANA_ADMIN_PASSWORD','N8N_BASIC_AUTH_USER','N8N_BASIC_AUTH_PASSWORD','FLOWISE_USERNAME','FLOWISE_PASSWORD','NEO4J_USER','NEO4J_PASSWORD','POSTGRES_PASSWORD','JWT_SECRET','ANON_KEY','SERVICE_ROLE_KEY']
SECRET_KEYS = ['SUPABASE_JWT_SECRET','GRAFANA_ADMIN_PASSWORD','N8N_BASIC_AUTH_PASSWORD','FLOWISE_PASSWORD','NEO4J_PASSWORD','POSTGRES_PASSWORD','JWT_SECRET','ANON_KEY','SERVICE_ROLE_KEY']

def test_env():
  p=Path('.env'); assert p.exists(), '.env missing'
  env={}
  for line in p.read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
      k,v=line.split('=',1); env[k]=v
  missing=[k for k in REQ if not env.get(k)]
  assert not missing, f'Missing vars: {missing}'
  for k in SECRET_KEYS:
    assert len(env.get(k,''))>=12, f'{k} too short'
