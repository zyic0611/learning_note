
llm返回的并非任务结果 是提出的下一步候选行动。 比如tool call

runtime执行后 环境中出现了新的observation 模型需要基于它重新理解 所以需要一个loop。

loop是由runtime外部控制 并非llm自己递归调用自己。

  

理解loop里的三个运行边界。

Message： 一条用户、工具、llm消息。

Turn：一次模型调用。

Run：从本次用户请求开始 到agent最终结束。 可能包含多个turn。