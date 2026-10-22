记录runtime执行 除了llm、tool外的节点编排逻辑。
它是一个观测类别 并不是唯一的span类型 所以它有很多具体的span类型 每种span类型记录内容不一样。
泛指由runtime编排逻辑产生的span。
具体有：
workflow span （ 粒度最大 包括了一批span。
- 节点span
- 调度span
- 上下文构建span
- 验证span
- 工具调度span
- 人工审批span
- model/tool span也会出现 但是一般这些单独归一类 上面那些都是runtime span。

并非所有runtime行为都需要构建span 还是观测层级来判断 如果是瞬间进行的操作 就是event。 持续一段时间 才是span。

现在分析runtime span的每种 都记录什么信息。

## workflow span
粒度最大 包括一次workflow的完整执行。

所以一般记录：
- 名字、版本
- 入口参数摘要
- 开始、结束时间
- 终止原因
- 总重试次数
- 总token消耗

回答的是 整个编排跑了多久 完成了吗 在那里完成 
## node span
workflow中某个业务节点的执行

- 名字、类型
- 输入状态 输出状态
- 开始时间 结束时间
- 状态
- 错误信息
- 重试次数

回答的是 哪个节点执行 执行情况如何 输入输出是什么

## scheduling span

表示runtime把任务交给下一个执行单元的过程。

runtime决定执行xx 放入队列 worker获取任务 开始执行任务

- 目标node
- 队列名称
- 调度原因
- 调度时间
- 队列等待时间
- workerId
- 调度状态
- 超时时间

核心在： runtime是否正确调度 任务在队列里排队多久 有没有丢失、延迟、超时

如果是瞬间选择的话 route event即可。 如果有队列等待or异步调度 才适合单独建span。

## 工具调度span
区别于工具调用span。

核心记录 runtime决定并准备调用哪个工具。
- 需要什么tool
- 实际选择了什么tool
- 选择原因
- 实际参数
- 路由结果
- 超时策略
- 状态

## 人工审批span

表示任务进入人工介入流程

可以记录
- 审批类型
- 审批原因
- 需要多少时间
- 超时时间
- 拒绝原因






