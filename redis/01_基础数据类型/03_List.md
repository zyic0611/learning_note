底层采用 quicklist  保留了双向链表在两端极速插入or弹出的o1特性 又通过内部紧凑排列大幅降低了内存碎片和指针空间浪费。



## 命令

入队：

`LPUSH key value1 value2` 从左侧头部插入

`RPUSH key value1 value2` 从右侧塞入



出队

`LPOP key` 从左侧弹出并返回

`RPOP key` 从右侧弹出并返回



范围查看 

`LRANGE key start stop`  获取指定范围的元素

lrange key 0 -1 会返回所有元素 危险命令 数据多时会阻塞



## 消息队列

生产者发送消息:

`LPUSH queue_name message_json`

消费者处理消息 

写一个死循环 不断执行`RPOP queue_name` 把任务从右边拿出来处理

先进先出 FIFO队列



## 阻塞读取

消费者有问题 死循环不断执行RPOP 当队列为空的时候 不断返回null 这叫 **CPU空转** 浪费cpu算力 对redis造成大量无效请求。



使用阻塞弹出 Blocking POP

命令 `BRPOP queue_name timeout`

如果timeout设置为0 代表无限期等待。

则如果队列没有数据 则该连接挂起 阻塞在redis端 无限期等待 不消耗任何cpu和网络贷款。

一旦有生产者LPUSH 则redis唤醒挂起的连接。



所以用redis实现低延迟又不对系统造成压力的消息队列 使用LPUSH+BRPOP



## 高并发不推荐用list

### 没有确认机制 ACK

消费者发送brpop redis就从list里弹出消息。

如果消息正在发送到服务端 比如springboot的时候 服务器宕机 

则消息永远丢失了

如果使用rabbitmq 会采用ACK机制。消费者pop拿到消息后 在rabbitmq里先不删除数据 只标记为锁定 只有消费者确定执行完消息任务 显式给rabbitmq发送ack确认 raabitmq才会删除消息。如果消费者挂了 rabbitmq没收到ack 就会把消息重放队列 重新发送给下一个人，



### 缺少死信队列和重试机制

redis list:

如果消费者用BRPOP 拿到了一个格式错误无法处理的消息 如果不做特殊处理 消息就抛出异常 丢失了 如果业务代码写了一个catch并且重新LPUSH机制 又会重新被消费 不断报错 系统陷入死循环

rabbitmq: 有DLX 一个消息重试3-5次报错 mq就会把m送到dlx里 报警让程序员排查 不会阻塞主队列的运转



### 缺少广播模式

redislist:

一个m被BRPOP出来后 只能由一个消费者拥有

rabbitmq:

引入Exchange概念 一个消息给交换机 可以复制并分发给不同的队列 让三个消费者并发消费。 这叫发布订阅模式 (Pub&Sub)





