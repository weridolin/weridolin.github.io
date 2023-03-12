####  sqlalchemy model类继承的验证结果
sqlalchemy对model类的继承的处理根据**__mapper_args__**的参数分为以下3种:        

- 1.单表:子类表示基类所有的可能出现的查询结果.基类的参数必须设置`polymorphic_on`参数来区分对应哪个子类,查询时子类会自动添加基类的
`polymorphic_on`字段作为筛选条件,**子类不需要指定表名**

```python

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

class Manager2(Employee2):
    manager_data: sa.Column(sa.String,nullable=True)
    __mapper_args__ = {
        "polymorphic_identity": "manager2",
    }


## 调用查询时,对应的生成的SQL如下.

session.query(Employee2).all()
## >>> employee2.id AS employee2_id, employee2.name AS employee2_name, employee2.type AS employee2_type FROM employee2
session.query(Engineer2).all()
## >>> SELECT employee2.id AS employee2_id, employee2.name AS employee2_name, employee2.type AS employee2_type FROM employee2 WHERE employee2.type IN ("engineer2") # 子类查询会自动增加基类设置的 type 字段.


```

- 2.多表情况1,子类必须通过外键关联到基类.查询会通过外键查询到对应的基类.**子类需要指定表名和外键**
```python
class Employee(DeclarativeBase):
    __tablename__ = "employee"
    id=sa.Column(sa.Integer,primary_key=True)
    name=sa.Column(sa.String)
    type=sa.Column(sa.String)

    __mapper_args__ = {
        "polymorphic_identity": "employee",
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

## 调用查询时,对应的生成的SQL如下.

session.query(Employee).all()
## >>> SELECT employee.id AS employee_id, employee.name AS employee_name, employee.type AS employee_type FROM employee
session.query(Engineer).all()
## >>> SELECT engineer.id AS engineer_id, employee.id AS employee_id, employee.name AS employee_name, employee.type AS employee_type, engineer.engineer_name AS engineer_engineer_name FROM employee JOIN engineer ON employee.id = engineer.id

```

- 3.多表情况2. 子类/父类完全独立的情况.需要指定 ``concrete``参数,**基表子表完全独立**.

```python

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
        "concrete": True, # 
    }

## 调用查询时,对应的生成的SQL如下.

session.query(Employee3).all()
## >>> SELECT engineer3.id AS engineer3_id, engineer3.engineer_name AS engineer3_engineer_name FROM engineer3
session.query(Engineer3).all()
## >>>  SELECT manager3.id AS manager3_id, manager3.manager_name AS manager3_manager_name FROM manager3

```


#### 结论
1. 按照当初的设想.上述方式选择只能选择第3种
2. 无论那种方式,**表字段都不可以继承,方法可以**.子表里面有用到了基表相同的字段,在子表也要重新声明,比如``ID``


上述结论.仅仅适用于继承于db.model类的再继承.

