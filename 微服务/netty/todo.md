### 第一阶段：温故知新（从 Redis 到 Java NIO）

_既然你已经懂了 Reactor，这一阶段主要是看 Java 怎么落地这些概念。_

- **Java NIO 三剑客**
    
    - `Buffer`（缓冲区）：深刻理解 `position`、`limit`、`capacity` 指针跳跃。
        
    - `Channel`（通道）：全双工的特性，与老 IO 的 `Stream` 对比。
        
    - `Selector`（选择器）：复习 `epoll`，看 Java `Selector` 是如何包装系统调用的。
        
- **Netty 的破局点**
    
    - 为什么不直接用 JDK 自带的 NIO？（Epoll 空轮询 Bug、API 繁琐、拆包粘包痛点）。
        

### 第二阶段：Netty 核心架构与线程模型

_把 Redis 里的“单/多 Reactor”概念直接映射过来。_

- **Netty 线程模型解析**
    
    - `EventLoop` 与 `EventLoopGroup`：它们是如何完美对应 Main-Sub Reactor 模型的。
        
    - `BossGroup` 与 `WorkerGroup` 的职责划分（连接建立 vs IO 读写）。
        
- **责任链模式：ChannelPipeline 与 ChannelHandler**
    
    - Inbound（入站）与 Outbound（出站）事件的传播顺序（**重点也是常踩坑点**）。
        
    - 自定义 Handler 的生命周期（`channelActive`, `channelRead` 等）。
        
- **Netty 的数据载体：ByteBuf**
    
    - 读写双指针机制（再也不用像 NIO 那样频繁调用 `flip()` 了）。
        
    - 内存池化技术（`Pooled` vs `Unpooled`）与直接内存（`Direct` vs `Heap`）。
        

### 第三阶段：网络通信的实战痛点（微服务必备）

_这是微服务通信底层最关注的几个核心问题。_

- **TCP 粘包与半包问题**
    
    - 产生的原因（MTU/MSS、滑动窗口、Nagle 算法）。
        
    - Netty 的四大解码器：
        
        - `FixedLengthFrameDecoder`（定长解码）
            
        - `LineBasedFrameDecoder`（行解码）
            
        - `DelimiterBasedFrameDecoder`（分隔符解码）
            
        - `LengthFieldBasedFrameDecoder`（基于长度字段解码 —— **微服务自定义协议最常用的神器**）。
            
- **编解码与序列化**
    
    - Java 原生序列化的缺陷。
        
    - 集成高效序列化框架：Protobuf、JSON (Jackson/Fastjson)、Hessian。
        
- **连接的保活机制**
    
    - TCP Keep-Alive 的局限。
        
    - Netty `IdleStateHandler` 实现心跳机制（处理微服务节点假死、网络抖动）。
        

### 第四阶段：Netty 高级特性与底层源码（拔高篇）

_面试必备，也是深入理解系统级优化的关键。_

- **真正的零拷贝（Zero-Copy）**
    
    - OS 层面的零拷贝（`sendfile`, `mmap`）。
        
    - Netty 层面的零拷贝（`CompositeByteBuf` 合并、`slice` 切片、`FileRegion`）。
        
- **Netty 性能优化调优**
    
    - `Option` 参数配置（如 `SO_BACKLOG`, `TCP_NODELAY`, `SO_KEEPALIVE`）。
        
    - 高并发场景下的参数选择。
        
- **FastThreadLocal 优化**
    
    - Netty 为什么自己造了一个 ThreadLocal？它是如何解决 Hash 冲突提高性能的？
        

### 第五阶段：终极实战（闭环你的微服务知识）

_用你刚学的知识，把它们串联起来。_

- **实战项目：手写一个基于 Netty 的简易 RPC 框架**
    
    - **注册中心**：用你刚学完的 **Nacos** 做服务提供者的注册与发现。
        
    - **通信层**：用 Netty 建立 Client 与 Server 的长连接。
        
    - **协议层**：用 `LengthFieldBasedFrameDecoder` 设计自定义 RPC 报文头部。
        
    - **代理层**：使用 JDK 动态代理生成接口的代理实现类，屏蔽底层网络调用。