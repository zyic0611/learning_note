

## equals hashCode

euqals原生就是比较内存地址 但是业务中两个对象id相同 就认为相同 哪怕new出来两个不同的对象 地址不同 所以需要重写equals【String类就这样

hashcode是一个native方法【C底层方法 他会根据内存地址计算出一个int整数 叫做哈希码 一般是用来配合哈希表的。

重写了equals就必须重写hashcode 不然两个相同的对象哈希码不通过 会被放在两个桶里。所以相同的对象必须有相同的哈希码。

## juc的方法

wait notify notifyall 这些多线程的方法 为什么定义在Object类里 不定义在Thread类里。

因为java提供的锁是对象级的 不是线程级的 。任何对象都可以作为一把锁。既然锁是加载对象上的 ，那么等待和唤醒这些操作 应该由对象控制。



## clone finalize

### clone

object默认浅拷贝 也就是复制原对象里的基本类型，如果有引用，则复制引用地址。也就是新旧对象共享一个对象，所以这个是浅拷贝。

要实现生拷贝 必须重写clone方法 或者序列化。 

调用clone方法的类必须实现 Cloneable接口 叫做标记接口 里面没有方法 给jvm看的通行证

### finalize

与GC绑定的方法 当GC准备回收一个对象的时候 会调用他的finalize

问题：

方法不可靠 执行时间无法保证 可能会让对象逃脱GC java9后被废弃

开发中不用它释放资源 用try-with-resource

## getClass toString

**1. `getClass()`** 搭配反射

- **作用：** 返回这个对象的运行时类（`Class` 对象）。它是 Java **反射机制**的入口。JVM 把类加载到方法区后，就会在堆里生成一个对应的 `Class` 对象，你可以通过它获取类的所有方法、属性、注解等。

**2. `toString()`** 一般被重写

- **默认实现：** `getClass().getName() + "@" + Integer.toHexString(hashCode())`。打印出来就是类似 `User@1b6d3586` 这样的东西。
- **实际应用：** 平时开发一定要重写它（通常用 Lombok 的 `@ToString` 注解），让它打印出具体的属性值，否则你在线上看日志排查问题时，满屏的内存地址会让你抓狂。