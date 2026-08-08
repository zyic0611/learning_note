## 个人技术笔记

后端开发方向的技术笔记，以 Markdown 形式整理，覆盖 Java 生态、中间件、Spring 框架、计算机网络、AI 应用等方向。

> 目标：体系化知识，而非零散记录。

---

### 仓库结构

```
.
├── java/                   # Java 核心
│   ├── basic/              #   基础：OOP、异常、泛型、String、Object、数据类型
│   ├── Collections/        #   集合：HashMap、ConcurrentHashMap、List
│   ├── JVM/                #   JVM：内存结构、GC、类加载、OOM/CPU 排查
│   └── JUC/                #   并发：锁(synchronized/CAS/volatile/ReentrantLock)、AQS、线程池、ThreadLocal
│
├── 中间件/                  # 中间件深入
│   ├── mysql/              #   MySQL：架构、存储引擎、索引、事务&MVCC、锁、日志、调优、高可用&分库分表
│   ├── redis/              #   Redis：基础/进阶类型、底层数据结构、线程模型、持久化、高可用、分布式锁、缓存问题
│   ├── rabbitmq/           #   RabbitMQ：基础、可靠性投递、DLX、幂等性、削峰填谷
│   └── es/                 #   Elasticsearch：基础、分布式架构、与 MySQL 数据一致性
│
├── spring生态/             # Spring 生态
│   ├── springboot/         #   Spring Boot：IOC&DI、AOP、自动装配、Bean 生命周期、循环依赖、事务管理
│   └── springsecurity/     #   Spring Security：RBAC、鉴权、框架架构
│
├── 计算机网络/              # TCP(握手/挥手/滑动窗口/拥塞控制)、HTTP、HTTPS
├── 网络架构原理/            # IO 模型、Reactor 模式
├── 算法/                   # 二分查找、String 类、集合 API
│
├── ai/                     # AI 应用
│   ├── agent/              #   Agent：提示词工程、推理规划、工具调用、记忆层、多智能体、工程落地
│   └── rag/                #   RAG：数据接入&索引、查询理解、检索&召回、召回后处理、生成闭环
│
├── os/                     # 操作系统（待完善）
├── 简历/                   # 简历、项目总结
└── 常用指令.md             # 常用命令速查
```

---

### 内容特点

- **体系化组织**：按知识域分层，每个子域有清晰的阅读顺序
- **源码导向**：JUC、Collections、Spring Boot 等深入源码层面
- **原理优先**：侧重"为什么"而非"是什么"，关注本质
- **持续迭代**：长期维护，跟随技术演进补充

---

### 技术栈

Java / JVM / JUC · MySQL / Redis / Elasticsearch · RabbitMQ · Spring Boot / Spring Security · TCP/IP · Agent / RAG

---

### 关于笔记

所有内容为个人理解整理，偏向原理讲解、关键点总结和面试视角，不求面面俱到。
