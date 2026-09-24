是模型决策规则，在提示词中的形式为：条件规则和决策表。

出现的原因是：提示词中不应该只有 平铺规则 应该表达条件关系。

并且要注意区分：

**Prompt中的条件规则 用于指导模型在某个工作流节点内进行判断 跨节点的确定性路由、权限和状态管理 应有langraph或者agent runtime实现**

所以有两种实现方式
1. Runtime Conditional Routing
2. Model-level Conditional Instruction

## Runtime Conditional Routing

由 langraph 代码 或者工作流引擎实现的。

适合
- 权限
- 状态流转
- 审批
- 重试限制
- 高风险操作
- 任务终止

## Model-level Conditional Instruction

由 system prompt 指导模型在节点内部做出判断

一般是 文本类型的 if xx do xx 或者路由表的形式。

适合
- 是否需要调用工具
- 是否缺少用户信息
- 如何解释工具结果
- 如果处理普通人物分支

相当于runtime的硬约束 属于是软约束。 一般是一些比较自由的路由。

## 总结

If-Else 和状态机不是都应该写在 Prompt 里。对于权限、审批、重试、状态流转等确定性逻辑，应使用 LangGraph 或代码实现；Prompt 中的条件规则只用于指导模型在某个节点内部完成**意图识别、工具选择、参数补全和结果解释**。生产 Agent 通常采用“**代码控制硬约束，模型负责开放式判断**”的混合架构。