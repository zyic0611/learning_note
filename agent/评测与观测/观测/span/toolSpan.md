模型生成的tool call 属于model span.
runtime解析tool call、鉴权、选择工具

核心记录工具执行的内容
- 工具名称、工具版本
- 实际请求参数 请求id 
- 工具执行结果 状态 错误码
- 延迟 重试次数 超时时间

