zset 既具备 set无序且唯一 又给每一个元素附加了一个double类型的分数 依靠score进行元素排序 从小到大

## 底层

跳表+Hash字典dict

Dict：

负责维护 元素到分数的映射关系 查询ZSCORE 某个元素的分数的时候 通过dict查询 O1

SkipList：

维护分数的排序和范围查找

结论：

用空间换时间 把查找元素分数o1和范围排序ologn结合



## 命令

`ZADD key score member` 新增或者更新分数

`ZINCRBY key increment member` 给某个元素加份： 比如每点击一次文章1 热度+1

`ZREVRANGE key start stop [withscores]` 按排名从大到小获取 比如获取前十名

`ZRANK key member` 获取自己的真实排名



## 延时任务 

比如要实现用户下单30min后 不支付自动取消

1.把订单id作为member 执行时间戳作为score

时间戳就是当前时间+30分钟后的时间

2.不断执行 zrangebyscore delay_queue 0 当前时间 limit 0 1 

意思就是不断取出在延迟队列里 时间戳在当前时间值钱的订单

3.只要查出来 就说明订单到期 拿出来处理 删除zset里 `ZREM`

这样就用zset实现一个分布式延时系统 不用数据库疯狂扫表



## 双重排序

zset比较两个节点大小 默认用score 从小到大排序 如果分数一样 比较member 成员字符串的字典序 本质上比较ascii码

### 时间排序

真实情况 比如分数排名 同分数应该按照先到这个排名的人 在前面。

刚好score本质是double 可以把时间戳放进score。

socre既记录分数 也记录时间戳

socre=真实分数+(最大时间戳-当前时间戳)的转换值 一个小书 把时间放在小数目

最大时间戳是未来的一个很大值

这样实现了 同分数 时间戳越小 排名越高

