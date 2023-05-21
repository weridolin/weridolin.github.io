### mongodb 分片集群的组成
mongodb的分片集群必须包含一下三个部分:  
- mongos:
集群的路由.直接与客户端连接,接收客户端请求,根据对应的分片键转发到对应的分片节点.
- config server:
保存集群的节点相关信息和一些元数据.配置服务也采取了主备模式
- Shards:   
存放数据,每个分片也可以采取主备模式


#### mongodb 的复制
mongodb的副本集是一组维护相同数据集合的mongod实例.每个副本集只能有一个主节点.主节点支持读写操作，备用节点只能支持读操作

##### docker-compose 部署副本集
- 1.先构建3个mongodb节点,这里以构建分片集群中的config节点为例子，构建一个主节点config1.两个副本节点config2,config3,`--replSet`参数表明改所属的副本集id.副本模式下节点有3种类型. a.primary:主节点 b.secondaries:从节点. c.arbiter:仲裁节点

```yaml
  # 配置服务器, 用于存储集群的元数据和配置设置 设置 config1/config2/config3为config sever副本集
  config1:
    container_name: config1
    image: mongo
    # --configsvr: 这个参数默认该节点是分片集群中的配置服务节点,默认端口为27019, 如果指定--port可不添加该参数
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10001:27017    
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config1:/data/configdb
    networks:
      - mongoCluster 


  config2:
    container_name: config2
    image: mongo
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10002:27017    
    volumes: 
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config2:/data/configdb
    networks:
      - mongoCluster 
 

  # 声明此mongod实例作为分片集群的配置服务器。默认端口是27019，默认的dbpath目录是/data/configdb，
  # 配置服务器存储集群的元数据和配置设置。从MongoDB 3.4开始，配置服务器必须部署为一个replicate set副本集，
  # 为了防止这个配置服务是单点服务。如果你的集群只有一个配置服务器，一旦这个配置服务器出现故障则集群将不可用
  config3:
    container_name: config3
    image: mongo
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10003:27017    
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config3:/data/configdb
    networks:
      - mongoCluster 

```
- 初始化节点信息.讲三个节点组成一个副本集
```shell

# 启动容器后，进入config容器内.运行mongosh命令进入mongo shell 交互.

# 运行 initiate命令，初始化mongo实例
>>> 
rs.initiate(
  {
    _id: "configsrv", ## 副本集和ID
    configsvr: true,
    members: [ 
      { _id : 0, host : "config1" }, # 第一个为主节点
      { _id : 1, host : "config2" }, # 从节点1
      { _id : 2, host : "config3" } # 从节点2
    ]
  }
)

# 初始化后.运行 rs.status 可以看到副本集的状态
>>> rs.status()
{
  set: 'configsrv',
  date: ISODate("2023-05-20T16:41:51.456Z"),
  myState: 1,
  term: Long("1"),
  syncSourceHost: '',
  syncSourceId: -1,
  configsvr: true,
  heartbeatIntervalMillis: Long("2000"),
  majorityVoteCount: 2,
  writeMajorityCount: 2,
  votingMembersCount: 3,
  writableVotingMembersCount: 3,
  ...
  members: [
    {
      _id: 0,
      name: 'config1:27017',
      health: 1,
      state: 1,
      stateStr: 'PRIMARY',
      uptime: 21301,
      optime: { ts: Timestamp({ t: 1684600910, i: 1 }), t: Long("1") },
      optimeDate: ISODate("2023-05-20T16:41:50.000Z"),
      lastAppliedWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      lastDurableWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      syncSourceHost: '',
      syncSourceId: -1,
      infoMessage: '',
      electionTime: Timestamp({ t: 1684579693, i: 1 }),
      electionDate: ISODate("2023-05-20T10:48:13.000Z"),
      configVersion: 1,
      configTerm: 1,
      self: true,
      lastHeartbeatMessage: ''
    },
    {
      _id: 1,
      name: 'config2:27017',
      health: 1,
      state: 2,
      stateStr: 'SECONDARY',
      uptime: 21228,
      optime: { ts: Timestamp({ t: 1684600909, i: 2 }), t: Long("1") },
      optimeDurable: { ts: Timestamp({ t: 1684600909, i: 2 }), t: Long("1") },
      optimeDate: ISODate("2023-05-20T16:41:49.000Z"),
      optimeDurableDate: ISODate("2023-05-20T16:41:49.000Z"),
      lastAppliedWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      lastDurableWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      lastHeartbeat: ISODate("2023-05-20T16:41:50.028Z"),
      lastHeartbeatRecv: ISODate("2023-05-20T16:41:51.035Z"),
      pingMs: Long("0"),
      lastHeartbeatMessage: '',
      syncSourceHost: 'config1:27017',  
      syncSourceId: 0,
      infoMessage: '',
      configVersion: 1,
      configTerm: 1
    },
    {
      _id: 2,
      name: 'config3:27017',
      health: 1,
      state: 2,
      stateStr: 'SECONDARY',
      uptime: 21228,
      optime: { ts: Timestamp({ t: 1684600909, i: 2 }), t: Long("1") },
      optimeDurable: { ts: Timestamp({ t: 1684600909, i: 2 }), t: Long("1") },
      optimeDate: ISODate("2023-05-20T16:41:49.000Z"),
      optimeDurableDate: ISODate("2023-05-20T16:41:49.000Z"),
      lastAppliedWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      lastDurableWallTime: ISODate("2023-05-20T16:41:50.342Z"),
      lastHeartbeat: ISODate("2023-05-20T16:41:50.030Z"),
      lastHeartbeatRecv: ISODate("2023-05-20T16:41:51.035Z"),
      pingMs: Long("0"),
      lastHeartbeatMessage: '',
      syncSourceHost: 'config1:27017',
      syncSourceId: 0,
      infoMessage: '',
      configVersion: 1,
      configTerm: 1
    }
  ],
  ok: 1,
  lastCommittedOpTime: Timestamp({ t: 1684600910, i: 1 }),
  '$clusterTime': {
    clusterTime: Timestamp({ t: 1684600910, i: 1 }),
    signature: {
      hash: Binary(Buffer.from("0000000000000000000000000000000000000000", "hex"), 0),
      keyId: Long("0")
    }
  },
  operationTime: Timestamp({ t: 1684600910, i: 1 })
}


```


### docker-compose 部署mongo分片集群。
由上面的mongodb的分片集群的组成可知,要组成一个集群，还需要增加一个mongos路由服务,多个shards节点服务.固在docker-compose.yaml里面再加上对应的服务.    

```yaml

version: '3.4'
services:
  # 分片
  shard1:
    image: mongo
    # --shardsvr: 将此mongod实例配置为分片集群中的分片。默认端口是27018。 
    # --directoryperdb：每个数据库使用单独的文件夹
    # replSet副本集名称 primary（主节点，提供增删查改服务），slaver（备节点，只提供读）,arbiter（仲裁节点，不存储数据，只负责仲裁
    command:  mongod --shardsvr --replSet shard1 --port 27017 --directoryperdb
    ports:
      - 20001:27017
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/shard1:/data/db
    networks:
      - mongoCluster 


  shard2:
    image: mongo
    command: mongod --shardsvr --replSet shard2 --port 27017 --directoryperdb
    ports:
      - 30001:27017
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/shard2:/data/db
    networks:
      - mongoCluster 


  shard3:
    image: mongo
    command: mongod --shardsvr --replSet shard3 --port 27017 --directoryperdb
    ports:
      - 20003:27017    
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/shard3:/data/db
    networks:
      - mongoCluster 


  # 配置服务器, 用于存储集群的元数据和配置设置 设置 config1/config2/config3为config sever副本集
  config1:
    container_name: config1
    image: mongo
    # --configsvr: 这个参数仅仅是将默认端口由27017改为27019, 如果指定--port可不添加该参数
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10001:27017    
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config1:/data/configdb
    networks:
      - mongoCluster 


  config2:
    container_name: config2
    image: mongo
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10002:27017    
    volumes: 
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config2:/data/configdb
    networks:
      - mongoCluster 
 

  # 声明此mongod实例作为分片集群的配置服务器。默认端口是27019，默认的dbpath目录是/data/configdb，
  # 配置服务器存储集群的元数据和配置设置。从MongoDB 3.4开始，配置服务器必须部署为一个replicate set副本集，
  # 为了防止这个配置服务是单点服务。如果你的集群只有一个配置服务器，一旦这个配置服务器出现故障则集群将不可用
  config3:
    container_name: config3
    image: mongo
    command: mongod --configsvr --directoryperdb --replSet configsrv --port 27017
    ports:
      - 10003:27017    
    volumes:
      - /etc/localtime:/etc/localtime
      # - /data/fates/mongo/config3:/data/configdb
    networks:
      - mongoCluster 

  # 路由
  mongos:
    image: mongo
    # mongo3.6版默认绑定IP为127.0.0.1，此处绑定0.0.0.0是允许其他容器或主机可以访问
    # configdb参数指明config server.
    command: mongos --configdb configsrv/config1:27017,config2:27017,config3:27017 --bind_ip 0.0.0.0 --port 27017
    ports:
      - 27017:27017
    volumes:
      - /etc/localtime:/etc/localtime
    depends_on:
      - config1
      - config2
      - config3
    networks:
      - mongoCluster  


  mongo-express:
    image: mongo-express
    container_name: mongo-express
    ports:
      - 8081:8081
    environment:
      # - ME_CONFIG_MONGODB_ADMINUSERNAME=admin
      # - ME_CONFIG_MONGODB_ADMINPASSWORD=admin
      - ME_CONFIG_MONGODB_SERVER=mongos
    networks:
      - mongoCluster 


networks:
  mongoCluster:
    external: true


```
启动后,我们需要先按照之前的方式启动config server服务.然后需要进入每个shard节点进行节点的初始化.

```shell
## 进入shard 各个容器,初始化 shard 节点
>>> rs.initiate(
  {
    _id: "shard3",
    members: [
      { _id : 0, host : "shard3" } # shard 如果同样采取的 主备模式.可以参考config server的初始化方式
    ]
  }
)



```

最后，我们需要启动一个mongos路由服务.进入该容器,把shard节点加入到集群

```

>>> 
sh.addShard("shard1/shard1:27018")
sh.addShard("shard2/shard2:27018")
sh.addShard("shard3/shard3:27018")



```