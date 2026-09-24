首先对于redis来说 所有的数据类型都是k-v结构。 String字符串的意思是 value可以是字符串、数字（整数）、二进制数据(突破，序列化后的对象)



底层采用 Redis自己构造的SDS数据结构 没采用c语言自带的字符串。



## 高频指令

`Set key value` 、`Get key `  基础的存取

`MSET k1 v1 k2 v2`、`MGET k1 k2`批量存取 

细节： 公司开发喜欢用MGET，因为可以减少网络IO(RTt 往返时间) 但是如果一次MGE 几万个KEY 会阻塞redis单线程。一般建议一次拉一两百个 分批进行

rtt： round-trip time 往返时间

`SETEX key seconds value` 设置键值的同时设置过期时间。是一个原子操作。 setnx理解为setexpire. 不要使用SET 再使用EXPIRE 这两个操作本身是原子操作 但是整体并不是原子操作 操作中间服务器宕机可能导致死key。

`SETNX key value` (set if not exist) key不存在才设置成功。 是早期实现分布式锁的基石命令。



## 原子计数

`INCR key` 、`DECR key` 将key中存储的数字值 +1 -1 必须是数字

`INCRBY key increment` 、`DECRBY key decrement`  增减制定步长



### 高并发的重要性

redis执行指令式单线程的 意味着incr操作天然原子性。 就算有10000个并发请求对同一个key做incr 结果也是准备的加10000. 不会出现多线程情况下的 脏读 丢失更新等线程安全问题。












