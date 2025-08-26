.PHONY: dev install clean test db-up db-down db-reset setup dev-with-db

dev:
	uvicorn app.main:app --reload

install:
	pip install -r requirements.txt

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

test:
	python -m pytest

# Database commands
db-up:
	docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5

db-down:
	docker-compose down

db-reset:
	docker-compose down -v
	docker-compose up -d postgres
	@echo "Database reset complete. Waiting for PostgreSQL to be ready..."
	@sleep 5

# Combined commands
setup: install db-up
	@echo "Setup complete! You can now run 'make dev'"

dev-with-db: db-up dev 