#!/usr/bin/python3
import os
import requests
import json
import sys
from typing import List, Dict

# Load environment variables from .env
def load_env():
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value.strip('"').strip("'")
    return env_vars

# Load environment variables
env_vars = load_env()

# Cloudflare API configuration
API_TOKEN = env_vars.get('CLOUDFLARE_API_TOKEN')
if not API_TOKEN:
    print("Error: CLOUDFLARE_API_TOKEN not found in .env file")
    print("Please add your Cloudflare API token to the .env file:")
    print("CLOUDFLARE_API_TOKEN=your_token_here")
    sys.exit(1)

ZONE_NAME = "opendiscourse.net"
BASE_URL = "https://api.cloudflare.com/client/v4"

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def get_zone_id(zone_name: str) -> str:
    """Get the zone ID for a domain."""
    response = requests.get(
        f"{BASE_URL}/zones?name={zone_name}",
        headers=HEADERS
    )
    try:
        response.raise_for_status()
        result = response.json()
        if not result['success']:
            print(f"Error getting zone ID: {result['errors']}")
            return None
        zones = result["result"]
        return zones[0]["id"] if zones else None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error getting zone ID: {e}")
        print("Response:", e.response.text)
        return None
    except Exception as e:
        print(f"Error getting zone ID: {e}")
        return None

def get_current_records(zone_id: str) -> List[Dict]:
    """Get current DNS records."""
    response = requests.get(
        f"{BASE_URL}/zones/{zone_id}/dns_records",
        headers=HEADERS
    )
    try:
        response.raise_for_status()
        result = response.json()
        if not result['success']:
            print(f"Error getting DNS records: {result['errors']}")
            return []
        return result["result"]
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error getting DNS records: {e}")
        print("Response:", e.response.text)
        return []
    except Exception as e:
        print(f"Error getting DNS records: {e}")
        return []

def create_or_update_record(zone_id: str, name: str, target_ip: str, existing_records: List[Dict]) -> None:
    """Create or update an A record."""
    # Check if record exists
    existing = next(
        (r for r in existing_records if r["name"] == name and r["type"] == "A"),
        None
    )
    
    record_data = {
        "type": "A",
        "name": name,
        "content": target_ip,
        "ttl": 1,  # Auto TTL
        "proxied": True  # Enable Cloudflare proxy
    }

    if existing:
        # Update existing record
        response = requests.put(
            f"{BASE_URL}/zones/{zone_id}/dns_records/{existing['id']}",
            headers=HEADERS,
            json=record_data
        )
    else:
        # Create new record
        response = requests.post(
            f"{BASE_URL}/zones/{zone_id}/dns_records",
            headers=HEADERS,
            json=record_data
        )
    
    try:
        response.raise_for_status()
        result = response.json()
        if not result['success']:
            print(f"Error {'updating' if existing else 'creating'} record for {name}: {result['errors']}")
            return
        print(f"{'Updated' if existing else 'Created'} record for {name}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error {'updating' if existing else 'creating'} record for {name}: {e}")
        print("Response:", e.response.text)
    except Exception as e:
        print(f"Error {'updating' if existing else 'creating'} record for {name}: {e}")

def main():
    # Read environment variables from .env
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value

    # Extract target IP (you'll need to provide this)
    target_ip = input("Enter the target IP address for the Hetzner server: ")

    # List of subdomains to configure
    subdomains = [
        env_vars.get('N8N_HOSTNAME', 'n8n.opendiscourse.net'),
        env_vars.get('WEBUI_HOSTNAME', 'openwebui.opendiscourse.net'),
        env_vars.get('FLOWISE_HOSTNAME', 'flowise.opendiscourse.net'),
        env_vars.get('SUPABASE_HOSTNAME', 'supabase.opendiscourse.net'),
        env_vars.get('OLLAMA_HOSTNAME', 'ollama.opendiscourse.net'),
        env_vars.get('SEARXNG_HOSTNAME', 'searxng.opendiscourse.net'),
        env_vars.get('NEO4J_HOSTNAME', 'neo4j.opendiscourse.net'),
        # Additional services
'rabbitmq.opendiscourse.net',  # For RabbitMQ management interface
'grafana.opendiscourse.net',   # For Grafana dashboards
'prometheus.opendiscourse.net', # For Prometheus
'langfuse.opendiscourse.net',  # For Langfuse UI
'graphite.opendiscourse.net',  # For Graphite web interface
'weaviate.opendiscourse.net',  # For Weaviate vector DB
'localai.opendiscourse.net',   # For LocalAI API
'vectorpg.opendiscourse.net',  # For VectorPG interface
'api.opendiscourse.net',       # Main API endpoint
    ]

    # Get zone ID
    zone_id = get_zone_id(ZONE_NAME)
    if not zone_id:
        print(f"Error: Could not find zone ID for {ZONE_NAME}")
        return

    # Get current records
    existing_records = get_current_records(zone_id)

    # Create/update records for each subdomain
    for subdomain in subdomains:
        create_or_update_record(zone_id, subdomain, target_ip, existing_records)

    print("\nDNS records configuration completed!")
    print("\nNOTE: DNS changes may take up to 24 hours to propagate fully, though often they are much faster.")
    print("You can verify the records in your Cloudflare dashboard.")

if __name__ == "__main__":
    main()
