import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import ForeignKey

SQLALCHEMY_URL = "sqlite:///" + \
    os.path.join(os.path.dirname(__file__), 'scheduler.db')

engine = sa.create_engine(
    SQLALCHEMY_URL, 
    echo=True)
SessionFactory = sessionmaker(bind=engine, autoflush=True)
session = SessionFactory()
DeclarativeBase = declarative_base()

############ 第一种继承 ， 多个表JOIN查询, 其实就是子类为父类的一个外键 ####################

class Employee(DeclarativeBase):
    __tablename__ = "employee"
    id=sa.Column(sa.Integer,primary_key=True)
    name=sa.Column(sa.String)
    type=sa.Column(sa.String)

    __mapper_args__ = {
        "polymorphic_identity": "employee",
        # "polymorphic_on": "type",
    }

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

class Engineer(Employee):
    __tablename__ = "engineer"
    id= sa.Column(ForeignKey("employee.id"), primary_key=True)
    engineer_name=sa.Column(sa.String)
    __mapper_args__ = {
        "polymorphic_identity": "engineer",
    }


class Manager(Employee):
    __tablename__ = "manager"
    id= sa.Column(ForeignKey("employee.id"), primary_key=True)

    manager_name=sa.Column(sa.String)
    __mapper_args__ = {
        "polymorphic_identity": "manager",
    }


################# 第二种继承, 代表着一个查询结果可以返回多种结果，#####################
class Employee2(DeclarativeBase):
    __tablename__ = "employee2"
    __allow_unmapped__ = True
    id=sa.Column(sa.Integer,primary_key=True)
    name=sa.Column(sa.String)
    type=sa.Column(sa.String)

    __mapper_args__ = {
        "polymorphic_identity": "employee",
        "polymorphic_on": "type",
    }


    def update(self):
        ## 
        pass

class Manager2(Employee2):
    manager_data: sa.Column(sa.String,nullable=True)


    __mapper_args__ = {
        "polymorphic_identity": "manager2",
    }

    def update(self):
        return super().update()

class Engineer2(Employee2):
    engineer_info: sa.Column(sa.String,nullable=True)


    __mapper_args__ = {
        "polymorphic_identity": "engineer2",
    }

    def update(self):
        return super().update()


##################### 第三种继承,继承子类为独立的表，不需要外键关联 ###################

class Employee3(DeclarativeBase):
    __tablename__ = "employee3"
    id=sa.Column(sa.Integer,primary_key=True)
    name=sa.Column(sa.String)
    type=sa.Column(sa.String)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

class Engineer3(Employee3):
    __tablename__ = "engineer3"
    id=sa.Column(sa.Integer,primary_key=True)
    engineer_name=sa.Column(sa.String)
    __mapper_args__ = {
        "concrete": True,
    }


class Manager3(Employee3):
    __tablename__ = "manager3"
    id=sa.Column(sa.Integer,primary_key=True)
    manager_name=sa.Column(sa.String)
    __mapper_args__ = {
        "concrete": True,
    }

DeclarativeBase.metadata.create_all(engine)

# session.query(Employee).all()
# session.query(Engineer).all()
# session.query(Manager).all()


# session.query(Employee2).all()
# session.query(Engineer2).all()
# session.query(Manager2).all()



session.query(Employee3).all()
session.query(Engineer3).all()
session.query(Manager3).all()


