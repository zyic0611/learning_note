Double-Check Locking 双重检查锁定 在多线程环境下 实现延迟初始化的优化手段。 一般用于编写 单例模式 Singleton。

核心目的： 保证线程安全的情况下尽可能减少加锁带来的性能开销。

## 代码

```java
public class Singleton {
    // 关键点 1：必须使用 volatile 修饰
    private static volatile Singleton instance;

    private Singleton() {}

    public static Singleton getInstance() {
        // 第一次检查：如果不为空，直接返回，避免进入同步代码块，极大地提升高并发性能
        if (instance == null) { 
            // 关键点 2：只在第一次初始化时加锁
            synchronized (Singleton.class) { 
                // 第二次检查：防止多个线程同时通过了第一次检查，排队进入锁后重复创建对象
                if (instance == null) { 
                    instance = new Singleton(); 
                }
            }
        }
        return instance;
    }
}
```

第一次检查 是无锁检查 如果已经初始化过 就直接返回 

第二次检查 是有锁检查 拦截在极短时间内 并发通过无锁检查 确保只有一个线程可以进行new操作。

## 为什么要加volatile

加synchronized重锁 只能保证临界区内的代码是单线程执行的 不能阻止临界区内的代码指令重排。



根源在于 `instance=new Singleton()` 并非原子操作 会被分成3部分

1 分配内存空间：为该对象在堆上分配一块空白内存

2 初始化对象： 执行singleton的构造方法 填充每个属性值

3 将内存地址赋值给引用：让instance变量指向这块内存地址



### 指令重排 会导致 1-3-2 乱序

多线程情况下：

1：线程a进入同步快 执行1 分配内存 3赋值引用 但是还没执行2 对象没被初始化 但是此时instance已经不为空

2：线程b刚好调用 getInstance() 来到了第一次检查 检查通过 因为instance已经不为空

3：此时初始化还没执行 线程b拿到的是一个内容为空白/默认零值的半成品对象 此时如果调用对象的方法或者读取属性 就会抛出错误



### volatile就可以防止 2 3重排  :

- 在 `instance = new Singleton();` 的写操作之前，强制插入一个 **StoreStore 屏障**。

- 这个屏障的物理意义是：**它保证了步骤 2（构造函数中的所有普通写操作，即初始化属性）必须在步骤 3（将地址赋值给 volatile 引用）之前全部完成并刷新到主内存。**

