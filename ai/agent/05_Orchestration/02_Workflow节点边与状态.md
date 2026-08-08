

## Workflow 基本结构

```text
Node
    执行一个明确职责。

Edge
    定义节点之间的流转关系。

State
    保存整个流程当前需要共享的数据。

Entry / End
    定义流程入口和终止位置。
```

## 节点

- LLM 节点：分类、抽取、生成或判断。
- Tool 节点：执行外部工具。
- Rule 节点：执行确定性业务规则。
- Human 节点：等待人工确认或补充信息。

原则一般是 尽量职责单一。 
并且尽量不要用llm节点承担本来可以给rule节点确定完成的校验。llm节点具有不确定性和成本 rule节点更稳定 可以审计。


## State 设计

本质是workflow的数据契约 并非聊天记录。
**是节点之间可读写的 结构化的任务上下文。**

内容一般是：
- input 原始请求
- extracted_data 已抽取字段
- tool result 工具结果
- error 失败信息
- output 最终输出

不要丢进去一大堆自然语言 否则很难校验 恢复 测试


## Workflow 与 Agent Loop

- Workflow 主流程由程序定义。
- 某个节点内部可以运行 ReAct 或 Plan-and-Execute。
- 模型不能任意跳过必须执行的安全和校验节点。


## 总结：
Workflow 由 Node、Edge 和 State 组成。Node 封装单一职责，Edge 负责控制流，State 是节点间传递的结构化数据契约。生产环境中，LLM 适合处理语义不确定的任务，规则和关键校验应放在确定性节点中；Workflow 可以在局部节点嵌入 Agent Loop，但不能让模型绕过关键流程。
