Multi-Agent 是把一个复杂任务拆给多个职责明确的 Agent 协作完成。

一般的流程
1. 用户任务
2. orchestration/workflow
3. 分发给 专用aent
4. 收集结构化结果
5. 汇总并且输出

所以 多智能体的目标是 能力隔离、权限隔离、上下文收敛。 并非多个agent自由聊天。

## 基本角色

- orchestrator 分发者。 负责选择执行者 分发任务 管理状态 处理失败 汇总结果。
- specialist agent 执行者 只处理一个明确的领域
- handoff：将任务及必要上下文 交给下一个agent的 受控 交接动作。

分发者可以是一个agent 也可以是确定性的workflow/ runtime。所以关键调度和权限控制 不应该完全依赖于llm

## handoff 传递内容

最小必要上下文：
- task 需要完成的子任务
- input 完成task所必要的数据
- constraints：权限、成本、时间、业务限制
- history_summary 必要的已完成结论 而不是完整的聊天记录
- expected_output 输出格式和验收标准
- trace_id 关联整个任务链路的标识


不可以默认共享完整对话和全部state 否则会导致
- 无关上下文干扰
- 敏感数据泄露
- token成本失控
- agent之间的责任边界不清楚

## 权限隔离

不同的agent应该拥有不同的工具和权限数据。 要遵循最小权限原则 即是某个agent出问题了 比如提示词注入还是输出异常 影响范围也应该被限制在自身权限内

## 协作失败如何处理

类似于节点 orchestrator需要给每个子agent定义
- 超时后的处理： 重试、降级、跳过、或者转人工
- 失败后的影响范围： 子任务失败是否会导致全部任务失败
- 输出校验： 结果必须符合预期的schema
- 结果冲突： 优先选择可信数据源、请求补充证据、或者人工总裁。

同时、不能把某个agent的自然语言结论 作为事实。 关键结果应该附带来源、工具结果、或可验证依据。

子agent输出
-> schema校验
-> 关键事实验证
-> 汇总
-> 最终输出

## 总结：
Multi-Agent 的价值不在于增加 Agent 数量，而在于把不同领域能力和权限拆开。Orchestrator 负责受控分发、状态管理与结果汇总，Specialist Agent 只处理边界清晰的子任务。Handoff 传递任务、最小必要上下文、约束和结构化输出要求，而不是完整上下文。对于高风险或无法可靠自动完成的步骤，Workflow 应支持 interrupt、Checkpoint 和 resume，将任务交给用户或人工审批后再继续。

