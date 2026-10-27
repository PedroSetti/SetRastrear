import os,secrets,hashlib,time,uuid,json,smtplib
from datetime import datetime,timezone
from email.message import EmailMessage
from collections import defaultdict,deque
from fastapi import FastAPI,Depends,HTTPException,Request,Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,EmailStr,Field
from sqlalchemy import create_engine,String,Float,Integer,Boolean,Text,ForeignKey,select,delete,update
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker,Session
from pwdlib import PasswordHash
import jwt

SECRET=os.environ.get('JWT_SECRET','')
if len(SECRET)<32: raise RuntimeError('JWT_SECRET precisa ter pelo menos 32 caracteres aleatorios')
DB=os.environ.get('DATABASE_URL','sqlite:///./rastrear.db')
if DB.startswith(('postgres://','postgresql://')):
 DB='postgresql+psycopg://'+DB.split('://',1)[1]
if os.getenv('APP_ENV')=='production' and DB.startswith('sqlite'):
 raise RuntimeError('Producao exige PostgreSQL persistente; configure DATABASE_URL')
engine=create_engine(DB,pool_pre_ping=True,connect_args={'check_same_thread':False} if DB.startswith('sqlite') else {})
SessionLocal=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
def uid(): return str(uuid.uuid4())
def now(): return int(time.time())
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
class User(Base):
 __tablename__='users'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 name:Mapped[str]; email:Mapped[str]=mapped_column(unique=True); password:Mapped[str]
 terms_at:Mapped[int]=mapped_column(default=now)
 blocked:Mapped[bool]=mapped_column(default=False); admin:Mapped[bool]=mapped_column(default=False)
 retention_days:Mapped[int]=mapped_column(default=30)
class Device(Base):
 __tablename__='devices'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 secret:Mapped[str]; owner:Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
 name:Mapped[str]=mapped_column(default='Android'); enabled:Mapped[bool]=mapped_column(default=False)
 interval:Mapped[int]=mapped_column(default=60); requested:Mapped[bool]=mapped_column(default=False)
class Pairing(Base):
 __tablename__='device_pairings'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 device:Mapped[str]=mapped_column(ForeignKey('devices.id')); code:Mapped[str]=mapped_column(unique=True)
 expires:Mapped[int]; claimant:Mapped[str|None]=mapped_column(nullable=True); name:Mapped[str]=mapped_column(default='Android')
class Location(Base):
 __tablename__='device_locations'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 device:Mapped[str]=mapped_column(ForeignKey('devices.id'),index=True)
 latitude:Mapped[float]; longitude:Mapped[float]; accuracy:Mapped[float]; battery:Mapped[int|None]
 timestamp:Mapped[int]=mapped_column(index=True)
class LoginSession(Base):
 __tablename__='sessions'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 user:Mapped[str]=mapped_column(ForeignKey('users.id')); expires:Mapped[int]; revoked:Mapped[bool]=mapped_column(default=False)
class Refresh(Base):
 __tablename__='refresh_tokens'
 id:Mapped[str]=mapped_column(primary_key=True)
 session:Mapped[str]=mapped_column(ForeignKey('sessions.id')); used:Mapped[bool]=mapped_column(default=False)
class Log(Base):
 __tablename__='security_logs'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 actor:Mapped[str]; action:Mapped[str]; timestamp:Mapped[int]=mapped_column(default=now)
class Notification(Base):
 __tablename__='notifications'
 id:Mapped[str]=mapped_column(primary_key=True,default=uid)
 user:Mapped[str]=mapped_column(ForeignKey('users.id')); message:Mapped[str]; timestamp:Mapped[int]=mapped_column(default=now)
class Reset(Base):
 __tablename__='password_resets'
 id:Mapped[str]=mapped_column(primary_key=True); user:Mapped[str]; expires:Mapped[int]
app=FastAPI(title='SetRastrear — Rastrear MB',version='1.0.0')
origins=[v.strip() for v in os.getenv('CORS_ORIGINS','https://localhost:8443' if os.getenv('APP_ENV')!='production' else '').split(',') if v.strip()]
if os.getenv('RENDER_EXTERNAL_URL'):origins.append(os.environ['RENDER_EXTERNAL_URL'].rstrip('/'))
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['GET','POST','DELETE','PATCH'],allow_headers=['Authorization','Content-Type','X-CSRF'])
hasher=PasswordHash.recommended(); bearer=HTTPBearer(); attempts=defaultdict(deque)
def db():
 with SessionLocal() as s: yield s
def fail(code=403,msg='Acesso negado'): raise HTTPException(code,msg)
def audit(s,actor,action): s.add(Log(actor=actor,action=action))
def limit(key,max_count=15,window=300):
 q=attempts[key]
 while q and q[0]<time.monotonic()-window:q.popleft()
 if len(q)>=max_count: fail(429,'Muitas tentativas; aguarde')
 q.append(time.monotonic())
@app.middleware('http')
async def guard(req:Request,call_next):
 if req.method not in ('GET','HEAD','OPTIONS') and req.headers.get('origin') and req.headers['origin'] not in origins:
  return Response(status_code=403)
 try:r=await call_next(req)
 except Exception:
  with SessionLocal() as logdb:
   audit(logdb,'platform','server_error');logdb.commit()
  return Response(content='{"detail":"Erro interno"}',status_code=500,media_type='application/json')
 r.headers['X-Content-Type-Options']='nosniff';r.headers['Cache-Control']='no-store';r.headers['X-Frame-Options']='DENY'
 r.headers['Referrer-Policy']='no-referrer'
 return r
def user(auth=Depends(bearer),s:Session=Depends(db)):
 try:
  c=jwt.decode(auth.credentials,SECRET,algorithms=['HS256'],issuer='SetRastrear',audience='web',options={'require':['exp','sub','sid']})
  session=s.get(LoginSession,c['sid']); u=s.get(User,c['sub'])
  if not session or session.user!=c['sub'] or session.revoked or session.expires<now() or not u or u.blocked: fail(401)
  return u,session
 except jwt.PyJWTError: fail(401,'Sessao expirada')
def device(auth=Depends(bearer),s:Session=Depends(db)):
 d=s.scalar(select(Device).where(Device.secret==digest(auth.credentials)))
 if not d: fail(401,'Dispositivo revogado')
 return d
def owned(s,u,id):
 d=s.get(Device,id)
 if not d or d.owner!=u.id: fail(404,'Dispositivo nao encontrado')
 return d
class Register(BaseModel):
 name:str=Field(min_length=2,max_length=100);email:EmailStr;password:str=Field(min_length=12,max_length=128);confirm_password:str;terms:bool
class Login(BaseModel):
 email:EmailStr;password:str=Field(max_length=128);remember:bool=False
class Claim(BaseModel): code:str=Field(max_length=100);name:str=Field(min_length=1,max_length=100)
class Confirm(BaseModel): pairing_id:str;authorize:bool
class Position(BaseModel):
 latitude:float=Field(ge=-90,le=90);longitude:float=Field(ge=-180,le=180);accuracy:float=Field(ge=0,le=100000)
 battery:int|None=Field(default=None,ge=0,le=100);timestamp:int
class Settings(BaseModel):
 enabled:bool;interval:int
def issue(s,session,response):
 raw=secrets.token_urlsafe(48);s.add(Refresh(id=digest(raw),session=session.id));s.commit()
 response.set_cookie('refresh',raw,httponly=True,secure=True,samesite='strict',max_age=session.expires-now(),path='/api/auth')
 return {'access_token':jwt.encode({'sub':session.user,'sid':session.id,'exp':now()+600,'iat':now(),'iss':'SetRastrear','aud':'web'},SECRET,algorithm='HS256'),'expires_in':600}
@app.post('/api/auth/register',status_code=201)
def register(data:Register,request:Request,s:Session=Depends(db)):
 limit(('register',request.client.host),10)
 if not data.terms or data.password!=data.confirm_password:fail(422,'Confirme senha e termos')
 email=str(data.email).lower()
 if s.scalar(select(User).where(User.email==email)):fail(409,'Cadastro indisponivel para este email')
 u=User(name=data.name,email=email,password=hasher.hash(data.password));s.add(u);s.flush();audit(s,u.id,'register');s.commit();return {'id':u.id}
@app.post('/api/auth/login')
def login(data:Login,request:Request,response:Response,s:Session=Depends(db)):
 limit(('login-ip',request.client.host),30);limit(('login-email',str(data.email).lower()),10)
 u=s.scalar(select(User).where(User.email==str(data.email).lower()))
 valid=hasher.verify(data.password,u.password if u else DUMMY)
 if not u or not valid or u.blocked:
  audit(s,'anonymous','login_failed');s.commit();fail(401,'Credenciais invalidas')
 session=LoginSession(user=u.id,expires=now()+(2592000 if data.remember else 43200));s.add(session);s.flush();audit(s,u.id,'login');return issue(s,session,response)
DUMMY=hasher.hash(secrets.token_urlsafe(32))
@app.post('/api/auth/refresh')
def refresh(request:Request,response:Response,s:Session=Depends(db)):
 raw=request.cookies.get('refresh','');row=s.get(Refresh,digest(raw))
 if not row:fail(401)
 session=s.get(LoginSession,row.session);u=s.get(User,session.user)
 if row.used:
  session.revoked=True;s.commit();fail(401,'Reutilizacao detectada; sessao revogada')
 if session.revoked or session.expires<now() or u.blocked:fail(401)
 changed=s.execute(update(Refresh).where(Refresh.id==row.id,Refresh.used==False).values(used=True)).rowcount
 if changed!=1:session.revoked=True;s.commit();fail(401)
 return issue(s,session,response)
@app.post('/api/auth/logout')
def logout(response:Response,ctx=Depends(user),s:Session=Depends(db)):
 ctx[1].revoked=True;audit(s,ctx[0].id,'logout');s.commit();response.delete_cookie('refresh',path='/api/auth');return {'ok':True}
class Email(BaseModel): email:EmailStr
@app.post('/api/auth/forgot')
def forgot(data:Email,request:Request,s:Session=Depends(db)):
 limit(('forgot',request.client.host),5)
 u=s.scalar(select(User).where(User.email==str(data.email).lower()))
 if u:
  token=secrets.token_urlsafe(32);s.add(Reset(id=digest(token),user=u.id,expires=now()+900));s.commit()
  if os.getenv('SMTP_HOST'):
   msg=EmailMessage();msg['Subject']='Redefinir senha SetRastrear';msg['From']=os.environ['SMTP_FROM'];msg['To']=u.email
   msg.set_content((os.getenv('PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL') or 'https://localhost:8443')+'/?reset='+token)
   with smtplib.SMTP(os.environ['SMTP_HOST'],int(os.getenv('SMTP_PORT','587'))) as smtp:
    smtp.starttls();smtp.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD']);smtp.send_message(msg)
 return {'message':'Se a conta existir, enviaremos instrucoes. SMTP deve estar configurado.'}
class NewPassword(BaseModel): token:str;password:str=Field(min_length=12,max_length=128)
@app.post('/api/auth/reset')
def reset(data:NewPassword,s:Session=Depends(db)):
 row=s.get(Reset,digest(data.token))
 if not row or row.expires<now():fail(400,'Token invalido')
 u=s.get(User,row.user);u.password=hasher.hash(data.password)
 s.execute(update(LoginSession).where(LoginSession.user==u.id).values(revoked=True));s.execute(delete(Reset).where(Reset.user==u.id));audit(s,u.id,'password_reset');s.commit();return {'ok':True}
@app.post('/api/device/install',status_code=201)
def install(request:Request,s:Session=Depends(db)):
 limit(('install',request.client.host),20)
 raw=secrets.token_urlsafe(48);d=Device(secret=digest(raw));s.add(d);s.commit();return {'device_id':d.id,'device_token':raw}
@app.post('/api/device/pairing')
def pairing(d=Depends(device),s:Session=Depends(db)):
 if d.owner:fail(409,'Remova o vinculo antes de parear novamente')
 s.execute(delete(Pairing).where(Pairing.device==d.id))
 code='RMB-'+'-'.join(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4)) for _ in range(3))
 p=Pairing(device=d.id,code=digest(code),expires=0);s.add(p);s.commit();return {'code':code,'expires':None,'qr':code}
@app.post('/api/devices/pair',status_code=202)
def claim(data:Claim,request:Request,ctx=Depends(user),s:Session=Depends(db)):
 limit(('pair-user',ctx[0].id),5);limit(('pair-ip',request.client.host),15)
 p=s.scalar(select(Pairing).where(Pairing.code==digest(data.code.strip().upper()),Pairing.claimant==None))
 if not p:fail(400,'Codigo invalido ou substituido')
 changed=s.execute(update(Pairing).where(Pairing.id==p.id,Pairing.claimant==None).values(claimant=ctx[0].id,name=data.name)).rowcount
 if changed!=1:fail(409)
 audit(s,ctx[0].id,'pair_requested');s.commit();return {'status':'Aguardando autorizacao no aparelho'}
@app.get('/api/device/status')
def status(d=Depends(device),s:Session=Depends(db)):
 p=s.scalar(select(Pairing).where(Pairing.device==d.id,Pairing.claimant!=None))
 owner=s.get(User,d.owner) if d.owner else None
 return {'linked':bool(owner),'account':owner.email if owner else None,'enabled':d.enabled,'interval':d.interval,'requested':d.requested,'pending':{'id':p.id,'name':s.get(User,p.claimant).name} if p else None}
@app.post('/api/devices/pair/confirm')
def confirm(data:Confirm,d=Depends(device),s:Session=Depends(db)):
 p=s.get(Pairing,data.pairing_id)
 if not p or p.device!=d.id or not p.claimant or d.owner:fail(400)
 if data.authorize:
  d.owner=p.claimant;d.name=p.name;d.enabled=True;s.add(Notification(user=p.claimant,message='Dispositivo autorizado: '+p.name));audit(s,d.id,'pair_authorized')
 s.delete(p);s.commit();return {'linked':bool(d.owner)}
def revoke(s,d):
 s.execute(delete(Location).where(Location.device==d.id));s.execute(delete(Pairing).where(Pairing.device==d.id));s.delete(d)
@app.delete('/api/device/link')
def unlink(d=Depends(device),s:Session=Depends(db)):
 audit(s,d.id,'device_revoked');revoke(s,d);s.commit();return {'ok':True}
@app.patch('/api/device/settings')
def settings(data:Settings,d=Depends(device),s:Session=Depends(db)):
 if data.interval not in (0,5,30,60,300,600,900,1800):fail(422)
 if data.enabled and not d.owner:fail(409)
 d.enabled=data.enabled;d.interval=data.interval;s.commit();return {'ok':True}
@app.post('/api/device/location',status_code=201)
def location(data:Position,d=Depends(device),s:Session=Depends(db)):
 if not d.owner or not d.enabled:fail(403,'Compartilhamento desativado')
 if abs(data.timestamp-now())>600:fail(422,'Horario invalido')
 limit(('location',d.id),60,60)
 u=s.get(User,d.owner)
 if u.blocked:fail(403)
 s.execute(delete(Location).where(Location.device==d.id,Location.timestamp<now()-u.retention_days*86400))
 s.add(Location(device=d.id,**data.model_dump()));d.requested=False;s.commit();return {'ok':True}
def serialize(l):return {k:getattr(l,k) for k in ('latitude','longitude','accuracy','battery','timestamp')} if l else None
@app.get('/api/devices')
def devices(ctx=Depends(user),s:Session=Depends(db)):
 return [{'id':d.id,'name':d.name,'enabled':d.enabled,'interval':d.interval,'location':serialize(s.scalar(select(Location).where(Location.device==d.id,Location.timestamp>=now()-ctx[0].retention_days*86400).order_by(Location.timestamp.desc()).limit(1)))} for d in s.scalars(select(Device).where(Device.owner==ctx[0].id))]
@app.get('/api/devices/{id}/location')
def latest(id:str,ctx=Depends(user),s:Session=Depends(db)):
 owned(s,ctx[0],id);return serialize(s.scalar(select(Location).where(Location.device==id,Location.timestamp>=now()-ctx[0].retention_days*86400).order_by(Location.timestamp.desc()).limit(1)))
@app.post('/api/devices/{id}/request')
def request_location(id:str,ctx=Depends(user),s:Session=Depends(db)):
 d=owned(s,ctx[0],id);d.requested=True;s.commit();return {'message':'Solicitado; o aparelho precisa estar compartilhando e conectado'}
@app.get('/api/devices/{id}/history')
def history(id:str,start:int=0,end:int=2147483647,ctx=Depends(user),s:Session=Depends(db)):
 owned(s,ctx[0],id)
 return [serialize(l) for l in s.scalars(select(Location).where(Location.device==id,Location.timestamp>=max(start,now()-ctx[0].retention_days*86400),Location.timestamp<=end).order_by(Location.timestamp).limit(10000))]
@app.delete('/api/devices/{id}/history')
def clear_history(id:str,ctx=Depends(user),s:Session=Depends(db)):
 owned(s,ctx[0],id);s.execute(delete(Location).where(Location.device==id));audit(s,ctx[0].id,'history_deleted');s.commit();return {'ok':True}
@app.delete('/api/devices/{id}')
def remove(id:str,ctx=Depends(user),s:Session=Depends(db)):
 d=owned(s,ctx[0],id);revoke(s,d);audit(s,ctx[0].id,'unlink');s.commit();return {'ok':True}
@app.get('/api/account')
def account(ctx=Depends(user)):
 u=ctx[0];return {'id':u.id,'name':u.name,'email':u.email,'admin':u.admin,'retention_days':u.retention_days}
class Retention(BaseModel): days:int=Field(ge=1,le=365)
@app.patch('/api/account')
def retention(data:Retention,ctx=Depends(user),s:Session=Depends(db)):
 u=ctx[0];u.retention_days=data.days
 ids=select(Device.id).where(Device.owner==u.id)
 s.execute(delete(Location).where(Location.device.in_(ids),Location.timestamp<now()-data.days*86400));s.commit();return {'ok':True}
@app.delete('/api/account')
def delete_account(ctx=Depends(user),s:Session=Depends(db)):
 u=ctx[0]
 for d in s.scalars(select(Device).where(Device.owner==u.id)):revoke(s,d)
 s.execute(delete(Pairing).where(Pairing.claimant==u.id))
 ids=select(LoginSession.id).where(LoginSession.user==u.id)
 s.execute(delete(Refresh).where(Refresh.session.in_(ids)));s.execute(delete(LoginSession).where(LoginSession.user==u.id));s.execute(delete(Notification).where(Notification.user==u.id));s.execute(delete(Reset).where(Reset.user==u.id));s.delete(u);s.commit();return {'ok':True}
@app.get('/api/sessions')
def sessions(ctx=Depends(user),s:Session=Depends(db)):
 return [{'id':x.id,'expires':x.expires,'revoked':x.revoked,'current':x.id==ctx[1].id} for x in s.scalars(select(LoginSession).where(LoginSession.user==ctx[0].id))]
@app.delete('/api/sessions/{id}')
def revoke_session(id:str,ctx=Depends(user),s:Session=Depends(db)):
 row=s.get(LoginSession,id)
 if not row or row.user!=ctx[0].id:fail(404)
 row.revoked=True;s.commit();return {'ok':True}
@app.get('/api/notifications')
def notifications(ctx=Depends(user),s:Session=Depends(db)):
 return [{'message':n.message,'timestamp':n.timestamp} for n in s.scalars(select(Notification).where(Notification.user==ctx[0].id).order_by(Notification.timestamp.desc()).limit(100))]
def admin(ctx=Depends(user)):
 if not ctx[0].admin:fail(403)
 return ctx[0]
@app.get('/api/admin/overview')
def overview(u=Depends(admin),s:Session=Depends(db)):
 audit(s,u.id,'admin_overview');s.commit()
 return {'status':'ok','users':[{'id':x.id,'name':x.name,'email':x.email,'blocked':x.blocked} for x in s.scalars(select(User))], 'devices':len(list(s.scalars(select(Device.id)))),'linked':len(list(s.scalars(select(Device.id).where(Device.owner!=None)))),'sessions':[{'id':x.id,'expires':x.expires,'revoked':x.revoked} for x in s.scalars(select(LoginSession))],'audit':[{'action':x.action,'actor':x.actor,'timestamp':x.timestamp} for x in s.scalars(select(Log).order_by(Log.timestamp.desc()).limit(200))]}
class Block(BaseModel): blocked:bool
@app.patch('/api/admin/users/{id}')
def block(id:str,data:Block,u=Depends(admin),s:Session=Depends(db)):
 target=s.get(User,id)
 if not target or target.admin:fail(400)
 target.blocked=data.blocked;s.execute(update(LoginSession).where(LoginSession.user==id).values(revoked=True));audit(s,u.id,'block:'+id+':'+str(data.blocked));s.commit();return {'ok':True}
@app.get('/api/health')
def health():return {'status':'ok'}

# As rotas API são registradas antes do painel na mesma origem.
if os.getenv('WEB_DIST'):
 app.mount('/',StaticFiles(directory=os.environ['WEB_DIST'],html=True),name='painel')
