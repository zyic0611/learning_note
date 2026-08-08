## tool calling是通信协议

参与者包括 model 、agent runtime 、tool executor

则三者之间需要传递
```
Model → Runtime：
我要调用哪个工具，候选参数是什么？

Runtime → Model：
对应的工具调用执行后，得到什么结果？
```

实际上是一套 请求-响应协议

tool call  ： 模型向runtime发出的结构化请求

tool result ：runtime 向模型返回的关联响应。

所以tool calling 包括：tool call 和tool result

类似于http 请求-响应：
```
HTTP Request
├── request id
├── endpoint
└── body

HTTP Response
├── request id
├── status
└── body

Tool Call
├── tool_call_id
├── tool_name
└── arguments

Tool Result
├── tool_call_id
├── status
└── content/data

```

但是tool calling比普通http请求多了一层：  请求是概率模型生成的 协议正确不代表业务正确。


## 一次llm请求包含

概念上 runtime 会提供
- message 历史消息
- tools列表 可调用工具
- tool choice 工具调用策略：

```
auto
    模型自行决定是否调用工具

none
    不允许模型调用工具

required
    要求模型必须调用工具

specific tool
    强制模型调用某个指定工具
```

这属于协议控制 不代表模型生成的参数一定对

因为强制调用某个工具 只能保证模型尝试产生这个tool的tool call 不保证参数之类的正确 也不代表调用一定有必要

## 模型响应的形式

一次模型调用后，Runtime 不应该假设模型一定返回文本或一定返回工具调用。

至少要处理下面几类结果。

### 最终文本

输出文本 没有输出tool cal

但是不一定等于任务成功 需要由runtime判断任务状态

### 单个tool call

runtime应该保存 Assistant信息 解析 校验 执行 写入Tool Result 再次调用模型

### 多个tool call

表示llm在一次响应中提出多个工具调用

但是同时生成 不一定可以并行执行 还需要分析
- 两个调用是否相互依赖
- 是否修改同一资源
- 是否存在执行顺序要求
- runtime是否允许并发

### 文本与tool call同时出现

某些模型协议是允许这种情况的。

这里的文本一般是过程性说明 并非最终答案。 Runtime不应该因为存在content就立即结束任务。 应该优先识别 **是否存在待处理的Tool Call**

更稳妥的流程：
1. 是否有ToolCall 有则处理调用
2. 没有Tool Call 再判断文本属于最终回答、澄清、拒绝、还是失败说明

## tool_call_id

是调用id 是用于连接 tool  call和 tool result的关联。
当并行调用的时候 尤其重要 。 否则发起tool call的顺序 可能和得到tool result的顺序不同 不知道那个结果是哪个工具的结果。

并且调用ID应该被视为不透明值 Runtime应该直接保存并返回 不能对其进行修改。 因为Runtime只需要知道其用于关联 不需要解释其内部结构。

### 其他id：

- tool_call_id： 关联模型协议中的调用与结果
- execution_id： 标识runtime的一次真实尝试
	- 是执行记录id  runtime只要执行一次工具调用 就会产生一次执行记录
	- 对于一个工具调用 可能产生很多次执行记录
	- 因为可能重试 被取消 被拒绝 需要用户确认 校验失败
	- 所以必须和工具id分离
	- 但是只会产生一份 面向llm 的tool result
- business id：标识业务对象的id
- trace id：关联整个任务的 可观测链路id




## 协议层和状态 分开

tool_result里：
协议层里的role=tool 只代表这条消息是对应工具调用返回的消息。 **但是不等于工具执行成功** 

真正的业务状态信息在 content字段里。 或者在status字段里。

status状态语义：
- success
- error
- partial_success
- accepted 异步任务被接受 但是未完成
- cancelled
- unknown


## 流式tool call

模型的tool call不一定一次完整输出 流式生成中 可能每次只输出一部分chunk。 所以runtime不能把每次收到的chunk都当成完整json解析。

正确流程：
1. 接受流式事件
2. 根据call index or call id 分组
3. 累计工具名称片段
4. 累计auguments字符串片段
5. 等待tool call完整事件
6. 再解析完整json
7. 最后进行schema校验和执行。

显然 不能边接受 边执行。 参数尚未准备完成 就执行 会产生严重错误。 一般原则： **Tool Call未完成前 只进行缓冲和展示 不进行真实执行**

## 内部统一协议

不同模型供应商可能使用不同名称和结构表达：
```
工具定义
Tool Call
Tool Result
流式事件
结束原因
工具选择策略
```

如果业务代码直接以来 供应商字段 当切换模型的时候 业务逻辑需要大面积修改。

比较好的架构

1. Provider Api
2. Provider Adapter
3. Internal Tool Protocol 内部工具协议 
4. Agent runtime

内部统一协议是一组 agent系统自己定义的数据类型和语义规范。 
比如可以定义内部所有 tool call的格式都用一个对象InternalToolCall 所有模型的响应都用一个对象 所有工具结果都用一个对象InternalToolResultInternalAssistantTurn

这样Runtime只依赖内部协议 不关心上游到底是什么模型 也不关心不同的工具结果是什么输出格式 都转成同一格式

## Provider Adapter

主要负责协议翻译。 是真正自信转换工作的代码。

在请求方向中：也就是向llm的请求中
消息 工具定义 工具调用策略 先经过provider adapter层 通过内部协议 转换为厂商协议 最后才可以进入 具体模型API 

响应方向中：也就是llm的输出 具体llm api响应后 会返回自己的厂商结构 经过provider adapter 统一翻译为内部协议 再输出文本、tool call、usage。

所以该层通常职责为：
- 转换消息角色和内容结构
- 转换工具定义
- 转换工具调用策略
- 解析工具调用
- 组装流式参数
- 保留原始调用ID
- 标准化token usage

不负责：
- 业务权限
- 用户确认
- 订单规则
- 工具真实执行
- 业务重试
这些由业务层或者runtime做。

## 内部协议不能强行抹平所有差异

统一抽象可以 但是不能模型能力不同。 所以内部协议需要定义能力信息 然后用true false字段 来区分不同模型的能力信息。

所以思路不是假设所有完全一样 而是 统一共同语义+显示暴露能力差异。


## 客户端历史和服务端历史

Tool calling的历史 可能由两种方式维护

### 客户端管理

客户端是指 调用llm api的一方。 一般是应用后端或者agent runtime。

客户端管理消息指的是 由agent runtime自己保存完整消息历史  每次调用llm 都发送完整的历史给模型厂商。 

所以message （user、assistant、tool ）全量发送

优点：
- 状态完全可见
- 不依赖服务端会话
- 容易迁移和回放

缺点：
- 每轮都需要重发历史
- token和请求题持续增长
- 客户端管理复杂

### 服务端管理

服务端一般指的是 模型厂商的服务器。 
服务端管理历史指的就是 模型厂商保存之前的模型上下文 客户端下一次请求只需要提供 某个 **会话id 、上一轮响应id **

服务端根据id 找到之前的上下文
优点：
- 客户端请求简单
- 不一定需要重发完整历史
缺点：
- 更依赖供应商状态
- 调试和迁移复杂
- 仍然需要应用保证自己的业务执行状态

不管哪种方式 都不能只靠模型供应商保存业务状态 必须要保存在业务系统或者runtime状态中

### 混合模式

真实设计中：一般采用混合模式

模型厂商服务端：保存模型上下文连接 减少请求组装工作 **负责上下文凭借拼接

Agent Runtime： 保存必要消息、工具执行、任务状态

真实业务系统： 保存订单 支付 邮件等权威业务状态。

## 工具消息历史剪裁

一组完整的历史理解为：
tool call+tool result+必要的关联元数据。

裁剪的时候必须 整体保留、整体摘要、或者整体删除。

可以摘要已完成的调用 ：
- 摘要不是原始Tool result。
- 重要的业务状态要保存在runtime state里
- 高风险操作的审计 不能只保留模型摘要
- 需要回放的时候 还要保留外部日志或者原始记录