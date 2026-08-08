## 读写双指针

内部维护了 两个独立指针。

- 读指针 `readerIndex`：表示下一次从哪里开始读
- 写指针`writerIndex`：表示下一次从哪里开始写

两个指针把 底层的字节数组 划分为三个区域。

1 废弃字节区`[0,readerIndex]`： 已经读过的数据 属于可以覆盖或者回收的安全区域。

2 可读字节区 `[readerIndex,writerInde)]` 存放有用 还没被消费过的数据

3 可写字节区 `[writerIndex,capacity)` 空的 可以寄继续写数据

## 内存位置

Direct 直接内存 vs Heap 堆内存

### HeapByteBuf

堆内存缓冲区

- 优点：创建和销毁很快 完全由JVM的GC管理 不容易造成严重的内存泄漏
- 缺点：在进行Socket网络读写的时候 OS无法直接访问JVM堆内的内存。   java必须在底层把heap的data copy到 os kernel的一块非heap 内存中 再发送给网卡 **多了一次内存拷贝 耗费cpu**

### DirectByteBuf

直接内存缓冲区

- 原理 ： 直接调用OS的API 类似于C语言的malloc 在JVM堆外分配内存
- 优点： **是实现 zero-copy的基础。** 操作系统的网卡驱动 可以直接读写这块内存 省去了从JVM往操作系统拷贝的过程 IO性能飞升。
- 缺点： 分配和释放内存的代价昂贵 涉及到系统调用 而且由于这块内存不在堆内 普通的GC无法管辖 如果不处理好 很容易造成 堆外内存溢出 OOM

### 微服务实战经验：

只要涉及到底层网络通信 比如 Nacos的长连接读写 Sentinel的规则推送 Dubbo Rpc Netty都是强制推荐使用 DirectByteBuf

## 分配策略

direct分配的很慢 又很贵 就用池化技术解决。 和线程池 数据库连接池思想一样。

**Unpooled：** 非池化 每次需要缓冲区的时候 就向Os申请一块全新的内存 用完就丢 在极高并发下 频繁的申请Direct会让CPU爆炸。

**Pooled：** 池化 netty启动的时候 直接向OS批发 一大块连续的内存 称为Arena 类属于内存大盘 有新的请求进来需要分配100字节 Netty字节通过自己内部的复杂算法 从大盘里借用一部分出来 用完再归还

