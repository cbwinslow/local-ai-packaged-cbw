import pathlib

FILES = [
    "docker-compose.all-in-one.yml",
    "docker-compose.override.public.yml",
    "docker-compose.override.public.supabase.yml",
]

def test_compose_no_supavisor():
    for file in FILES:
        text = pathlib.Path(file).read_text()
        assert "supavisor" not in text
        assert "supabase-pooler" not in text
