"""应用配置:从环境变量加载,集中管理。"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BE_DIR = Path(__file__).resolve().parent.parent  # BE/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # 数据库
    database_url: str = f"sqlite:///{BE_DIR / 'data' / 'app.db'}"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # 通义千问(后续阶段使用)
    dashscope_api_key: str = ""

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
