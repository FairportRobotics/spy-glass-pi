PYTHON ?= python3
VENV := .venv

.PHONY: install install-service run test

install:
	sudo apt-get update
	sudo apt-get install -y python3-venv python3-picamera2 python3-opencv imx500-all imx500-tools
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	mkdir -p models

install-service:
	sudo useradd --system --home-dir /opt/spy-glass --create-home --shell /usr/sbin/nologin spyglass
	sudo chown -R spyglass:spyglass /opt/spy-glass
	sudo install -d -o spyglass -g spyglass /var/lib/spy-glass
	sudo cp deploy/spy-glass.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable --now spy-glass

run:
	$(VENV)/bin/python -m spyglass

test:
	$(VENV)/bin/python -m unittest discover -s tests -v
