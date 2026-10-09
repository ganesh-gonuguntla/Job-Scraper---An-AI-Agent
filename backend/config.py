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

# Tunable Limits
MAX_QUERIES: int = int(os.getenv("MAX_QUERIES", "5"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "1"))
RESUME_CHAR_CAP: int = int(os.getenv("RESUME_CHAR_CAP", "6000"))
EXA_NUM_RESULTS: int = int(os.getenv("EXA_NUM_RESULTS", "8"))
MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "15"))
JOB_TOKEN_CAP: int = int(os.getenv("JOB_TOKEN_CAP", "900"))  # chars ~ 3600
GROQ_BATCH_TOKEN_BUDGET: int = int(os.getenv("GROQ_BATCH_TOKEN_BUDGET", "3000"))
MAX_TO_SCORE: int = int(os.getenv("MAX_TO_SCORE", "15"))
GOOD_JOBS_MIN: int = int(os.getenv("GOOD_JOBS_MIN", "5"))
LLM_DELAY_SECONDS: float = float(os.getenv("LLM_DELAY_SECONDS", "2.0"))
FX_USD_INR: float = float(os.getenv("FX_USD_INR", "83.0"))

# Provider Keys
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")

# Operation Modes
MOCK_LLM: bool = os.getenv("MOCK_LLM", "false").lower() in ("true", "1", "yes")

# Database & Checkpointer paths
DATA_DIR = root_dir / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "checkpoints.db"
CACHE_DB_PATH = DATA_DIR / "cache.db"

# LLM Models
GEMINI_MODEL = "gemini-1.5-flash"
GROQ_MODEL = "llama-3.1-8b-instant"
