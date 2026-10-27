import uuid,time,hashlib
from sqlalchemy import String,Float,Integer,Boolean,Text,ForeignKey
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from alembic import op
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

revision='001'
down_revision=None
def upgrade(): Base.metadata.create_all(op.get_bind())
def downgrade(): Base.metadata.drop_all(op.get_bind())
