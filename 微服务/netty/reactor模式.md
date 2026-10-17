下面介绍nio的三要素 reator是使用三要素构建的一个设计模式。
本质上是多路复用+响应器模式

## Seletor
是读写探测器。是跑在reator循环的主线程里的一个组件。它的核心作用就是绑定上所有连接的channel对象。
底层操作系统来完成 可能是使用poll/epoll 也就是当channel对象有数据产生 也就是有事件的时候 
就会唤醒seletor 并且知道哪个客户端连接有事件发生
所以它是内核层面的东西
## channel
chanel是一个连接对象 是一个实体。 每当有一个客户端要和服务端建立连接的时候 就相当于在接受一个客户端的socket。 就需要建立一个socketChannel对象来管理连接 1000个客户端连接就会创建1000个连接。

并且它是全双工的 区别与BIO里 读写都需要创建对象。

## buffer
是一个数据容器。需要认真分析客户端如何发送数据：
1. 客户端发送数据 是发给服务端网卡的 不能直接发给java线程
2. 操作系统内核告诉seletor这个socket有数据产生 也就是有事件
3. reactor主线程就会调用 channel的方法 把数据从内核缓冲区读取到java的buffer里 java才可以读取数据

## bio两要素
实际上因为bio是半双工的
所以只需要socket作为读/写对象 buffer作为缓冲区
## reator循环

1. 先在操作系统层面创建一个tcp来监听 socket（os层面的内核对象）（java层面是创建一个serversocketchannel） 并且绑定一个端口 后续的客户端都往这个端口连接
2. 此时把这个 服务channel注册到seletor 关心accept 接受连接事件
3. while循环内部 seletor阻塞等待
4. 当有客户端连接进来的时候 seletor被唤醒
5. 执行accept 创建channel对象 并且绑定到seletor上 关心read事件
6. while循环内部 seletor阻塞等待 
7. 客户端产生事件的时候 seletor被唤醒 然后就开始执行事件
8. channel对象去os读数据到buffer
9. 任务丢进pipeline
10. 业务handler开始工作
本质seletor绑定了两个事件 连接和读事件。






