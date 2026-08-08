使用spi机制和 processorSlot建立好 各个slot组成的安检流水线后 一个请求(流量)就可以跑在这个流水线上。 但是他需要如何携带自己的信息呢 比如：某个slot怎么知道是哪个应用调用的接口  某个Slot又应该限制哪个对象，则引出核心对象 Context 上下文

## ThreadLocal

java高并发的web编程中 比如Tomcat。 每一个并发的请求都是一个独立的线程Thread处理的。

该请求会穿过 层层代码： Controller Service Mapper  不需要再每个方法体的参数都加上context。 直接把context放在threadLocal里。

也就是每个线程的私有数据。

**优点：** 完美隔离 a线程放进去的 context b线程拿不到。 保证了高并发场景下 无数个请求的数据不会串位。

**缺点：**内存泄漏。 使用的是Tomcat这种线程池  线程用完会回收到池子里 不会销毁。 请求结束的时候 如果不手动丢弃context 下一个请求拿到该线程 就会带着上一个context 导致数据错乱 甚至OOM。

## 创建context 类似于挂号

真正创建 `Context` 的并不是 `SphU.entry()`，而是 `ContextUtil.enter(contextName, origin)`。

- `contextName`：也就是入口名称（比如你从“APP端”进来的，还是“小程序端”进来的）。
- `origin`：调用来源（在使用微服务时，这通常是上游服务的名称）。

**思考：但在我们平时写 Spring Boot 代码，用 `@SentinelResource` 注解时，从来没写过 `ContextUtil.enter()`，为什么没报错？** 这就是 Sentinel 的“兜底保姆机制”。如果你不显式调用，Sentinel 源码在执行 `SphU.entry()` 时，会悄悄去查一下当前线程的口袋。如果发现口袋是空的，它会主动给你建一个名字叫 `sentinel_default_context` 的病历本，来源为空。

## 进入责任链

sentinel的固定模版是：

```java
Entry entry = null;
try {
    entry = SphU.entry("resourceName");
    // 业务逻辑
} finally {
    if (entry != null) {
        entry.exit(); // <--- 极其致命的一句
    }
}
```

使用资源名 调用`SphU.entry(资源名)` 创建entry 然后顺着责任链 往下传递。 责任链上每一个slot 都是往context里读或者写东西。

## 释放资源

模版里的finally必须执行 entry.exit() 退出资源。

当 `entry.exit()` 被调用时，Sentinel 不仅仅是记录一个请求结束的时间来计算 RT（响应时间），更关键的是，它会顺藤摸瓜找到 `Context`，并在合适的时机调用 `ContextUtil.exit()`。 这个方法里面最核心的一句代码就是： 把context从ThreadLocal里删除掉。

解决了Tomcat的缺点，防止Tomcat线程池复用导致的内存泄漏和数据污染