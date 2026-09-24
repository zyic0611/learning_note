快速列表 


## 为什么出现

redis3.2之前 list的底层实现有两种 根据数据量切换

**纯双向链表** linkedlist 

节点分散在内存各处 容易产生内存碎片

 附加空间很高 每个节点都需要维护prev和next两个指针 16字节一共 

**纯压缩列表**ziplist 

一块连续的内存 如果数据量非常大 向os申请一大块连续内存非常困难

中间元素的插入或者修改会引起 连锁更新的问题



## 底层

本质上是一个由ziplist/listpack作为节点的双向链表

架构：

`[ziplist/listpack] <-> [ziplist/listpack] <-> [ziplist/listpack]`



## 解决

### 消灭了巨型连续内存的问题

如果一个ziplist太大了 就不往里添加数据 而是新建一个ziplist 通过链表指针连接 

避免了申请大量连续内存失败

也把连锁更新的范围限制在一个ziplist里



### 降低了指针开销

用quicklist 指针数量只跟内部ziplist节点数量有关 比纯链表大大减少



### 两端操作依然迅速

因为最外层是双向链表 LPUSH RPUSH 只需要找到头尾两个节点 字节放数据就行 时间复杂度仍然是o1





## 升级

redis7.0以后 把节点替换成没有连锁更新缺点的listpack

