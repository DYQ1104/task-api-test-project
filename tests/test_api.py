import requests

def test_health(base_url): assert requests.get(base_url+'/health').json()=={'status':'ok'}
def test_registration_duplicate(base_url,user):
 r=requests.post(base_url+'/api/v1/auth/register',json={'username':user['name'],'password':user['password']}); assert r.status_code==409
def test_login_wrong_password(base_url,user):
 r=requests.post(base_url+'/api/v1/auth/login',json={'username':user['name'],'password':'WrongPass123'}); assert r.status_code==401
def test_missing_token(base_url): assert requests.get(base_url+'/api/v1/projects').status_code==401
def test_invalid_token(base_url): assert requests.get(base_url+'/api/v1/projects',headers={'Authorization':'Bearer bad'}).status_code==401
def test_project_create_list_update_delete(base_url,user):
 h=user['headers']; r=requests.post(base_url+'/api/v1/projects',headers=h,json={'name':' Alpha '}); assert r.status_code==201; p=r.json(); assert p['name']=='Alpha'
 assert requests.get(base_url+'/api/v1/projects',headers=h).json()['total']==1
 assert requests.patch(base_url+f"/api/v1/projects/{p['id']}",headers=h,json={'name':'Beta'}).json()['name']=='Beta'
 assert requests.delete(base_url+f"/api/v1/projects/{p['id']}",headers=h).status_code==204
def test_cross_user_project_is_hidden(base_url,user,project):
 requests.post(base_url+'/api/v1/auth/register',json={'username':'other'+user['name'],'password':'Password123'})
 token=requests.post(base_url+'/api/v1/auth/login',json={'username':'other'+user['name'],'password':'Password123'}).json()['access_token']
 assert requests.get(base_url+f"/api/v1/projects/{project['id']}",headers={'Authorization':'Bearer '+token}).status_code==404
def test_task_crud_and_cascade(base_url,user,project):
 h=user['headers']; pid=project['id']; r=requests.post(base_url+f'/api/v1/projects/{pid}/tasks',headers=h,json={'title':'Task'}); assert r.status_code==201; tid=r.json()['id']
 assert requests.patch(base_url+f'/api/v1/tasks/{tid}',headers=h,json={'status':'done'}).json()['status']=='done'
 assert requests.get(base_url+f'/api/v1/projects/{pid}/tasks',headers=h).json()['total']==1
 assert requests.delete(base_url+f'/api/v1/projects/{pid}',headers=h).status_code==204
 assert requests.get(base_url+f'/api/v1/tasks/{tid}',headers=h).status_code==404
def test_invalid_task_status(base_url,user,project):
 r=requests.post(base_url+f"/api/v1/projects/{project['id']}/tasks",headers=user['headers'],json={'title':'x','status':'bad'}); assert r.status_code==400
def test_expired_token_rejected(base_url,user):
 from app.auth import create_token
 # Token signature is generated with same process secret; use the helper's supported TTL to create an expired token.
 expired=create_token(999,now=1,ttl=1)
 assert requests.get(base_url+'/api/v1/projects',headers={'Authorization':'Bearer '+expired}).status_code==401

def test_validation_error_contract(base_url):
 r=requests.post(base_url+'/api/v1/auth/register',json={'username':'ab','password':'short'})
 assert r.status_code==400
 assert r.json()['error']['code']=='VALIDATION_ERROR'
 assert r.json()['error']['details']

def test_project_pagination_and_limits(base_url,user):
 h=user['headers']
 for name in ('one','two','three'):
  assert requests.post(base_url+'/api/v1/projects',headers=h,json={'name':name}).status_code==201
 result=requests.get(base_url+'/api/v1/projects?page=1&page_size=2',headers=h)
 assert result.status_code==200 and len(result.json()['items'])==2 and result.json()['total']==3
 assert requests.get(base_url+'/api/v1/projects?page=0',headers=h).status_code==400

def test_cross_user_task_update_and_delete_blocked(base_url,user,project):
 other='other'+user['name']
 requests.post(base_url+'/api/v1/auth/register',json={'username':other,'password':'Password123'}).raise_for_status()
 token=requests.post(base_url+'/api/v1/auth/login',json={'username':other,'password':'Password123'}).json()['access_token']
 foreign={'Authorization':'Bearer '+token}
 task=requests.post(base_url+f"/api/v1/projects/{project['id']}/tasks",headers=user['headers'],json={'title':'owned'}).json()
 assert requests.patch(base_url+f"/api/v1/tasks/{task['id']}",headers=foreign,json={'title':'hacked'}).status_code==404
 assert requests.delete(base_url+f"/api/v1/tasks/{task['id']}",headers=foreign).status_code==404
 assert requests.get(base_url+f"/api/v1/tasks/{task['id']}",headers=user['headers']).json()['title']=='owned'

def test_task_title_boundaries_and_unknown_fields(base_url,user,project):
 url=base_url+f"/api/v1/projects/{project['id']}/tasks"; h=user['headers']
 assert requests.post(url,headers=h,json={'title':'   '}).status_code==400
 assert requests.post(url,headers=h,json={'title':'x'*121}).status_code==400
 assert requests.patch(base_url+f"/api/v1/projects/{project['id']}",headers=h,json={'owner_id':999}).status_code==400

def test_delete_task_and_repeat_delete(base_url,user,project):
 task=requests.post(base_url+f"/api/v1/projects/{project['id']}/tasks",headers=user['headers'],json={'title':'delete'}).json()
 url=base_url+f"/api/v1/tasks/{task['id']}"
 assert requests.delete(url,headers=user['headers']).status_code==204
 assert requests.delete(url,headers=user['headers']).status_code==404
