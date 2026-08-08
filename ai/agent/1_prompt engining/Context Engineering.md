Context Engineering 

- Prompt Engineering：设计和组织模型指令。
- Context Engineering：设计每次推理时模型能看到的完整信息集合。
- Prompt Engineering 是 Context Engineering 的一个子集。
  
上下文工程是提示词工程的自然扩展 而不是替代关系


## context的组成

指令性上下文
- system/developer instructions 系统指令
- 用户当前任务
- 工具使用规则
- 输出契约

知识性上下文
- RAG检索文档
- 数据库结果
- 文件和代码
- 外部API数据

状态性上下文
- 历史对话
- 当前计划
- 已完成步骤
- 工具调用和结果
- 环境状态

记忆
- 工作记忆 一般是短期记忆 当前正在处理的记忆
- 情景记忆 长期记忆，过去发生过的具体时间
- 语义记忆 长期记忆 稳定积累下来的经验 可以重情景记忆中提炼

上下文管理规则：
- 相关性 ：只放当前任务需要的信息
- 新鲜度：避免过期皇台
- 来源：保留provenance和引用 也就是检索来的信息可以溯源
- 权限：不能检索用户无权访问的数据
- 信任边界： 网页、文档、工具调用结果 可能包含 prompt injection
- token budget： 上下文不一定越长越好
- compaction：长任务需要摘要和状态压缩
- progressive disclosure : 渐进式披露 不一次给所有信息 先给高层信息 再通过工具按需加载信息细节
- just-in-time Retrival 检索也是 需要的时候再检索 不要一次性塞入所有资料。


所以高质量上下文 就是尽可能小的 但是信号高的 信息集合。
并且长上下文会出现 注意力稀释、工具结果膨胀、context rot（上下文腐化）