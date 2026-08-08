##  ProcessorSlot

所有的检查站Slot 都需要实现顶层接口 ProcessorSlot。 

该接口核心动作只有两个 entry exit

当一个请求到达某个slot的时候 先执行自己的entry逻辑 执行之后 调用`fireEntry` 也就是结束该次entry 请求下一个 请求才会流转到下一个slot

```java
public interface ProcessorSlot<T> {
    // 请求进入该节点时的逻辑
    void entry(Context context, ResourceWrapper resourceWrapper, T param, int count, boolean prioritized, Object... args) throws Throwable;

    // 请求调用上一个节点时的触发逻辑（也就是放行，把接力棒交给下一个 Slot）
    void fireEntry(Context context, ResourceWrapper resourceWrapper, Object obj, int count, boolean prioritized, Object... args) throws Throwable;

    // 请求退出该节点时的逻辑
    void exit(Context context, ResourceWrapper resourceWrapper, int count, Object... args);

    void fireExit(Context context, ResourceWrapper resourceWrapper, int count, Object... args);
}
```

## Java SPI机制

全称是 Service Provider Interface

类似于SpringBoot的 `spring.factories`自动装配原理  sentinel用的是原生的java规范 自己封装了一个`SpiLoader`

核心工作原理 **约定大于配置**

Sentinel 在初始化责任链时，不会去硬编码 `new FlowSlot()`，而是去读项目依赖。具体步骤如下：

1. 寻找目录:扫描所有jar包下的 `META-INF/services/`目录
2. 读配置文件:寻找一个以接口全限定名命名的文件 `com.alibaba.csp.sentinel.slotchain.ProcessorSlot`
3. 反射实例化: 这个文件里写了一排类的全限定名 都是slot。 sentinel把这些类通过反射加载进内存。
4. 组装排序： 通过类上的@Spi注解中的order属性。 对这些Slot进行升序排序 最后收尾相连 组装成单向链表。

## 使用SPI

使用这个机制 就可以决定slot的排序顺序 以及可以随意插拔slot 自定义slot

总的来说 **是架构设计的杀手锏**

假设在环卫综合调度 SaaS 平台中，抢单接口面临一个特殊的业务需求：**不仅要限制接口的 QPS，还要在最前置校验当前司机的“健康码/疲劳驾驶状态”，如果不合规，连 QPS 都不消耗，直接拒绝。**

用 Sentinel 的 SPI 机制，这事解决起来极其优雅，完全不需要改动原有的业务代码，也不需要改 Sentinel 的源码：

**第一步：写一个自定义 Slot** 写一个 `DriverStatusCheckSlot`，实现 `ProcessorSlot` 接口。在里面加上疲劳驾驶的校验逻辑。通过类上的 `@Spi(order = -9500)` 注解，确保它排在 `StatisticSlot` 等核心组件的前面。

**第二步：配置 SPI 文件** 在你的项目 `resources` 目录下，建一个神奇的路径和文件： `META-INF/services/com.alibaba.csp.sentinel.slotchain.ProcessorSlot`

**第三步：写上你的名字** 在这个文件里，写上你刚刚写的类的全路径： `com.yourcompany.sanitation.slot.DriverStatusCheckSlot`

搞定！下次重启平台，你的这个安全校验站就会被 Sentinel 的 `SpiLoader` 动态抓取，悄无声息地嵌在原本的拦截流水线的最前端。