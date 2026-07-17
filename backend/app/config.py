from pathlib import Path
from typing import Dict, Optional
import os


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "ai_literacy.db"


def _load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_LOCAL_ENV = _load_env_file(ROOT_DIR / ".env.local")


def get_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    current_env = _load_env_file(ROOT_DIR / ".env.local")
    return os.getenv(name) or current_env.get(name) or _LOCAL_ENV.get(name) or default


def get_db_path() -> Path:
    configured = get_setting("AI_LITERACY_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def get_xfyun_api_key() -> str:
    value = get_setting("XFYUN_MAAS_API_KEY", "")
    if not value:
        raise RuntimeError("XFYUN_MAAS_API_KEY is not configured")
    return value


def get_xfyun_model() -> str:
    return get_setting("XFYUN_MAAS_MODEL", "xopqwen36v35b") or "xopqwen36v35b"


def get_xfyun_base_url() -> str:
    return (
        get_setting("XFYUN_MAAS_BASE_URL", "https://maas-api.cn-huabei-1.xf-yun.com/v2")
        or "https://maas-api.cn-huabei-1.xf-yun.com/v2"
    ).rstrip("/")


def get_deepseek_api_key() -> str:
    value = get_setting("AI_LITERACY_DEEPSEEK_API_KEY") or get_setting("DEEPSEEK_API_KEY", "")
    if not value:
        raise RuntimeError("AI_LITERACY_DEEPSEEK_API_KEY or DEEPSEEK_API_KEY is not configured")
    return value


def get_deepseek_model() -> str:
    return get_setting("DEEPSEEK_MODEL", "deepseek-v4-pro") or "deepseek-v4-pro"


def get_deepseek_base_url() -> str:
    return (get_setting("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com").rstrip("/")


def get_kimi_api_key() -> str:
    value = (
        get_setting("AI_LITERACY_KIMI_API_KEY")
        or get_setting("KIMI_API_KEY")
        or get_setting("MOONSHOT_API_KEY", "")
    )
    if not value:
        raise RuntimeError("AI_LITERACY_KIMI_API_KEY, KIMI_API_KEY, or MOONSHOT_API_KEY is not configured")
    return value


def get_kimi_model() -> str:
    return get_setting("KIMI_MODEL", "kimi-k2.6") or "kimi-k2.6"


def get_kimi_base_url() -> str:
    return (get_setting("KIMI_BASE_URL", "https://api.moonshot.cn/v1") or "https://api.moonshot.cn/v1").rstrip("/")


DEFAULT_RAG_DB_PATH = BACKEND_DIR / "data" / "rag" / "zhishitupu.db"


def get_dashscope_api_key() -> str:
    value = get_setting("DASHSCOPE_API_KEY", "")
    if not value:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is not configured; set it in the environment or in .env.local"
        )
    return value


def get_dashscope_base_url() -> str:
    return (
        get_setting("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")


def get_dashscope_embedding_model() -> str:
    return get_setting("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4") or "text-embedding-v4"


def get_dashscope_embedding_dimensions() -> int:
    return int(get_setting("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024") or "1024")


def get_rag_database_path() -> Path:
    configured = get_setting("RAG_DATABASE_PATH")
    return Path(configured) if configured else DEFAULT_RAG_DB_PATH
