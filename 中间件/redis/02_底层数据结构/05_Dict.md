## 结构

三层结构模型 

1.dictEntry 节点  

真正存储数据 包括key value 

2.dictht 哈希表 

包括一个dicEntry数组 哈希表大小size 掩码sizemask =size-1 和当前节点数used

3.dict 最高层封装

​	

在 **Redis 7.0** 之后的源码中，为了进一步节省内存并提高缓存命中率，把 `dictht` 这个中间层结构去掉了，直接将两个哈希表的数组等信息拍平放到了 `dict` 结构体里。但核心的 `双表机制 (ht[0], ht[1])` 思想完全没变。



## 哈希算法与冲突解决

### 哈希函数

redis4.0前用的是MurmurHash2 。

4.0之后换成了SipHash

原因：

MurmurHash虽然很快 但是容易遭受HashDos攻击： 可以伪造大量哈希值相同的key塞进redis 导致哈希表退化成链表 单线程的Redis会直接被卡死 

SipHash牺牲了少量的性能 换取了极强的抗哈希碰撞能力

### 索引计算

索引计算不用% 而是用&

因为位运算在cpu级别 比除法指令快。

所以哈希表的size只能是2的n次方

只有size=2^n hash%size==hash&(size-1)



### 冲突解决

redis采用拉链法 key计算出来的index相同 形成链表。

采用头插法 因为不需要遍历链表 时间为o1





## 渐进式rehash

把扩容的压力分摊到每一次日常操作 全部复制的话 redis单线程会被严重阻塞



### 扩容与缩容

缩容： 负载因子 <0.1

扩容：一般情况 >=1 

如果在执行BGSAVE / BGREWRITEAOF 阈值变成 >=5

原因： 重点

BGSAVE 是靠fork() 子进程来持久化RDB文件 linux的fork（）依赖COW （copy on write 写时复制）机制 如果此时发生大规模rehash 会导致大量的内存数据被修改 出发os的物理内存页复制 导致redis内存占用暴增。为了减少内存分页的复制 redis在后台持久化的时候避免rehash

### 渐进式rehash

1.分配内存

 根据扩容or缩容需求 为`ht[1]`分配对应大小的哈希表空间 

2.开启rehash模式 

把dict结构体中的rehashidex从-1改成0 代表渐进式rehash开始

3.分摊迁移 crud

在rehash期间 每一次对dict执行crud时 顺便迁移ht`[0]`的rehashidex索引位置的整个链表迁移到`ht[1]` 然后rehashidex++

4.定时任务兜底 

如果服务器很闲 没有crud操作 redis后台定时任务批量进行rehash迁移 防止扩容长期停滞

5.完成并释放

当 `ht[0]` 的所有节点都迁移完毕后，释放 `ht[0]` 的内存。将 `ht[1]` 的指针赋值给 `ht[0]`，并把 `rehashidx` 重置为 -1。

### rehash期间的读写逻辑

新增： 直接加到`ht[1]`里

查 删 改：先去`ht[0]` 没有就去`ht[1]`



如果 渐进式rehash期间 客户端想要获取所有key等全量遍历命令 redis会同时遍历`ht[0]`和`ht[1]`两个哈希表 保证数据不遗漏。

总结：

rehash期间的所有读操作 均两表一起看