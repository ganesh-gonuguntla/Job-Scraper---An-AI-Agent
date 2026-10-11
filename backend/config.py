import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from root or backend directory
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Tunable Pipeline Limits
MAX_QUERIES: int = int(os.getenv("MAX_QUERIES", "5"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "1"))
RESUME_CHAR_CAP: int = int(os.getenv("RESUME_CHAR_CAP", "6000"))
SEARCH_NUM_RESULTS: int = int(os.getenv("SEARCH_NUM_RESULTS", "10"))
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "20"))
JOB_TOKEN_CAP: int = int(os.getenv("JOB_TOKEN_CAP", "900"))  # chars ~ 3600
GROQ_BATCH_TOKEN_BUDGET: int = int(os.getenv("GROQ_BATCH_TOKEN_BUDGET", "3000"))
MAX_TO_SCORE: int = int(os.getenv("MAX_TO_SCORE", "20"))
GOOD_JOBS_MIN: int = int(os.getenv("GOOD_JOBS_MIN", "5"))
LLM_DELAY_SECONDS: float = float(os.getenv("LLM_DELAY_SECONDS", "1.5"))
FX_USD_INR: float = float(os.getenv("FX_USD_INR", "83.0"))
MIN_DISPLAY_SCORE: int = int(os.getenv("MIN_DISPLAY_SCORE", "20"))  # Show all jobs >= 20% match

# Active Provider Keys
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENWEBNINJA_API_KEY: str = os.getenv("OPENWEBNINJA_API_KEY", "")
JSEARCH_BASE_URL: str = os.getenv("JSEARCH_BASE_URL", "https://api.openwebninja.com/jsearch")
MAX_JSEARCH_CALLS_PER_RUN: int = int(os.getenv("MAX_JSEARCH_CALLS_PER_RUN", "6"))
ADZUNA_APP_ID: str = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY: str = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_DEFAULT_COUNTRIES: list[str] = ["in", "us", "gb", "de", "ca"]
DEFAULT_COUNTRIES: list[str] = ["in", "us", "gb"]
SOURCE_TIMEOUT_SECONDS: float = float(os.getenv("SOURCE_TIMEOUT_SECONDS", "25.0"))

def log_config_startup():
    """Logs presence and length of key credentials at startup without exposing values."""
    keys = [
        ("ADZUNA_APP_ID", ADZUNA_APP_ID),
        ("ADZUNA_APP_KEY", ADZUNA_APP_KEY),
        ("OPENWEBNINJA_API_KEY", OPENWEBNINJA_API_KEY),
    ]
    print("[CONFIG STARTUP] Verifying API Credentials from .env:")
    for name, val in keys:
        status = "present" if bool(val and val.strip()) else "missing"
        length = len(val.strip()) if val else 0
        print(f"  {name:20}: {status} (length: {length})")

log_config_startup()

# Database & Checkpointer paths
DATA_DIR = root_dir / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "checkpoints.db"
CACHE_DB_PATH = DATA_DIR / "cache.db"

# LLM Models (Active Groq & Gemini Models)
GROQ_RESEARCH_MODEL = os.getenv("GROQ_RESEARCH_MODEL", "qwen/qwen3.8-27b")
GROQ_EXTRACTION_MODEL = os.getenv("GROQ_EXTRACTION_MODEL", "qwen/qwen3.8-27b")
GROQ_SCORING_MODEL = os.getenv("GROQ_SCORING_MODEL", "qwen/qwen3.8-27b")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
