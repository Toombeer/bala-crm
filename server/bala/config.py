"""Настройки из переменных окружения. Полный список — в .env.example."""
import os
import secrets


class Settings:
    def __init__(self) -> None:
        self.env = os.getenv('BALA_ENV', 'dev')
        self.db_path = os.getenv('BALA_DB', os.path.join('data', 'bala.db'))
        secret = os.getenv('BALA_SECRET', '')
        if not secret:
            if self.env == 'prod':
                raise RuntimeError('BALA_SECRET обязателен в продакшене: сгенерируйте `python -c "import secrets;print(secrets.token_urlsafe(48))"`')
            secret = 'dev-secret-' + secrets.token_hex(8)
        self.secret = secret
        self.token_hours = int(os.getenv('BALA_TOKEN_HOURS', '12'))
        self.cors_origins = [o.strip() for o in os.getenv('BALA_CORS', '').split(',') if o.strip()]
        self.rates_auto = os.getenv('BALA_RATES_AUTO', '1') == '1'
        self.tz_offset_hours = int(os.getenv('BALA_TZ_OFFSET', '5'))  # Казахстан, UTC+5
        self.web_dir = os.getenv('BALA_WEB_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web'))
        self.login_attempts = int(os.getenv('BALA_LOGIN_ATTEMPTS', '10'))  # за 15 минут с одного IP


settings = Settings()
