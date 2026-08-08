默认交换机就是没有名字的交换机 名字为`""` 也就是空字符串。

## 底层

每创建一个new队列 底层自动将队列绑定到Default Exchange上 并且强制制定Bindingkey为queuename。 队列名。

意味着把消息发送给默认交换机 routingkey只要写队列名 就会精准投递。

所以Erlang底层 默认交换机就是一个 DirectExchange

## 大厂禁止使用

**破坏了解耦精髓** MQ的核心价值在于生产者不知道消息会去哪个队列 如果使用defaultexchange 生产者必须在代码里硬编码消息的routingkey为目标队列的名字

**无法扩展业务** 没办法进行多播 一个消息没办法发送给多个队列 退化成RPC调用 失去了MQ广播和组播的能力