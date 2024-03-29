### rabbitMq的集群模式主要有3种模式

- 主备模式      
区别于数据库的主从节点,从节点相当于主节点的备份副本，但是要注意，从节点只会保存一些除了消息之外的一些元数据，所有从节点收到的请求，真实转向的都是主节点，一般在并发和数据不是特别多的情况下使用，当主节点挂掉会从备份的节点中选择一个节点出来作为主节点对外提供服务。所有的读写操作都在主节点上面。

```mermaid
graph TB

    A(主节点1) ----> F[消费者1]
    A(主节点1) ----> B[从节点2] ---> M[消费者2]
    A(主节点1) ----> C[从节点3] ---> N[消费者3]

```

- 镜像队列模式


#### 基于docker-compose的rabbitMQ集群部署
- 先运行3个rabbitMQ docker 容器

``` yaml
version: '3.8'
services:
  rabbitmq1:
    image: rabbitmq:management
    hostname: rabbitmq1  ## 
    container_name: rabbitmq1
    ports:
      - "5672:5672"
      - "15672:15672"
    # volumes:
    #   - /opt/docker_volume/rabbitmq/rabbitmq1/data:/var/lib/rabbitmq
    environment:
      - RABBITMQ_DEFAULT_USER=root
      - RABBITMQ_DEFAULT_PASS=root
      - RABBITMQ_ERLANG_COOKIE=123
      - RABBITMQ_NODENAME=r1
    networks:
      - rabbitmq

  rabbitmq2:
    image: rabbitmq:management
    hostname: rabbitmq2
    container_name: rabbitmq2
    ports:
      - "5672:5672"
    # volumes:
    #   - /opt/docker_volume/rabbitmq/rabbitmq2/data:/var/lib/rabbitmq
    environment:
      - RABBITMQ_ERLANG_COOKIE=123
      - RABBITMQ_NODENAME=rabbitmq2
      - RABBITMQ_CLUSTERED=true
      - RABBITMQ_CLUSTER_WITH=r1@rabbitmq1
      - RABBITMQ_RAM_NODE=true
    networks:
      - rabbitmq
    depends_on:
      - rabbitmq1

  rabbitmq3:
    image: rabbitmq:management
    container_name: rabbitmq3
    hostname: rabbitmq3
    ports:
      - "5672:5672"
    # volumes:
    #   - /opt/docker_volume/rabbitmq/rabbitmq3/data:/var/lib/rabbitmq
    environment:
      - RABBITMQ_ERLANG_COOKIE=123
      - RABBITMQ_NODENAME=rabbitmq3
      - RABBITMQ_CLUSTERED=true
      - RABBITMQ_CLUSTER_WITH=r1@rabbitmq1
      - RABBITMQ_RAM_NODE=true
    networks:
      - rabbitmq
    depends_on:
      - rabbitmq1  

networks:
  rabbitmq:
    driver: bridge



```

- 进入rabbitmq1/rabbitmq2容器,运行:`rabbitmqctl join_cluster {{RABBITMQ_NODENAME}}@{{HOSTNAME}}`命令,将该节点加入集群   
比如对于rabbitmq2/3，运行 `rabbitmqctl join_cluster r1@rabbitmq1`

