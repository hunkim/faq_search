VENV = .fvenv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
STREAMLIT = $(VENV)/bin/streamlit
UVICORN = $(VENV)/bin/uvicorn
MODEL_ID = Huffon/sentence-klue-roberta-base

test_es: $(VENV)/bin/activate
	$(PYTHON) es.py

run_streamlit: $(VENV)/bin/activate
	$(STREAMLIT) run streamlit_app.py --server.runOnSave=true --server.enableCORS=false --server.enableXsrfProtection=false --server.port=8080

run_fastapi: $(VENV)/bin/activate
	$(UVICORN) fastapi_app:app --reload --port 8081

run_emb: $(VENV)/bin/activate
	$(UVICORN) emb_app:app --reload --port 8082

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

import_model:
	eland_import_hub_model   --url https://localhost:9200/  \
	 --hub-model-id $(MODEL_ID)  \
	  --task-type text_embedding  --clear-previous --start \
	  --ca-cert=~/es/config/certs/http_ca.crt -u elastic -p $(ELASTIC_PASSWORD)

clean:
	rm -rf __pycache__
	rm -rf $(VENV)