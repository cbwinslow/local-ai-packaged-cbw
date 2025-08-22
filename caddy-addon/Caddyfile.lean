# Minimal Caddyfile (no extra security headers or rate limiting)
# Switch to Caddyfile.ext later for hardened deployment.

{
	# Basic global options can remain minimal; ACME email optional
	# email {env.ACME_EMAIL}
}

{env.PORTAL_HOSTNAME} {
	reverse_proxy portal:8085
}

{env.N8N_HOSTNAME} {
	reverse_proxy n8n:5678
}

{env.FLOWISE_HOSTNAME} {
	reverse_proxy flowise:3000
}

{env.WEBUI_HOSTNAME} {
	reverse_proxy open-webui:8080
}

{env.SEARXNG_HOSTNAME} {
	reverse_proxy searxng:8080
}

{env.NEO4J_HOSTNAME} {
	reverse_proxy neo4j:7474
}

{env.LANGFUSE_HOSTNAME} {
	reverse_proxy langfuse-frontend:3000
}

{env.SUPABASE_HOSTNAME} {
	reverse_proxy kong:8000
}
