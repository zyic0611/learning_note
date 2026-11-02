

Q:**FastAPI为什么适合开发Agent服务？**

A： 

主要是因为异步能力比较适合。 agent服务中大量操作属于io密集型操作 fastapi基于 async/await 可以实现异步编程 在等待io的时候 释放线程 提高并发处理能力。

对接口的开发支持很完善 提供路由管**理 请求参数解析 自动生成api文档**

pydantic提供强类型参数校验 agent场景中有大量结构化参数 比如用户请求 tool参数 llm结构化输出 agent state  可以通过pydantic定义schema。

支持流式响应  agent通常交互耗时长  fastapi支持sse 流式响应。

易于继承agent生态 本身python就很适合 可以结合langchain langraph openaisdk 向量数据库sdk。

总结：

FastAPI适合开发Agent服务主要因为Agent场景有大量IO操作，比如调用LLM、工具和数据库，FastAPI基于async/await可以提升并发处理能力。同时FastAPI结合Pydantic可以方便进行请求和结构化输出校验，并且支持SSE流式响应，适合Agent长耗时、多步骤执行的交互模式。另外Python生态丰富，方便集成LangChain、LangGraph等LLM应用框架。





Q:**FastAPI中的async/await解决什么问题？**

A：

主要用于处理io密集型任务 通过异步编程请求 在等待io结果时 阻塞线程 提高服务并发能力。在agent服务中 请求通常需要等待llm api 数据库 外部工具返回结果 如果使用同步方式 一个请求等待期间 会占用线程 而异步方式可以在等待io时 释放事件循环 让其他请求继续执行 提高并发能力。 

cpu密集型任务就需要多进程或者异步任务队列处理。







Q;**Agent调用多个工具时，如何实现并发调用？**

首先需要分析 多个工具间 是否存在依赖关系。 只有工具之间相互独立 才可以并发调用。 在python中可以使用async。await结合 asyncio.gather 将多个异步任务提交到事件循环中同步执行 等待所有任务结束后汇总结果 再给llm推理。 

同时需要考虑 异常处理 超时控制 并发数量。 避免单个tool失败影响agent整个流程



Q:**Python协程为什么可以提高IO性能？**

本质原因是 在io等待期间 协程可以让出执行权 让事件循环去调度其他任务 避免线程阻塞 提高cpu利用率和并发能力。

一个线程可以管理大量携程。 多线程可以可以提高io并发 但是线程的切换存在开销 而且线程的数量受限于OS，协程通过用户态调度 切换成本低。





Q:**Pydantic除了参数校验，还有什么作用？**

可以作为**数据模型定义**和**数据转换层。**

在fastAPI中 可以通过basemodel 定义请求和响应的数据schema 实现数据解析 类型转换 序列化。

在agent中 还可以约束llm输出格式。





Q:**一个Agent请求很慢，你怎么排查性能瓶颈？**

A：

先进行链路拆分 和耗时监控 拆解请求阶段。

用户请求 - fastapi接口 -agent请求-llm调用 - tool调用 -rag检索 -数据库执行 -llm生成 -返回结果

给每个阶段增加日志和trace  看哪个部分耗时慢。

如果是llm调用慢： 使用更快模型 降低prompt长度 减少上下文token 使用流式输出降低首字响应时间

如果是agent循环太多：排查tool调用次数 node执行次数 设置最大迭代时间 优化prompt 增加终止条件

如果是rag慢 

看是召回慢： 数据库太庞大 索引不合理 topk过大。 

rerank慢：替换模型

tool调用慢：看网络、 用并发调用优化、增加缓存

如果是数据库： 排查慢sql 看索引是否命中 增加索引 排查索引失效的情况 可以使用连接池 优化sql语句 避免一些文件排序、中间表 还有深分页 索引失效

如果是服务本身的问题：看fastapi层代码有没有问题 线程池配置怎么样 并发量怎么样。





Q：trace具体如何做的

最简单的方式就是代码执行前后 记录时间。

agent项目里 langraph的callback 一般自带事件机制 可以监听节点开始结束 tool开始结束 llm开始结束

生产项目一般可以用**链路追踪工具OpenTelemetry** 根据traceid 把llm调用 agent节点 工具调用分装成trace和span 接入企业内部监控系统



Q：你说优化badcase，怎么发现badcase？”

badcase的发现 主要通过线上日期 用户反馈 以及自动化评测（构建评测集 定期跑agent）三个渠道。 

发现问题后 我会记录完整的agent执行链路 保护用户query、检索结果 prmopt上下文 llm输出 工具调用过程。然后分析问题出在哪个环节。 最后把badcase沉淀成测试集 进行回归验证。

Q:**Agent服务如何保证高并发？**

从接口层分析 需要异步提高io并发 因为llm大部分操作都是io操作 所以使用 fastapi的 async和await 还有asyncio事件循环。

从服务层分析： 单个agent实例处理又上线 可以部署多个实例 通过nginx 服务处理发现 进行负载均衡

限制agent并发执行数量 因为agent一次请求 成本比较高 如果瞬间大量流量 则可能导致llm api限流、数据库压力 内存OOM 所以需要控制并发数 比如semaphore

对于长任务来说 如果任务很耗时 比如多论agent推理 大批量文档处理 数据分析 不能一直占用http连接 要引入消息队列 异步处理

对于重复请求 引入缓存减少重复调用 redis存储工具结果信息 热门查询结果信息 

可以优化数据库和外部资源 比如数据库连接池配置 索引优化 外部api超时控制 限流 熔断 重试 避免一个慢服务拖垮agent

控制token消耗： 高并发下 llm的成本和延迟来自token 所以可以压缩prompt 历史消息做摘要 控制rag topk 减少无效agent循环



Q:**如何设计一个生产级Agent服务架构？**

A： 从整体架构分析 可以分为接入层、agent编排层、llm层、能力层，数据层，同时配置可观测性和安全机制。

接入层 主要是fastpic。负责接受请求校验 身份认证和流式响应。

核心编排层使用LangGraph 管理Agent状态 节点执行 条件路由 checkpoint

能力层包括 llm层负责模型调用 需要考虑模型选择 prompt管理 token控制  、tool调用： 需要做好schema校验、权限控制、超时、重试、熔断、rag知识增强层 负责专门领域知识检索查询

数据层： redis存储session 、热点缓存 agent短期状态 、临时查询结果。mysql存储用户的数据 业务数据 等一些需要长期落盘保存的数据。向量数据库存储知识库向量。另外生产环境需要增加任务队列处理长耗时的请求

可观测性：通过opentelemetry和日志系统实现

安全和稳定性：增加权限控制 限流 异常充实 安全过滤等 保证agent稳定运行


Q：FastApi是什么 

A：

FastAPI 是一个基于 Python 类型注解的 Web API 框架。它底层使用 Starlette 处理 Web 请求，使用 Pydantic 完成数据校验和序列化，支持异步编程，并且能够自动生成 Swagger 接口文档。

Q：FastAPI、Flask 和 Django 有什么区别？

A：Flask 是轻量级 Web 框架，自由度比较高，但很多功能需要自己集成。Django 是功能比较完整的 Web 框架，自带 ORM、后台管理和用户系统，更适合完整的网站项目。FastAPI 主要面向 API 开发，支持异步、类型校验和自动接口文档，比较适合微服务和 AI 服务。
