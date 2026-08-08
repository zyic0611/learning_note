### 01 RabbitMQ 核心概念与 AMQP 协议

这是理解 RabbitMQ 为什么如此设计的基石，摆脱对 API 的死记硬背。

- **01_AMQP 协议模型** (Producer、Broker、Exchange、Queue、Consumer 的宏观流转)
    
- **02_核心组件解析** (Connection 与 Channel 的区别，为什么推荐多路复用 Channel 而不是新建 Connection)
    
- **03_Virtual Host 隔离机制** (多租户设计思想在业务隔离中的应用)
    
- **04_消息结构剖析** (Message Properties 与 Body，如何利用 Header 传递隐式参数)
    

### 02 路由模型与 Exchange 交换机底层

深入理解解耦的精髓，这是 RabbitMQ 对比其他 MQ 最灵活的地方。

- **01_Direct Exchange** (精确匹配与单播路由)
    
- **02_Fanout Exchange** (广播模型，性能最高的交换机，为什么它不需要绑定 RoutingKey)
    
- **03_Topic Exchange** (通配符匹配与组播，`*` 与 `#` 的性能差异与实现机制)
    
- **04_Headers/Default Exchange** (隐式路由与特殊场景应用)
    
- **05_Alternate Exchange 备份交换机** (消息无法路由时的兜底策略)
    

### 03 核心壁垒：消息 100% 可靠性投递

这是面试必考，也是业务开发（如高并发抢单、核心调度）中最痛的踩坑点。必须形成完整的闭环思维。

- **01_生产端防丢失** (Publisher Confirm 异步确认机制、Return Callback 路由失败回调)
    
- **02_Broker 端防丢失** (Exchange/Queue/Message 的全链路持久化机制及磁盘同步时机)
    
- **03_消费端防丢失** (手动 ACK 机制、`basic.reject`/`basic.nack` 的重回队列风险与死循环处理)
    
- **04_可靠性最终一致性方案** (本地消息表、定时任务轮询补偿、结合 MySQL 事务的落地)
    

### 04 进阶特性：延迟、死信与流量削峰

这部分是中间件服务于业务架构的核心利器。

- **01_TTL（Time To Live）** (消息过期与队列过期的区别)
    
- **02_DLX 死信队列** (死信产生的四大条件：被拒、过期、超长；DLX 的路由绑定设计)
    
- **03_延迟队列架构** (TTL + DLX 的原生实现局限性，对比 `rabbitmq-delayed-message-exchange` 插件的优缺点)
    
- **04_流量削峰实战** (高并发下利用 MQ 保护底层 MySQL 数据库的架构设计)
    

### 05 消费语义：幂等性、顺序性与积压处理

微服务架构下的高阶难题。

- **01_消息幂等性保障** (如何防范重复消费？结合 Redis SETNX 或 MySQL 唯一索引的防重方案)
    
- **02_局部顺序消息** (RabbitMQ 如何保证单队列的 FIFO？多消费者打乱顺序后的业务层重组策略)
    
- **03_海量消息积压** (突发十万级积压的应急处理：扩容 Consumer、临时队列转储、极限参数调优)
    

### 06 高可用架构与集群原理 (Erlang 底层)

跳出业务开发，站在系统运维和架构师的视角看 MQ。

- **01_Erlang 语言特性简述** (为什么 RabbitMQ 选 Erlang？Actor 并发模型与高并发网络处理的优势)
    
- **02_普通集群模式** (元数据同步原理，为什么 Queue 数据不默认全量复制)
    
- **03_镜像集群模式 Mirror Queue** (早期的高可用方案、主从同步机制、GM 组播协议)
    
- **04_Quorum Queues 仲裁队列** (RabbitMQ 3.8+ 引入，基于 Raft 协议的现代高可用队列，对比镜像队列的优势)
    
- **05_网络分区与脑裂** (PAUSE_MINORITY 策略与恢复机制)
    

### 07 客户端实践 (结合 Spring Boot 3)

将理论落地到你熟悉的工程环境中。

- **01_Spring AMQP 源码浅析** (`MessageListenerContainer` 的运转机制、线程池调度)
    
- **02_Prefetch Count 调优** (QoS 机制，为什么默认值往往导致性能瓶颈？如何根据业务耗时设置合理拉取量)
    
- **03_并发消费者配置** (`concurrent-consumers` 与 `max-concurrent-consumers` 的弹性伸缩)
    
- **04_序列化选型** (默认 JDK 序列化的坑，Jackson JSON 序列化配置与安全白名单)
    

### 08 宏观视野：MQ 选型与架构比对

既然目标是建立宏观架构视野，这一步不可或缺。

- **01_RabbitMQ vs Kafka** (推与拉的模型差异、解耦与吞吐量的博弈、日志流与消息队列的区别)
    
- **02_RabbitMQ vs RocketMQ** (阿里系金融级 MQ 的事务消息机制，RabbitMQ 为什么很难做原生的两阶段提交事务消息)
    
- **03_场景驱动选型** (什么时候用 Redis 的 Stream/List？什么时候必须上 RabbitMQ？)