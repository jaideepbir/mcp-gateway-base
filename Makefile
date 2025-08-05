up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	docker-compose exec opa run-tests

policy-test:
	docker-compose exec opa run-policy-tests

db-migrate:
	# Placeholder for database migration command
	echo "Database migration not implemented yet"
