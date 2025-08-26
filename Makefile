.PHONY: bootstrap deploy logs down test dns-apply

bootstrap:
	sudo ./scripts/supa-container-bootstrap.sh CREATE_USER=true CBW_PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINIEs0Bgiq6JOaoYOUUcJgsgIs1MM0KqhwTF5W+Y1Hq3'

deploy:
	sudo DOMAIN=opendiscourse.net EMAIL=admin@opendiscourse.net ./scripts/supa-container-deploy.sh

logs:
	cd compose && docker compose logs -f --tail=200

down:
	cd compose && docker compose down

test:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip pytest requests dnspython
	DOMAIN=opendiscourse.net EXPECTED_IPV4=YOUR.SERVER.IP . .venv/bin/activate && pytest -q

dns-apply:
	cd terraform/dns && terraform init && terraform apply
