# DevSentinel — Developer Commands

.PHONY: install api dashboard seed test

install:
	pip install -r requirements.txt

api:
	uvicorn main:app --host 0.0.0.0 --port 8080 --reload

dashboard:
	streamlit run dashboard/app.py --server.port 8501

seed:
	python migrations/seed_incidents.py

test:
	pytest tests/ -v

dev:
	@echo "Starting DevSentinel in dev mode..."
	@start /B uvicorn main:app --host 0.0.0.0 --port 8080 --reload
	@streamlit run dashboard/app.py --server.port 8501
