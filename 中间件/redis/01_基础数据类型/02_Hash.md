Hash可以理解为 java中 存在内存里的 `Map<String,Map<String,String>>`

所以本质上也是 k-v结构 key是String  Value是一个 k-v都是 String的哈希表。



## 底层存储

可以做到既省内存 查询极快。

数据量小的时候 ：

使用Listpack /Ziplist 。 hash里字段很少 并且里面的值很短的时候。用这两种紧凑的连续内存结构。

优点：

节约内存

缺点：

顺序遍历 on 复杂度。 但是因为数据量很小 cpu缓存对顺序读取很有利 所以反而比hash更快。

数据量大的时候

转换成真正的hashtable



## 命令与避坑

`HSET key field value`、`HGET key field` 设置和获取单个字段

`HMSET 、HMGET` 批量操作  （新版本中HSET已经支持多个field-value传入 HMSET已经被视为废弃）

`HINCRBY key field increment` 对Hash中某个具体的字段进行原子加减

`HEGTALL KEY`危险命令：

问题： 获取HASH中所有字段和值 如果hash里存了很多属性 会直接把redis单线程卡死 引发巨大的网络带宽消耗

解决： `HSCAN`命令 像游标卡尺一样 每次只拉取一小批数据 分多次拉取



## 业务1:对象存储

经常需要缓存 实体对象

### 用String 存Json

缺点 

如果对象每10s就需要更新某一个字段 

必须把整个json字符串都get出来 然后在业务代码里反序列化 修改某一个属性 再序列化为json 再set回去 。

非常消耗CPU和网络IO 在高并发情况下会引发严重的并发覆盖问题 容易被旧的json覆盖



### Hash存储

实现局部更新很简单 只需要一句

`HSET key field  newvalue`



##  业务2 归类存放

如果有一百万个 状态数据 

如果都用String存储 redis就会在最外层的全局字典中产生100万个key

 redis为了维护每一个底层key 都需要消耗额外的元数据内存 比如过期时间 lru时间 导致严重的内存浪费



用Hash存储 只需要一个key。 特别在数据量在hash的listpack编码范围 内存下降10倍多 



## hash局限性

很多时候都会用string去存json 

本质原因在于 redis的过期机制(TTL)是作用在key上的 并不是作用到filed上。

Hash的问题：

如果hash存50个属性 想设置某一个属性在1h后过期 做不到。只能设置整个hash key过期。 

导致如果想让hash里的某个数据过期 要么通过代码在应用层处理 要么把数据拆分成独立的key。

使用string：

每一个属性都是单独的string key 可以为每一个key设置不同的过期时间。


## 渐进式rehash

只要用到hash表  就必须面对扩容问题。 由于redis是单线程的  hash的扩容是一次性把所有数据重新映射  如果hash表数据很多 会导致redis直接阻塞。

所以内部维护两个hash表 h0 h1
扩容的时候 不是一次性搬运。每对这个hash表进行操作的时候 就搬运一部分数据到新hash表。 并且扩容之后的添加操作 都是添加到新hash表。