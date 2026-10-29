"""Запуск: python -m bala  (или uvicorn bala.app:app)."""
import os

import uvicorn

if __name__ == '__main__':
    uvicorn.run('bala.app:app', host=os.getenv('BALA_HOST', '0.0.0.0'), port=int(os.getenv('BALA_PORT', '8000')), proxy_headers=True, forwarded_allow_ips='*')
