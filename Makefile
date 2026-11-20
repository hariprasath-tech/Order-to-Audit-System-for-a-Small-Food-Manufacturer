.PHONY: help build up down restart logs shell test migrate seed benchmark reconcile clean lint

help:
	@echo "Order-to-Audit Snack Factory Makefile"
	@echo "Usage:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start web and PostgreSQL containers"
	@echo "  make down        - Stop all containers"
	@echo "  make restart     - Restart web service"
	@echo "  make logs        - Tail web container logs"
	@echo "  make test        - Run pytest suite inside web container"
	@echo "  make migrate     - Run Django database migrations"
	@echo "  make seed        - Load benchmark master data (flour, oil, pouches, etc.)"
	@echo "  make benchmark   - Run automated end-to-end headless benchmark verification"
	@echo "  make reconcile   - Run inventory ledger reconciliation"
	@echo "  make shell       - Open Django interactive shell"
	@echo "  make lint        - Run ruff linter check"
	@echo "  make clean       - Remove containers and database volumes"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart web

logs:
	docker compose logs -f web

test:
	docker compose exec web pytest -v

migrate:
	docker compose exec web python manage.py migrate

seed:
	docker compose exec web python manage.py seed_benchmark

benchmark:
	docker compose exec web python manage.py run_benchmark

reconcile:
	docker compose exec web python manage.py reconcile_stock

shell:
	docker compose exec web python manage.py shell

lint:
	ruff check .

clean:
	docker compose down -v
