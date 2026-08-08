DLX其实就是普通的交换机

## 消息变成DM的三大条件

### 消息被拒绝

消费者处理消息发生业务异常

底层 消费者调用了 `basic.reject` or `basic.nack`拒绝了消息 并且明确设置了 `requeue=false` 不可重新入队

结果：消息如果**不可以被处理** 也不能被**返回原队列** 就会被路由到DLX

### 消息过期

TTL Expired

消息的TTL耗尽 就会成为死信 进入DLX

### 队列超长

声明队列的时候 要设置最大消息数or最大字节数。

满了之后 RMQ默认会把 **队列头部最早的消息** 变成死信放入DLX

## 路由绑定

`x-dead-letter-exchange`：指定这个队列的死信该发给哪个交换机（即 DLX 的名字）。

`x-dead-letter-routing-key`：指定死信发往 DLX 时，携带什么 Routing Key。

## routing key 替换机制

如果在配置业务队列时，**没有**显式指定 `x-dead-letter-routing-key`，死信在进入 DLX 时，会**保留原有的 Routing Key**（也就是 `task.normal`）。这在实际开发中非常有用：你可以用一个统一的 DLX 来接收成百上千个业务队列的死信，然后根据它们原本的 Routing Key 分发到不同的报警队列中去。