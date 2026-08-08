生产环境中 system prompt不是一段几千字的字符串 而是由多个模块组合而成。

基础行为
+角色 role
+业务目标 goal
+领域规则 rule
+工具策略 tool
+安全策略 safe
+输出契约

模块化的优点 可以带来
- 复用
- 版本管理
- 单独评测
- 快速定位问题
- 不同agent共享基础规则
- 不同业务规则组合不同模块

## 推荐的模块分类

base/
- 基础行为规范
- 语言和沟通方式
- 通用安全要求

identity/
- Role 角色
- Scope  职责
- Audience 审计

task/
- Goal 目标
- Acceptance Criteria 接受标准
- Non-goals 不做什么
- Stop Condition 停止条件

policy/
- Constraints  限制
- Conditional Rules  条件规则
- Uncertainty Policy  不确定性处理
- Error Handling 错误解决 降级策略
- Escalation 升级策略

tools/
- Tool descriptions 工具描述
- Tool-use policy 工具使用规则
- Parameter constraints 参数限制
- Side-effect policy  副作用策略 

output/
- Output Contract  输出契约
- Schema 输出模式
- Error format 错误的格式

examples/
- Few-shot examples 一些案例
- Boundary examples 边界案例

## 模块化的程度

不等于无限拆文件 过度模块化会导致
- 规则分散
- 上下文难以理解
- 模块之间冲突
- 版本难以追踪
- prompt拼接顺序不清楚

好模块的要求
- 有单一职责 不与其他模块冲突
- 可以独立理解
- 有明确输入和输出
- 有明确适用范围
- 不重复定义其他模块的规则

## 组合顺序

没有通用的固定顺序

一般可以

1. Agent身份和职责
2. 总体目标
3. 职责范围和边界
4. 约束和安全限制
5. 工具规则
6. 任务处理策略
7. 输出契约
8. 示例
9. 当前动态上下文

并且避免模型在不同模块之间写互相冲突的规则。

## 静态模块和动态模块分离

动态模块就是当前的信息 
- 当前用户
- 租户
- 任务
- 权限
- 检索结果
- 记忆
- 工具结果
不能直接直接拼接进高权限指令文本中 尤其是来自外部用户 网页 文档数据。

## prompt template

可以给出提示词模版 
```
你是 {agent_role}。

当前用户身份：
<user_context>
{user_context}
</user_context>

当前任务：
<task>
{user_task}
</task>
```

当变量注入的时候 要考虑
- 变量是否可行
- 是否包含恶意指令
- 是否需要转移
- 是否需要为空
- 是否需要长度限制
- 是否包含隐私
- 是否需要审计
动态变量不能覆盖prompt的原油语义

## prompt versioning 版本发布

每次prompt发布 都需要记录

prompt version
model version
tool version
output schema version
context version
eval version

## prompt as code
prompt应该像代码一样管理 
- 代码审查
- 版本控制
- 单元测试
- 变更记录
- Lint检查
- 回归评测
- 灰度发布
## 多模型适配

不同模型对以下内容的表现可能不同
- XML标签
- markdown标题
- few-shot数量
- 工具触发指令
- 推理提示
- 输出格式

因此不能假设一份prompt在all model上表现一致 因此需要采用

共享业务规则+ 模型适配层+模型专输出模版

## 模块化的风险

不同模块之间的冲突

模块顺序影响行为：不同模型对指令位置敏感

prompt过长  模块化虽然提高维护性 但是注入模型的上下文还是有token和注意力的成本存在

依赖隐私上下文 ：一个模块假设模型已经知道另一个模块的内容

## 总结

Prompt 模块化的目的不是把文本机械拆成多个文件，而是让角色、目标、约束、工具、安全和输出契约具有清晰边界，并能够独立测试、组合、版本化和灰度发布。

