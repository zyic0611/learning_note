为每个线程分发了context的信息。 当携带者contxt的请求 顺着责任链来到 `NodeSelectorSlot`检察站的时候 sentinel会在内存里画出 **调用关系地图**

为什么需要画地图 ：因为可能不同的用户从不同的入口 比如app和后台 都调用同一个核心资源 ： xx接口。 

**所以资源其实就是接口。**

而后台肯定希望 精细的控制某个端的资源访问 放行某个端口。 链路化的精细限流 必须依赖调用树。

## Node家族

当请求经过 `NodeSelectorSlot时` sentinel会把调用路径 抽象成 三种节点的层级关系：

1.全局唯一上帝节点 machine-root

​	是所有流量的汇总节点  单机维度下的总QPS 总CPU负载 都是它来统领

2.标识入口的父节点 EntranceNode

​	每一个不同的Context名称 对应一个EntranceNode 。标识着入口名，也就是线程请求。 挂在machine-root下

3.真正干活的子节点 DefaultNode

​	挂在入口节点下的叶子结点 代表 在特定入口下 访问的具体资源 也就是具体接口

## NodeSelector核心源码

每次请求进来 都需要在树上找节点 甚至动态创建节点 高并发下 不会拖垮性能吗？

```java
// 核心缓存 Map，注意 volatile 关键字！
private volatile Map<String, DefaultNode> map = new HashMap<String, DefaultNode>(10);
```

请求到达时

实际执行的代码是：

```java
// 请求到来时执行的方法
public void entry(Context context, ...) {
    // 【第一步：无锁化查询】
    DefaultNode node = map.get(context.getName()); 
    
    if (node == null) {
        // 【第二步：加锁】
        synchronized (this) {
            // 【第三步：加锁后，再查一次！】
            node = map.get(context.getName()); 
            
            if (node == null) {
                // 真正创建节点并加入 Map 的逻辑
                node = new DefaultNode(...);
                // ... 省略将新节点放入新 Map 并替换老 Map 的过程 ...
            }
        }
    }
    // 放行，进入下一个 Slot
    fireEntry(context, ...);
```



1.继续寻址：

​	拿着当前的context名字 也就是对应entrancenode 查询map  如果命中 说明该入口之前有人访问 直接把查到的defaultnode塞进context里 然后放行。 不操作任何复杂的树形遍历。

2.无锁化双重检查 DCL：

​	没查到 就用sunchronized锁住当前对象 也就是锁住当前入口。再查一次map 防止并发冲突。然后新建节点 挂在树上 最后放进map。  

**无锁化：**

​	指的是不对entry这个方法上锁。一般害怕并发冲突 直接对方法上Synchronized锁 或者用ConcurrentHashMap 不用hashmap 。但是这样会导致 每一次请求进来 就算节点已经建立好了 也要排队等锁 才能确定有没有节点 或者经历复杂的并发控制机制 再高并发情况下 性能灾难。

**性能压榨：**

​	 由于系统的接口数量和入口数量 在运行期 基本是固定的(99.99999%情况下)。 也就是意味着1000w个请求了 只有开始的几个请求在第一步寻址 也就是查询hashmap的时候会查到null,剩下的所有请求走第一步都会拿到node。

**再次查询**

​	也就是高并发编程中常见的 **竞态条件** 场景：

也就是 三个线程a b c同时执行了第一步无锁化查询 都是null。 由于锁只有一把 只有一个线程可以获取。 假如a获取了锁 创建了defaultenode 放进map里。此时b获取锁 没有执行再次查询 则不知道a干了活 就自己在创建一个defaultenode 塞进map。 **导致A记录的并发统计数据清0 整个调用树再并发极高的情况下 不断被重置 破坏 导致限流功能失效**

**双重检查锁**

​	外层检查 挡住99.999的并发 实现无锁极速获取

​	内层检查 挡住0.0001的瞬间 因为并发挤过外层检查的少数 保证单例的绝对安全