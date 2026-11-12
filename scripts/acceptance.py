import os, subprocess, sys, time, requests
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:18766'
def main():
 env=os.environ.copy(); env['TASK_API_DB']=str(ROOT/'data'/'acceptance.sqlite3'); env['TASK_API_TOKEN_SECRET']='self-test-secret'
 p=subprocess.Popen([str(ROOT/'.venv'/'Scripts'/'python.exe'),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','18766'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  for _ in range(50):
   try:
    if requests.get(BASE+'/health',timeout=1).status_code==200: break
   except requests.RequestException: time.sleep(.2)
  def ck(v,n):
   assert v,n; print('PASS',n)
  ck(requests.get(BASE+'/health').json()=={'status':'ok'},'health')
  users=[]
  for n in ('alice','bobby'):
   requests.post(BASE+'/api/v1/auth/register',json={'username':n,'password':'Password123'}).raise_for_status()
   tok=requests.post(BASE+'/api/v1/auth/login',json={'username':n,'password':'Password123'}).json()['access_token']; users.append({'Authorization':'Bearer '+tok})
  ck(requests.get(BASE+'/api/v1/projects').status_code==401,'missing token rejected')
  ck(requests.get(BASE+'/api/v1/projects',headers={'Authorization':'Bearer bad'}).status_code==401,'invalid token rejected')
  a,b=users
  pr=requests.post(BASE+'/api/v1/projects',headers=a,json={'name':' Alpha '}); ck(pr.status_code==201 and pr.json()['name']=='Alpha','project create and trim'); pid=pr.json()['id']
  ck(requests.get(BASE+f'/api/v1/projects/{pid}',headers=b).status_code==404,'cross-user project read blocked')
  task=requests.post(BASE+f'/api/v1/projects/{pid}/tasks',headers=a,json={'title':'Task'}); ck(task.status_code==201,'task create'); tid=task.json()['id']
  ck(requests.get(BASE+f'/api/v1/tasks/{tid}',headers=b).status_code==404,'cross-user task read blocked')
  ck(requests.patch(BASE+f'/api/v1/tasks/{tid}',headers=a,json={'status':'invalid'}).status_code==400,'invalid task status rejected')
  ck(requests.delete(BASE+f'/api/v1/projects/{pid}',headers=a).status_code==204,'project deletion succeeds')
  ck(requests.get(BASE+f'/api/v1/tasks/{tid}',headers=a).status_code==404,'cascade task deletion')
  print('ALL ACCEPTANCE CHECKS PASSED')
 finally:
  p.kill(); p.wait(timeout=10)
if __name__=='__main__': main()
