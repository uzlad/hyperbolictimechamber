import os

class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    db_path: str = os.getenv("DB_PATH", "data/movies.db")

settings = Settings()
