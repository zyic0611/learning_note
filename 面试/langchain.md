

## 1.1 LangChain 是什么？

LangChain 是 LLM 应用开发框架，主要提供：

- 不同模型厂商的统一调用接口；
- 标准化的消息对象；
- Prompt 模板；
- Tool Calling 和 Agent；
- 结构化输出；
- 文档、Embedding、Retriever、Vector Store 等 RAG 组件。

它解决的是**组件标准化和应用编排**，不是让模型本身变聪明，也不会自动保证答案正确。

### 1.2 LangChain 和 LangGraph 的区别

- **LangChain**：模型、消息、工具、结构化输出、Agent 等上层开发组件。
- **LangGraph**：有状态工作流、节点、边、循环、持久化、中断恢复等底层编排能力。
- 简单通用 Agent 可以直接使用 LangChain 的 `create_agent`。
- 流程复杂、需要确定性控制或持久化恢复时，再直接使用 LangGraph。


### 1.3 当前版本意识

本文按 LangChain 1.x 的主流接口准备：

- 使用 `init_chat_model` 或具体厂商的 ChatModel；
- 使用 `create_agent` 创建 Agent；
- 使用 `@tool` 定义工具；
- 使用 Pydantic + `with_structured_output` 获取结构化结果。

旧项目里可能看到 `LLMChain`、`AgentExecutor`、`initialize_agent` 等旧式写法。知道它们是历史 API 即可，不要把它们作为当前面试的主答案。

### 必须知道

- `invoke()` 输入一个请求，返回完整结果。
- ChatModel 返回的通常是 `AIMessage`，不是普通字符串，文本在 `response.content` 中。
- `temperature` 越低，输出通常越稳定，但不代表完全确定。
- `timeout` 是单次调用超时；`max_retries` 是模型客户端层面的重试配置。
- 是否支持工具调用、结构化输出、多模态，取决于具体模型和供应商。
- LangChain 统一了上层接口，但不能抹平所有厂商能力和参数差异。

---

## 3. Messages：模型上下文的基本单位

常见消息类型：

| 类型 | 含义 |
|---|---|
| `SystemMessage` | 角色、原则和全局约束 |
| `HumanMessage` | 用户输入 |
| `AIMessage` | 模型回复，也可能携带 `tool_calls` |
| `ToolMessage` | 工具执行结果，必须关联对应的工具调用 ID |

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage("你是严谨的数据库助手。"),
    HumanMessage("什么情况下联合索引会失效？"),
]

answer: AIMessage = model.invoke(messages)
print(answer.content)
print(answer.usage_metadata)  # 某些模型会提供 token 使用量
```

也可以使用字典格式：

```python
messages = [
    {"role": "system", "content": "你是严谨的数据库助手。"},
    {"role": "user", "content": "解释最左匹配原则。"},
]
```

### 高频追问

**Prompt 和 Message 有什么区别？**

Prompt 是给模型的完整输入设计；Message 是 ChatModel 上下文中的标准消息单位。Prompt 模板最终通常会生成一组 Messages。

**直接连续调用 `model.invoke()` 会自动记住历史吗？**

不会。直接调用模型时，应用必须把需要的历史消息再次传入。会话状态和持久化属于应用层或 LangGraph 的职责。

**为什么不能把所有历史消息无限追加？**

会造成上下文超限、Token 成本和延迟增加，还会引入无关信息。生产环境通常会采用窗口裁剪、摘要和结构化业务状态。

---

## 4. Prompt Template 与 LCEL

### 4.1 ChatPromptTemplate

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是{domain}领域助手，只根据已知信息回答。"),
    ("human", "用户问题：{question}"),
])

prompt_value = prompt.invoke({
    "domain": "MySQL",
    "question": "MVCC 解决了什么问题？",
})

print(prompt_value.messages)
```

Prompt 模板的价值：

- 把固定指令与动态变量分离；
- 统一输入格式，便于复用和测试；
- 可以插入历史消息占位符；
- 便于版本管理和评测。

注意：模板变量仍然可能受到 Prompt Injection。不能因为使用模板，就信任用户输入或模型生成的 SQL、URL、文件路径。

### 4.2 Runnable 与 LCEL

LangChain 的很多组件都实现了 Runnable 接口，可以使用 `|` 串联：

```python
from langchain_core.output_parsers import StrOutputParser

chain = prompt | model | StrOutputParser()

result = chain.invoke({
    "domain": "MySQL",
    "question": "解释覆盖索引。",
})
print(result)
```

数据流是：

```text
dict 输入 → PromptValue → AIMessage → str
```

常用 Runnable 方法：

| 同步 | 异步 | 作用 |
|---|---|---|
| `invoke` | `ainvoke` | 单个输入 |
| `batch` | `abatch` | 多个相互独立的输入 |
| `stream` | `astream` | 流式输出 |

面试要点：LCEL 只是组件组合方式。复杂的有状态分支、循环和恢复不适合只靠一条很长的 LCEL Chain，应使用 Agent 或 LangGraph。

---

## 5. 结构化输出：业务项目重点

自然语言适合展示，不适合直接作为程序控制信号。意图识别、QueryPlan、路由判断等应尽量使用结构化输出。

```python
from typing import Literal
from pydantic import BaseModel, Field

class QueryIntent(BaseModel):
    query_type: Literal["detail", "aggregate", "ranking"] = Field(
        description="查询类型"
    )
    metric: str = Field(description="用户要查询的业务指标")
    city: str | None = Field(default=None, description="城市筛选条件")
    limit: int = Field(default=10, ge=1, le=100)

intent_model = model.with_structured_output(QueryIntent)

intent = intent_model.invoke(
    "查询上海中标金额最高的前 5 家企业"
)

print(intent)
print(intent.query_type, intent.city, intent.limit)
```

### 必须知道

- Pydantic 负责字段类型、枚举、范围、必填项等校验。
- `with_structured_output()` 返回的是包装后的新模型对象。
- 底层可能使用供应商原生结构化输出，也可能使用 Tool Calling 实现，取决于模型能力和配置。
- Schema 合法只表示“格式正确”，不表示“业务语义一定正确”。
- 关键字段还需要业务规则校验，例如指标白名单、城市权限和查询上限。
- 不推荐依赖“请返回 JSON”再用正则截取，因为容易遇到 Markdown 包裹、缺字段和类型错误。

### 面试回答

> 我会把意图、路由和查询计划定义成 Pydantic 模型，使用枚举、范围和字段描述约束模型输出；解析成功后还会执行一层确定性的业务校验。结构化输出解决的是格式稳定性，不能替代业务正确性校验。

---

## 6. Tool Calling：必须真正理解的完整链路

### 6.1 定义工具

```python
from langchain.tools import tool

@tool
def query_amount(city: str, year: int) -> dict:
    """查询某城市某年的中标总金额。

    Args:
        city: 城市名称，例如上海、杭州。
        year: 四位年份，例如 2025。
    """
    # 示例数据；生产环境应在这里调用受控的业务服务。
    return {"city": city, "year": year, "amount": 12_500_000}
```

工具定义中最重要的是：

- 工具名称清楚；
- docstring 准确描述“什么时候使用”；
- 参数类型和描述明确；
- 返回值尽量结构化、体积受控；
- 工具内部做鉴权、参数校验、超时和异常处理。

### 6.2 手动完成一次工具调用循环

这一段建议亲手敲两遍。它能证明你真正理解 Tool Calling，而不是只会调用 Agent 封装。

```python
import json
from langchain.messages import HumanMessage, ToolMessage

tools = [query_amount]
tool_map = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

messages = [HumanMessage("查询上海 2025 年的中标总金额，并用万元表示")]

# 第一次调用：模型判断是否需要工具，模型自己不会执行工具。
ai_message = model_with_tools.invoke(messages)
messages.append(ai_message)

# 应用程序读取 tool_calls 并执行对应工具。
for tool_call in ai_message.tool_calls:
    selected_tool = tool_map[tool_call["name"]]
    tool_result = selected_tool.invoke(tool_call["args"])

    messages.append(
        ToolMessage(
            content=json.dumps(tool_result, ensure_ascii=False),
            tool_call_id=tool_call["id"],
        )
    )

# 第二次调用：模型看到工具结果后生成自然语言答案。
final_message = model_with_tools.invoke(messages)
print(final_message.content)
```

完整过程：

```text
HumanMessage
    ↓
模型返回 AIMessage(tool_calls=[name, args, id])
    ↓
应用执行真实 Python 工具
    ↓
应用构造 ToolMessage(tool_call_id=id)
    ↓
再次调用模型生成答案
```

### 6.3 高频追问

**模型会直接执行 Python 函数吗？**

不会。模型只生成调用请求，包括工具名和参数；LangChain Agent 或应用程序负责匹配并执行工具。

**为什么 `ToolMessage` 需要 `tool_call_id`？**

一次模型回复可能包含多个并行工具调用。ID 用于把每个执行结果与原始调用准确对应。

**`bind_tools()` 做了什么？**

它把工具的名称、描述和参数 Schema 提供给模型，并返回一个绑定工具后的新模型对象；它不等于立即执行工具。

**工具描述为什么重要？**

模型主要根据工具名、描述和参数 Schema 决定是否调用以及如何传参。描述模糊、工具职责重叠会增加错选工具的概率。

**工具返回的数据是否可信？**

要分情况。数据库或内部服务结果可以作为业务数据，但外部网页等工具结果仍是不可信输入，可能包含恶意指令，不能让它绕过系统权限和业务校验。

---

## 7. 使用 `create_agent` 创建最小 Agent

手动循环用于理解原理；实际开发中可以使用 `create_agent` 自动完成“模型 → 工具 → 模型”的循环。

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=[query_amount],
    system_prompt=(
        "你是招投标数据助手。涉及金额查询时必须调用工具；"
        "不得编造数据；最终金额同时给出元和万元。"
    ),
)

result = agent.invoke({
    "messages": [
        {"role": "user", "content": "上海 2025 年中标总金额是多少？"}
    ]
})

print(result["messages"][-1].content)
```

### Agent 的本质

Agent 不是一个神秘组件，本质上是一个循环：

1. 把消息和工具描述交给模型；
2. 模型决定回答还是调用工具；
3. 如果调用工具，运行工具并把结果加入消息；
4. 再次调用模型；
5. 直到模型不再发起工具调用，或达到停止条件。

### Agent 和固定 Chain 怎么选？

- 步骤固定、强调确定性：优先普通代码、LCEL 或 LangGraph 固定工作流。
- 工具选择和执行顺序确实需要模型动态决策：使用 Agent。
- 涉及转账、删除、发消息等高风险副作用：不能让 Agent 无约束自主执行，需要权限校验、人工审批和幂等保护。

### 为什么生产环境不能只写 `create_agent()` 就结束？

还必须考虑：

- 最大执行步数和死循环；
- 模型与工具超时；
- 哪些错误可以重试；
- 工具副作用和幂等；
- 用户、租户和数据权限；
- 上下文裁剪；
- Token 与延迟预算；
- 日志、Tracing、评测和告警；
- Prompt Injection 与敏感数据泄露。

---

## 8. 流式、异步和批处理

### 流式模型输出

```python
for chunk in model.stream("用三点解释事务隔离级别"):
    print(chunk.text, end="", flush=True)
```

### 异步调用

```python
response = await model.ainvoke("解释什么是 MVCC")
print(response.content)
```

### 批处理

```python
responses = model.batch([
    "解释 B+ 树",
    "解释覆盖索引",
    "解释索引下推",
])
```

面试要点：

- I/O 密集型服务通常优先使用异步接口提高并发能力。
- `batch` 适合相互独立的请求，不等于一次对话的多轮上下文。
- 流式输出降低的是用户感知到的首字延迟，不一定降低总耗时或 Token 成本。
- SSE 只是把服务端事件持续传给客户端；它和模型流式 API 不是同一个概念。

---

## 9. 工程化高频问题

### 9.1 重试

适合重试：

- 短暂网络错误；
- 限流；
- 部分服务端错误。

不应盲目重试：

- 鉴权失败；
- 参数或 Schema 错误；
- 确定性的业务校验失败；
- 已经产生副作用、但执行结果未知的操作。

重试应配合指数退避、随机抖动、最大次数和全链路重试预算，防止重试风暴。

### 9.2 结构化输出失败

处理顺序通常是：

1. 捕获校验异常；
2. 判断是临时模型输出问题还是业务输入缺失；
3. 必要时进行有限重试或让模型修复；
4. 仍失败则降级或向用户澄清；
5. 记录原始响应、Schema 版本和错误分类，但注意脱敏。

### 9.3 Token 与上下文治理

- 只注入与当前任务相关的信息；
- 大型工具结果先过滤、聚合或摘要；
- 完整数据放外部存储，模型上下文只放摘要和引用；
- 区分对话消息、结构化业务状态和外部查询结果；
- 用真实 Token、延迟和任务成功率做评测，不凭感觉优化。

### 9.4 可观测性

至少记录：

- request/session/trace ID；
- 模型名称与 Prompt 版本；
- 每次工具名、参数摘要、耗时和结果状态；
- Token、首字延迟和总延迟；
- Agent 步数与停止原因；
- 异常类型、重试次数和降级结果。

不要在日志中直接记录 API Key、完整个人信息或未经脱敏的业务数据。

---

## 10. 大厂面试常问：精简回答

### Q1：为什么使用 LangChain，不直接调用模型 SDK？

> 简单调用我可以直接使用厂商 SDK。使用 LangChain 的价值主要在于统一模型与消息接口、工具与结构化输出抽象、Runnable 组合以及与 Agent、LangGraph、Tracing 体系集成。代价是多一层抽象，所以我会根据复杂度选择，而不是所有项目都强行使用。

### Q2：Chain 和 Agent 的区别？

> Chain 的步骤通常由开发者预先确定，执行更稳定、容易测试；Agent 让模型动态决定工具及执行顺序，灵活但不确定性、成本和风险更高。关键业务流程应尽量确定性编排，只在真正需要语义决策的位置使用模型。

### Q3：Tool Calling 和普通 Prompt JSON 有什么区别？

> Tool Calling 使用模型提供商定义的工具调用协议，输出包含工具名、结构化参数和调用 ID，比要求模型在普通文本里输出 JSON 更稳定，也能正确关联并行工具结果。但参数仍然来自模型，执行前必须校验。

### Q4：结构化输出能保证正确吗？

> 只能提高格式和类型的可靠性，不能保证事实与业务语义正确。后面仍需做权限、枚举、范围、字段关系和数据存在性校验。

### Q5：Agent 如何避免死循环？

> 设置最大步数或递归限制；记录重复工具调用及参数；对错误分类，不让不可重试错误持续反思；设置 Token、时间和工具调用预算；达到阈值后降级、澄清或终止。

### Q6：Prompt Injection 怎么防？

> 不把模型当权限系统；系统侧固定工具白名单和参数校验；鉴权由后端上下文注入而不是相信用户提供；外部检索内容视为不可信数据；敏感操作增加审批；最终由代码执行权限和业务规则兜底。

### Q7：为什么工具结果不直接全部放入上下文？

> 大结果会增加 Token、延迟和敏感信息暴露风险，也可能稀释关键信息。通常返回必要字段、统计摘要和结果引用，完整结果留在受控存储中。

### Q8：LangChain 的抽象有什么缺点？

> 版本变化较快；复杂封装可能隐藏底层模型请求与错误；不同供应商能力仍有差异；排障时需要理解实际消息、工具协议和执行循环。因此生产代码需要锁定版本、保留 Tracing，并理解框架下面发生了什么。

---

## 11. 面试前必须能现场写出的代码

按优先级练习：

1. `init_chat_model` + Messages 调用模型；
2. `ChatPromptTemplate | model | StrOutputParser`；
3. Pydantic + `with_structured_output`；
4. `@tool` + `bind_tools`，手动执行一次工具调用循环；
5. `create_agent` 创建工具 Agent；
6. `stream`、`ainvoke` 能说清用途。

通过标准：

- 不看 AI，30 分钟内写完第 1～5 项；
- 能画出 `HumanMessage → AIMessage(tool_calls) → ToolMessage → AIMessage`；
- 能解释每个对象是什么，而不是只记住 import；
- 能补充超时、重试、权限、幂等和日志等生产问题。

---

## 12. 一页速记

```text
模型调用：init_chat_model → invoke / ainvoke / stream
消息类型：SystemMessage / HumanMessage / AIMessage / ToolMessage
Prompt：ChatPromptTemplate
组合方式：prompt | model | parser
结构化输出：Pydantic + model.with_structured_output(...)
工具定义：@tool
工具绑定：model.bind_tools(...)
工具请求：AIMessage.tool_calls
工具结果：ToolMessage(tool_call_id=...)
Agent：create_agent(model, tools, system_prompt)

最重要的三个判断：
1. 模型只提出工具调用，程序才真正执行工具。
2. 结构化输出保证格式，不保证业务正确。
3. Agent 适合动态决策，确定性流程优先用代码或图编排。
```

---

## 13. 官方资料

- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)
- [LangChain Messages](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [ChatPromptTemplate API](https://reference.langchain.com/python/langchain-core/prompts/chat/ChatPromptTemplate)
- [Runnable API](https://reference.langchain.com/python/langchain-core/runnables/passthrough)

> 学习方法：先看本文并手敲代码；遇到版本差异时，以官方文档和项目实际锁定版本为准，不要混用旧博客中的 API。
