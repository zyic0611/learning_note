subAgent

Claude Code 的子 Agent，本质是：主模型通过 Agent 工具提出一个子任务，Runtime 为它配置独立的消息历史、模型和工具，再运行一套 Agent Loop，最后把结果交回主 Agent。

和主Agent需要context管理一样 子 Agent 则可以 把探索过程放在另一个 Context 中，从一开始就减少主 Context 的增长 。

实现方法就是主Agent输出一个 Agent工具调用 runtime接受调用 校验参数 解析子 Agent 定义并启动执行。

并且这个子agent执行的时候是复用 Agent Loop。有两类子agent

## 普通子context

给一个任务 构造新的上下文开始工作

context为本次委派任务和必要信息

systemPrompt为子agent自己的角色指令

工具集合为子Agent定义和规则筛选

模型也是按照配置使用

## Fork Agent

带着父agent的上下文 分出去做另一个指定的任务。

context为父工作消息历史和本次委派指令

systemPrompt继承+追加子任务约束

工具集合和父一致

模型也继承

## 决策

尽量使用普通subAgent 如果任务严重依赖前面的决策和讨论 用Fork 因为明显Fork初始携带