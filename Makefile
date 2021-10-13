

.PHONY: install-piptools install-deps install-dev update-deps tests install-user-unit setup-install pip-install

upgrade-pip:
	python3 -m pip install --upgrade pip

install-piptools:
	pip3 install pip-tools toml

install-deps:
	pip3 install -r requirements.txt

install-deps-dev: install-piptools
	pip3 install -r requirements.dev.txt

update-requirements:
	pip-compile
	pip-compile requirements.in requirements.dev.in --output-file requirements.dev.txt

install:
	pip3 install ./

install-dev:
	pip3 install --user -e ".[dev]"

lint:
	flake8
tests:
	pytest -vs --disable-warnings tests

format:
	yapf -ir ./

install-user-unit:
	mkdir -p ~/.config/systemd/user/
	cp service/lxdrunner.service ~/.config/systemd/user/

setup-install:
	python3 setup.py install

pip-install:
	pip install ./

