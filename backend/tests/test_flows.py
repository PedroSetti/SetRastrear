import os,secrets,time
os.environ['JWT_SECRET']=secrets.token_hex(32)
os.environ['DATABASE_URL']='sqlite://'
import pytest,jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app import main as m

@pytest.fixture(autouse=True)
def database():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 m.SessionLocal=sessionmaker(engine,expire_on_commit=False);m.Base.metadata.create_all(engine);m.attempts.clear()
 yield
 m.Base.metadata.drop_all(engine)
def client():return TestClient(m.app,base_url='https://testserver')
def register(c,email='pedro@example.com'):
 return c.post('/api/auth/register',json={'name':'Pedro','email':email,'password':'SuperSenhaSegura123!','confirm_password':'SuperSenhaSegura123!','terms':True})
def login(c,email='pedro@example.com'):
 r=c.post('/api/auth/login',json={'email':email,'password':'SuperSenhaSegura123!'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['access_token']}
def install(c):
 r=c.post('/api/device/install');assert r.status_code==201
 return r.json()['device_id'],{'Authorization':'Bearer '+r.json()['device_token']}
def pair(c,h,dh):
 p=c.post('/api/device/pairing',headers=dh).json()
 assert c.post('/api/devices/pair',headers=h,json={'code':p['code'],'name':'Meu celular'}).status_code==202
 status=c.get('/api/device/status',headers=dh).json()
 assert c.post('/api/devices/pair/confirm',headers=dh,json={'pairing_id':status['pending']['id'],'authorize':True}).status_code==200
def point(c,dh):return c.post('/api/device/location',headers=dh,json={'latitude':-23.55,'longitude':-46.63,'accuracy':15,'battery':72,'timestamp':int(time.time())})
def test_registration_and_login():
 c=client();assert register(c).status_code==201;assert register(c).status_code==409;h=login(c)
 assert c.get('/api/account',headers=h).json()['email']=='pedro@example.com'
 with m.SessionLocal() as s:assert s.scalar(select(m.User)).password.startswith('$argon2')
def test_terms_password_validation():
 c=client();data={'name':'Pedro','email':'p@example.com','password':'abcdefgh123456','confirm_password':'different','terms':True}
 assert c.post('/api/auth/register',json=data).status_code==422
def test_logout_revokes_access():
 c=client();register(c);h=login(c);assert c.post('/api/auth/logout',headers=h).status_code==200
 assert c.get('/api/account',headers=h).status_code==401
def test_refresh_rotation_replay_revokes_session():
 c=client();register(c);h=login(c);old=c.cookies.get('refresh');assert c.post('/api/auth/refresh').status_code==200
 evil=client();evil.cookies.set('refresh',old);assert evil.post('/api/auth/refresh').status_code==401
 assert c.get('/api/account',headers=h).status_code==401
def test_pair_requires_device_confirmation():
 c=client();register(c);h=login(c);id,dh=install(c);p=c.post('/api/device/pairing',headers=dh).json()
 assert c.post('/api/devices/pair',headers=h,json={'code':p['code'],'name':'Celular'}).status_code==202
 assert c.get('/api/devices',headers=h).json()==[];assert point(c,dh).status_code==403
 pending=c.get('/api/device/status',headers=dh).json()['pending']
 assert c.post('/api/devices/pair/confirm',headers=h,json={'pairing_id':pending['id'],'authorize':True}).status_code==401
 assert c.post('/api/devices/pair/confirm',headers=dh,json={'pairing_id':pending['id'],'authorize':False}).status_code==200
 assert c.get('/api/devices',headers=h).json()==[]
def test_link_location_history_and_unlink():
 c=client();register(c);h=login(c);id,dh=install(c);pair(c,h,dh);assert point(c,dh).status_code==201
 assert len(c.get(f'/api/devices/{id}/history',headers=h).json())==1
 assert c.delete(f'/api/devices/{id}/history',headers=h).status_code==200
 assert c.get(f'/api/devices/{id}/history',headers=h).json()==[]
 assert c.delete(f'/api/devices/{id}',headers=h).status_code==200
 assert point(c,dh).status_code==401
def test_cross_account_isolation():
 c=client();register(c);h=login(c);id,dh=install(c);pair(c,h,dh);point(c,dh)
 other=client();register(other,'other@example.com');oh=login(other,'other@example.com')
 for path in ['location','history']:assert other.get(f'/api/devices/{id}/{path}',headers=oh).status_code==404
 assert other.delete(f'/api/devices/{id}',headers=oh).status_code==404
 assert other.delete(f'/api/devices/{id}/history',headers=oh).status_code==404
def test_pause_blocks_upload():
 c=client();register(c);h=login(c);_,dh=install(c);pair(c,h,dh)
 assert c.patch('/api/device/settings',headers=dh,json={'enabled':False,'interval':60}).status_code==200
 assert point(c,dh).status_code==403
def test_invalid_pair_rate_limit():
 c=client();register(c);h=login(c)
 for _ in range(5):assert c.post('/api/devices/pair',headers=h,json={'code':'RMB-INVALID','name':'x'}).status_code==400
 assert c.post('/api/devices/pair',headers=h,json={'code':'RMB-INVALID','name':'x'}).status_code==429
def test_pair_code_has_no_time_expiration(monkeypatch):
 c=client();register(c);h=login(c);_,dh=install(c);p=c.post('/api/device/pairing',headers=dh).json()
 assert p['expires'] is None
 future=m.now()+86400*365*10
 with m.SessionLocal() as s:
  pairing=s.scalar(select(m.Pairing));assert pairing.expires==0
  session=s.scalar(select(m.LoginSession));session.expires=future+3600;s.commit()
 monkeypatch.setattr(m,'now',lambda:future)
 assert c.post('/api/devices/pair',headers=h,json={'code':p['code'],'name':'x'}).status_code==202
 pending=c.get('/api/device/status',headers=dh).json()['pending']
 assert pending is not None
 assert c.post('/api/devices/pair/confirm',headers=dh,json={'pairing_id':pending['id'],'authorize':True}).status_code==200
def test_new_code_invalidates_previous_code():
 c=client();register(c);h=login(c);_,dh=install(c)
 old=c.post('/api/device/pairing',headers=dh).json()['code']
 new=c.post('/api/device/pairing',headers=dh).json()['code']
 assert old!=new
 assert c.post('/api/devices/pair',headers=h,json={'code':old,'name':'x'}).status_code==400
 assert c.post('/api/devices/pair',headers=h,json={'code':new,'name':'x'}).status_code==202
def test_expired_jwt():
 c=client();register(c);h=login(c);claims=jwt.decode(h['Authorization'][7:],m.SECRET,algorithms=['HS256'],audience='web');claims['exp']=0
 assert c.get('/api/account',headers={'Authorization':'Bearer '+jwt.encode(claims,m.SECRET,algorithm='HS256')}).status_code==401
def test_admin_does_not_bypass_owner():
 c=client();register(c);h=login(c);id,dh=install(c);pair(c,h,dh);point(c,dh)
 a=client();register(a,'admin@example.com');ah=login(a,'admin@example.com')
 assert a.get('/api/admin/overview',headers=ah).status_code==403
 with m.SessionLocal() as s:u=s.scalar(select(m.User).where(m.User.email=='admin@example.com'));u.admin=True;s.commit()
 r=a.get('/api/admin/overview',headers=ah);assert r.status_code==200;assert 'latitude' not in r.text
 assert a.get(f'/api/devices/{id}/location',headers=ah).status_code==404
def test_csrf_origin():
 assert client().post('/api/device/install',headers={'Origin':'https://evil.example'}).status_code==403
def test_delete_account_revokes_device():
 c=client();register(c);h=login(c);_,dh=install(c);pair(c,h,dh)
 assert c.delete('/api/account',headers=h).status_code==200
 assert c.get('/api/account',headers=h).status_code==401
 assert point(c,dh).status_code==401
def test_login_bruteforce():
 c=client();register(c)
 for _ in range(10):assert c.post('/api/auth/login',json={'email':'pedro@example.com','password':'bad'}).status_code==401
 assert c.post('/api/auth/login',json={'email':'pedro@example.com','password':'bad'}).status_code==429
def test_reset_token_expires_and_revokes_sessions():
 c=client();register(c);h=login(c)
 with m.SessionLocal() as s:
  u=s.scalar(select(m.User));s.add(m.Reset(id=m.digest('testtoken'),user=u.id,expires=m.now()+60));s.commit()
 assert c.post('/api/auth/reset',json={'token':'testtoken','password':'AnotherStrongPassword123'}).status_code==200
 assert c.get('/api/account',headers=h).status_code==401
 assert c.post('/api/auth/reset',json={'token':'testtoken','password':'AnotherStrongPassword123'}).status_code==400
def test_invalid_coordinates():
 c=client();_,dh=install(c)
 assert c.post('/api/device/location',headers=dh,json={'latitude':100,'longitude':0,'accuracy':0,'timestamp':int(time.time())}).status_code==422
