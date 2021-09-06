

.PHONY: install-piptools install-deps install-dev update-deps tests

upgrade-pip:
	python -m pip install --upgrade pip

install-piptools:
	pip3 install pip-tools toml

install-deps:
	pip3 install -r requirements.txt

install-dev: install-piptools
	pip3 install -r requirements.txt -r requirements.dev.txt

update-deps:
	pip-compile
	pip-compile requirements.in requirements.dev.in --output-file requirements.dev.txt

lint:
	flake8
tests:
	pytest -vs --disable-warnings tests

format:
	yapf -ir ./
