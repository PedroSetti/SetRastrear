import sys
from sqlalchemy import select,delete
from .main import SessionLocal,User,Device,Location,now,audit
with SessionLocal() as s:
 if sys.argv[1]=='admin':
  u=s.scalar(select(User).where(User.email==sys.argv[2]))
  if not u: raise SystemExit('Cadastre a conta antes')
  u.admin=True;audit(s,u.id,'admin_granted');s.commit()
 elif sys.argv[1]=='purge':
  for u in s.scalars(select(User)):
   s.execute(delete(Location).where(Location.device.in_(select(Device.id).where(Device.owner==u.id)),Location.timestamp<now()-u.retention_days*86400))
  s.commit()
