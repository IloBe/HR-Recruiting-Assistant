Push-Location "c:/Program Files/myRepos/recruitment-assistant"
uv venv
uv run pip install -r recruitment_assistant/requirements.txt
uv run python -m streamlit run recruitment_assistant/ui/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Pop-Location
