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
    return os.getenv(name) or _LOCAL_ENV.get(name) or default


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
    return get_setting("DEEPSEEK_MODEL", "deepseek-chat") or "deepseek-chat"


def get_deepseek_base_url() -> str:
    return (get_setting("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "https://api.deepseek.com").rstrip("/")
