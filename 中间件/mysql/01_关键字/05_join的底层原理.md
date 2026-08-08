

join本质上就是嵌套循环 nested-loop

## SNLJ

simple nested-loop join 双重for循环

两个表数据量为100 1000 不走索引 直接join  则snlj 磁盘/内存扫描总次数为10万次 

snjl： for(a:0-100): for(b:0-1000)  则b表被扫描100次 

## BNLJ

Block Nested-Loop Join 使用内存空间换时间

引入join buffer 连接缓冲区进行优化。

a表连接b表 不再是一行一行取a表数据去比较 而是把a表的数据一次性装进join buffer 然后全盘扫描b表 让b表的每一行与buffer里的a表数据做批量对比 减少了内层表b表的磁盘扫描次数

举例：

snjl： for(a:0-100): for(b:0-1000)  则b表被扫描100次 

bnlj： for(b:0-1000):寻找内存

把a放进内存 则b表只扫描一次 做1000次内存比较 

因为磁盘io很慢 把耗费时间的比较放进内存。





## INLJ

Index Nexted-Loop Join 

前提就是 被驱动表 也就是内层循环的表 关联字段 必须有索引

snjl: for(a:0-100): for(b:0-1000) 

inlj:  for(a:0-100): 走索引 索引树高

如果树高为3 则扫描次数就变成100x3。就300次 性能很高。

可以推出 被驱动表放数据量大的表 去走索引 效率高



## 小表驱动大表

left join： 左表是驱动表 

inner join： mysql优化器会自动选择数据量较小的表作为驱动表。