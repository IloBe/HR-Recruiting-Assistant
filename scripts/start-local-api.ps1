Push-Location "c:/Program Files/myRepos/recruitment-assistant"
uv venv
uv run pip install -r recruitment_assistant/requirements.txt
uv run uvicorn recruitment_assistant.api.main:app --host 0.0.0.0 --port 8000 --reload
Pop-Location
