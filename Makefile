PYTHON ?= python3
VENV := .venv

.PHONY: install run test

install:
	sudo apt-get update
	sudo apt-get install -y python3-venv python3-picamera2 python3-opencv imx500-all imx500-tools
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	mkdir -p models

run:
	$(VENV)/bin/python -m spyglass

test:
	$(VENV)/bin/python -m unittest discover -s tests -v
