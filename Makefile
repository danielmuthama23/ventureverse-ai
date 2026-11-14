.PHONY: install dev-api dev-web build serve test e2e
install:
	pip install -r backend/requirements-dev.txt
	cd frontend && npm install
dev-api:        ## API with auto-reload on :8000
	cd backend && uvicorn app.main:app --reload --port 8000
dev-web:        ## Vite dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev
build:
	cd frontend && npm run build
serve: build    ## API + built frontend on :8000
	cd backend && uvicorn app.main:app --port 8000
test:
	cd backend && python -m pytest -q
e2e:            ## needs the server on :8000 and playwright installed
	cd e2e && npm install && node smoke.mjs
