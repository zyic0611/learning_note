RabbitMq 是基于高级消息队列协议 AMQP  Advanced Message Queuing Protocol。 核心在于灵活的 Routing机制

在AMQP中 Producer不可以直接把Message发送到queue中。 这是和其他消息队列最本质的区别。

## 核心实体组件

- **producer 生产者:**

​	 消息的创建者 负责构造消息内容(Body+Properties) 并给消息贴标签 （Routing key)。然后扔给Broker。

- **Broker 代理节点：**

​	RabbitMQ Server本身。 看作一个大型的邮局。

- **Exchange 交换机 :**

​	是AMQP的灵魂 位于broker内部。 是区别于其他mq的核心设计。

​	 exchange本身不存储消息 只负责路由。 接受生产者的消息 根据路由规则 决定把消息发送到哪个queue or 直接丢弃

- **Queue 队列：**

​	存储消息的实体。 FIFO结构。 可以配置为内存存储 or 落盘持久化。

​	消息在这里排队 等待被取走。

- **Consumer 消费者：**

​	是接收并处理消息的应用。订阅具体的queue  queue中有消息的时候 broker会把message 推给消费者。或者消费者主动拉取。 （rabbitmq推荐push模式。



## 连接纽带

Routing Key 路由键

​	生产者发消息时 附带的属性 绑定在消息上。 类似于信件的收货地址



Binding Key 绑定键

​	队列和交换机建立的绑定关系 制定的规则。 也就是队列拿着这个绑定规则 去交换机上匹配对应的路由。



流转逻辑：

​	实际上是broker里的exchange做匹配的事。

​	 当消息到达 Exchange 时，Exchange 会拿着消息的 **Routing Key**，去和自己身上绑定的所有队列的 **Binding Key** 进行匹配。匹配上了，消息就复制一份进入该 Queue；匹配不上，默认丢弃（除非配置了死信队列或备份交换机）。

​	消息是被复制给队列 所以一条消息可以发给多个队列。



## 为什么要设计Exchange

本质上是实现 生产者与路由逻辑的绝对解耦。 生产者只管生产消息 无脑丢给交换机。 

