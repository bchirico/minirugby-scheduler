.PHONY: install test lint format run all

install:
	pip3 install -r requirements.txt

test:
	python3 -m pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

run:
	python3 app.py

all: format lint test
