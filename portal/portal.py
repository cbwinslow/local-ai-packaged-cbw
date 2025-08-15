import os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.getenv("PORT", "8085"))

TEMPLATE = """<!doctype html><html lang=en><head><meta charset=utf-8><title>Local AI Portal</title>
<style>body{font-family:system-ui,Arial,sans-serif;margin:2rem;max-width:880px}h1{margin-top:0}code{background:#f5f5f5;padding:2px 4px;border-radius:4px}section{margin-bottom:2rem}a{color:#0366d6;text-decoration:none}a:hover{text-decoration:underline}ul{line-height:1.5}</style></head><body>
<h1>Local AI Package Portal</h1>
<p>Quick links to running services (auto-generated at container start).</p>
<section><h2>Services</h2><ul>{links}</ul></section>
<section><h2>Environment Keys (masked)</h2><ul>{envs}</ul></section>
<footer><small>Generated {host} • All secrets masked • Non-destructive.</small></footer>
</body></html>"""

LINK_ENV_MAPPING = [
    ("n8n", "N8N_HOSTNAME", "n8n", "/"),
    ("Open WebUI", "WEBUI_HOSTNAME", "openwebui", "/"),
    ("Flowise", "FLOWISE_HOSTNAME", "flowise", "/"),
    ("Supabase Studio", "SUPABASE_HOSTNAME", "supabase", "/"),
    ("Langfuse", "LANGFUSE_HOSTNAME", "langfuse", "/"),
    ("Ollama (if proxied)", "OLLAMA_HOSTNAME", "ollama", "/"),
    ("Neo4j Browser", "NEO4J_HOSTNAME", "neo4j", "/"),
    ("SearXNG", "SEARXNG_HOSTNAME", "searxng", "/"),
]

MASK_LIST = [
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "SERVICE_ROLE_KEY",
    "ANON_KEY",
    "N8N_ENCRYPTION_KEY",
    "N8N_USER_MANAGEMENT_JWT_SECRET",
]

def mask(v: str):
    if not v:
        return "(unset)"
    if len(v) <= 8:
        return "***" + v[-2:]
    return v[:4] + "…" + v[-4:]

def derive_host(host_env: str, default_sub: str):
    host = os.getenv(host_env)
    if host:
        return host, False
    base = os.getenv("BASE_DOMAIN")
    if base and default_sub:
        return f"{default_sub}.{base}", True
    return None, False

def linkify(label, host_env, default_sub, path):
    host, derived = derive_host(host_env, default_sub)
    if not host:
        return f"<li>{label}: <em>not configured</em></li>"
    scheme = "https://" if not host.startswith("http") else ""
    badge = " <small style='opacity:.6'>(derived)</small>" if derived else ""
    return f"<li><a href='{scheme}{host}{path}' target='_blank' rel='noopener'>{label}</a>{badge}</li>"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/index.html'):
            self.send_response(404)
            self.end_headers()
            return
        links_html = "".join(linkify(*triple) for triple in LINK_ENV_MAPPING)
        env_items = []
        for k in sorted(MASK_LIST):
            env_items.append(f"<li><code>{k}</code>: {mask(os.getenv(k,''))}</li>")
        body = TEMPLATE.format(links=links_html, envs="".join(env_items), host=os.getenv("HOSTNAME","portal"))
        data = body.encode()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    httpd = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Portal running on :{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
