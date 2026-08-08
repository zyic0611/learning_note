## Mark Word

锁的物理载体。 

HotSprot JVM中 java对象在内存中 分为三块区域: 对象头 实例数据 对其填充。

对象头中的 Mark Word 标记字 是实现锁状态的核心。

占用8字节 64bit. 

## ObjectMonitor 管程

锁升级为重量级锁时 MarkWord会指向底层一个c++对象 管程

核心属性决定了线程的阻塞与唤醒机制。

- _owner：线程的持有者
- _EntryList：阻塞队列 存储等待获取锁的对象
- _WaitSet：等待队列 存储调用了wait方法 让出锁的线程 当被notify唤醒后 线程会从waitset转移到entrylist参与锁竞争

## 可见性

JMM不仅保证了原子性 遵循JMM 保证了可见性

获取锁：JMM 强制要求线程清空本地工作内存  必须从主内存 (Main Memory) 中重新读取共享变量的最新值。

释放锁：JMM 强制要求线程在释放锁之前，必须将工作内存中修改过的共享变量立即刷新回主内存。 底层实现依赖于汇编层面的**内存屏障** 防止了指令重排序导致的数据不一致。



## 死锁问题

### 无条件的阻塞挂起

当线程执行到synchronized代码块 发现锁对象的_owner字段指向其他线程的时候 JVM就直接把当前线程封装为`ObjectWaiter` 字节丢入EntryList队列 然后操作系统把线程挂起 状态为Blocked。 

线程为blocked 不会主动释放当前已经持有的其他monitor 这种持有旧锁 拿不到新锁 容易导致死锁。

ReentrantLock用非阻塞尝试tryLock()实现



### 超时退让

没有超时没有获取新资源 释放旧资源的能力 只能无限等待

ReentrantLock用超时等待tryLock(time)实现 立刻尝试获取锁 获取不到 不会进入同步队列阻塞 立刻返回false。

### 阻塞态不可中断

在等待队列EntryList中 线程不响应操作系统的中断信号

ReentrantLock用acquireInterruptibly实现