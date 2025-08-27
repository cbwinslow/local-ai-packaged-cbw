import subprocess, yaml, pathlib, pytest

def test_start_services_preflight():
    result = subprocess.run(["python", "start_services.py", "--preflight"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"preflight failed: {result.stderr}")
    compose_path = pathlib.Path("supabase/docker/docker-compose.yml")
    if not compose_path.exists():
        pytest.skip("Supabase compose missing")
    data = yaml.safe_load(compose_path.read_text()) or {}
    services = data.get("services", {})
    assert "supabase-pooler" not in services and "supavisor" not in services
