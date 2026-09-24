## 主动轮询

对于一个连接 需要分配一个线程 不断的询问需要xxxx吗。 所以对于n个连接 就需要n个线程。 高并发场景下 系统内存会崩溃。

## 反应器思想

给每一个连接安装一个呼叫器。 线程不再主动连接。只有连接的事件发生 线程才根据不同的事件被动做出 react。

本质上就是： 基于时间驱动的响应机制  把主动等待变成了被动通知。

## 伪代码

```java
// 1. 这是一个永不停止的循环 (这就是 Reactor 线程)
while (true) {
    // 2. 阻塞在这里，等待多路复用器 (epoll) 告诉我有事件发生
    List<Event> events = epoll.waitForEvents(); 
    
    // 3. 一旦有事件，就开始分发 (Dispatch)
    for (Event event : events) {
        if (event.type == "新连接入场") {
            Acceptor.handle(event); // 叫接待员去迎客
        } 
        else if (event.type == "客户端发来数据 (可读)") {
            ReadHandler.handle(event); // 叫读数据的处理器去干活
        } 
        else if (event.type == "可以给客户端发数据了 (可写)") {
            WriteHandler.handle(event); // 叫写数据的处理器去干活
        }
    }
}
```

可以看出 多路复用器是核心。 reactor模式就是一个死循环。



## 文件事件处理器

redis基于reactor模式开发了网络事件处理器 叫做文件事件处理器。 

单线程运行 但是通过io多路复用程序监听多个socket。

四个核心组件：

1.多个socket连接

2.io多路复用程序 监听多个socket

3.文件事件分发器：路由功能 接受多路复用程序传来的socket 根据socket的事件类型 调用对应的事件处理器

4.事件处理器：处理对应的事件

