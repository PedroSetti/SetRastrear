import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql'])
def test_provider_database_url_uses_psycopg(scheme):
    env = dict(os.environ, APP_ENV='production', DATABASE_URL=f'{scheme}://test:test@127.0.0.1/test', JWT_SECRET='runtime-test-only-secret-32-characters')
    result = subprocess.run([sys.executable, '-c', 'from app.main import engine; print(engine.url.drivername)'], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'postgresql+psycopg'


def test_production_refuses_ephemeral_sqlite():
    env = dict(os.environ, APP_ENV='production', DATABASE_URL='sqlite://', JWT_SECRET='runtime-test-only-secret-32-characters')
    result = subprocess.run([sys.executable, '-c', 'from app.main import app'], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'PostgreSQL persistente' in result.stderr


def test_combined_hosting_serves_panel_without_shadowing_api(tmp_path):
    (tmp_path / 'index.html').write_text('<!doctype html><title>SetRastrear</title>', encoding='utf-8')
    env = dict(os.environ, APP_ENV='test', WEB_DIST=str(tmp_path), DATABASE_URL='sqlite://', JWT_SECRET='runtime-test-only-secret-32-characters')
    code = '''from app.main import app
from fastapi.testclient import TestClient
with TestClient(app) as client:
 assert 'SetRastrear' in client.get('/').text
 assert client.get('/api/health').json() == {'status':'ok'}
'''
    result = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
