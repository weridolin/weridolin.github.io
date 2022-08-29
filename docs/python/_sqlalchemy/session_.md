## session
当需要进行数据库的操作,**sqlalchemy**需要通过**DBAPI**与数据库建立链接.session可以看作这个connection的代理,sqlalchemy的增删改查都通过**session**来完成。

- identity_map
session.identity_map存放所有orm对象,当进行add操作,并且**commit()**完成后,identity_map**只会保留最近调用的add的传入条目**,比如调用了两次add(record),则只会cache第二次add()传入的record（第一次会被生成对应的sql语句,并从map中移除,但此时还没执行）,query的情况下也一样，只会保留最近query的一次结果


## orm对象的状态
当我们把一个实例化了一个ORM对象,并且对其增删改查操作，其状态可分为以下四种:
- 1. 临时状态(transient):即该实例还没有添加到session里面.此时该实例还没有数据库自增的id
- 2. 挂起状态(pending):当调用了session.add()方法,把该实例添加到session中时的状态,此时仍让没有同步到数据库,也不会有自增id
- 3. 持久化(persistent):当该实例被持久化到数据库后的状态,即调用了flush后,或者从数据库query出来的数据。
- 4. 删除(deleted):当删除了一个对象，并且session已经flush.(但transaction仍未完成)时的状态，当transaction完成后，状态变成了**detached**状态,当session rollback后变成了**persistent** 状态
- 5. 分离(Detached):当前对象在数据库中有对应的记录，但不存在任何session中的状态。此时该实例拥有数据库对应的自增ID


## session.expunge(orm)
session.expunge可以将persistent状态的实例移出session,并且使其状态为**detached**,或者将**pending**状态的改为**transient**状态

## Refreshing / Expiring
session.expire()/refresh()会把session中的所有orm对象设置为过期,当下次访问时,会执行对应的sql从数据库中拿到最新的数据。一般用于从数据库中强行刷新数据。

## flush/commit
session.flush()会把session中的orm对象生成对应SQL,但此时并持久化到数据库，但是会生成对应的自增ID,flush时commit的一部分


```python



```