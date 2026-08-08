核心思想： 写操作的时候 复制整个数组 在新的数组上写入或者删除 然后覆盖旧数据 读操作的时候不加锁 直接读旧数据的 一种线程安全的List。

## 数据结构

底层就是一个字段

```java
private transient volatile Object[] array
```

关键在于volatile数组引用 保证可见性 写完立刻队其他线程可见。



## COW写时复制

写时复制 采用的是加ReentrantLock 加锁后复制数据 然后修改新的数组 最后替换引用 然后解锁。

## 读快照

读的时候 不加锁 直接读取 但是读的是旧数组 可能在此时 也有新的数据往里面写入  所以线程安全的本质不是靠CAS 也不是靠加锁 是用版本替换规避并发冲突 。所以是弱一致性集合

## 为什么不用CAS

CAS不适合多个位置修改 当写入多个数据的时候 就不太合适

## 适用

CHM适用于高并发 而CopyOnwriteArrayList就适用于 读多写少 读远大于写 不要求强一致性。

比如 白名单 配置 黑名单

## 不会failfast

failfast发生在ArrayList HashMap LinkedList 并发修改的时候 由于modCount字段校验时 不等于期望的值 就会报fail-fast错误 。

他并不是线程安全机制 只是错误检测机制 只是为了尽快报错 

CopyOnwriteArrayList 直接复制整个数组 引用替换 不会发生该错误



## 总结

CopyOnWriteArrayList 通过写时复制实现线程安全：写操作通过加锁复制整个底层数组并替换引用，读操作无锁直接访问 volatile 数组，因此读性能极高，但写开销较大，只适用于读多写少的并发场景，并提供弱一致性的迭代器避免 fail-fast。