from sqlalchemy.orm import Relationship,DeclarativeBase
from sqlalchemy import ForeignKey,Column,INTEGER,String
from sqlalchemy import create_engine
import os
from sqlalchemy import desc,asc

class Base(DeclarativeBase):
    pass

class USER(Base):
    __tablename__ = "user"
    id = Column(INTEGER,primary_key=True)
    name = Column(String(256))


class flow(Base):
    __tablename__="flow"
    id = Column(INTEGER,primary_key=True)
    USER_ID = Column(ForeignKey(USER.id,onupdate="CASCADE", ondelete="CASCADE"))
    flow_name = Column(String(256))
    user = Relationship("USER",backref="public_history") # 可以通过查询flow.user直接访问user, 也可以在 通过 user.public_history 查询到所有的flow

    def __repr__(self) -> str:
        return f"id:{self.id}"


from sqlalchemy.orm import Session

url= "sqlite:///" + os.path.join(os.path.dirname(__file__), 'test.db')
engine = create_engine(url, echo=True)

Base.metadata.create_all(engine)

session = Session(bind=engine)

# user1= USER(name="test")
# session.add(user1)
# session.add(user1)
# session.flush()

flow1 = flow(USER_ID=1,flow_name="flow1")
session.add(flow1)
session.flush()
# flow1.flush()
print(flow1.user)
# flow2 = flow(USER_ID=user1.id,flow_name="flow2")
# session.add_all([flow1,flow2])
session.commit()
# print(flow1.user)
# print(user1.public_history)
# flows=session.query(flow).order_by((asc(flow.id))).all()
# print(flows)

