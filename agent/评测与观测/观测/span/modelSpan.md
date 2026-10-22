当runtime调用模型的时候 会创建model span。

流程为：

开始modelSpan->拼接context->request llm->llm response ->结束model Span

主要记录：


**配置：** 模型的配置 比如模型名、模型版本、温度、最大token、提示词版本

**输出：** 文本内容 tool_call 完成原因（为什么此时认为要输出 很重要）

**运行：** 输入token 输出token 延迟 重试此次数 



