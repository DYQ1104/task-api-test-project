import os, subprocess, sys, tempfile, time, uuid
from pathlib import Path
import pytest, requests
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:18767'
@pytest.fixture(scope='session')
def base_url():
    os.environ['TASK_API_TOKEN_SECRET']='pytest-secret'
    temp_dir=tempfile.TemporaryDirectory(prefix='task-api-pytest-')
    env=os.environ.copy()
    env['TASK_API_TOKEN_SECRET']='pytest-secret'
    env['TASK_API_DB']=str(Path(temp_dir.name)/'isolated.sqlite3')
    process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','18767'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if process.poll() is not None: pytest.fail(f'API exited with {process.returncode}')
            try:
                if requests.get(BASE+'/health',timeout=.5).ok: break
            except requests.RequestException: time.sleep(.2)
        else: pytest.fail('API did not become healthy')
        yield BASE
    finally:
        process.kill(); process.wait(timeout=10)
        temp_dir.cleanup()
@pytest.fixture
def user(base_url):
    name='u'+uuid.uuid4().hex[:12]; password='Password123'
    response=requests.post(base_url+'/api/v1/auth/register',json={'username':name,'password':password}); assert response.status_code==201
    token=requests.post(base_url+'/api/v1/auth/login',json={'username':name,'password':password}).json()['access_token']
    return {'name':name,'password':password,'headers':{'Authorization':'Bearer '+token}}
@pytest.fixture
def project(base_url,user):
    response=requests.post(base_url+'/api/v1/projects',headers=user['headers'],json={'name':'Project'}); assert response.status_code==201
    return response.json()
