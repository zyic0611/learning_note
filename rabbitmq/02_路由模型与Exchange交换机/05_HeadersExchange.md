抛弃了RoutingKey 依靠消息的Header属性进行匹配。

## 匹配规则

使用Headers交换机 绑定队列就不看RoutingKey 而是传入一个包含了 键值对的Hash表 其中有一个特殊的键 **`x-match`**

- `x-match=all`代表全匹配 生产者发来的消息Header里 必须完全包含 队列绑定时 要求的所有K-V键值对 才能路由成功
- `=any` 代表部分匹配 只要休息Header里包含任何一个 匹配的K-V对 路由成功



## 问题

AMQP协议中 一条晓得二进制流主要分为三块

Frame Header帧头 

content Properties属性（包含headers）

Body消息体

如果使用direct/topic/fanout 他们只会解析协议最外层的routingkey字符串 解析很快 然后直接丢给底层的ETS路由表

如果使用headers 路由引擎必须深入解析 AMQP协议中的 Content Properties区域 把headers拆成Erlang的字典结构 再跟每个绑定队列的字典去执行all或者any的对比运算

字典比对的cpu消耗是字符串匹配的几十倍 并发情况下会导致RMQ集群的CPU负载飙升 吞吐量断崖式下跌。

## 架构替代方案

headers主要可以解决 满足多个复杂条件才可以接收消息的场景。

替代方案：

**1.降维打击：**

​	把多维度的Header条件拼接成Topic字符串 设置RoutingKey 用Topic交换机解决，

**2.消费者端解决**：

​	把消息用Fanout or Direct发送 让消费者代码自行判断Header里有没有需要的字段。 宁愿消耗业务服务的CPU 也不要消耗MQ的CPU。 大厂架构的核心思想：**中间件只做纯粹的管道	** 

