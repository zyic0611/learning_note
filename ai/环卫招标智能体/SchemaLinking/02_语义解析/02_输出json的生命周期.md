最好 既驱动 Schema Linking，又注入 SQL 生成阶段的 Prompt。

输出的json一般叫做QueryIntent

## 如果只用来模式召回
当llm召回模式后 生成sql的时候 还需要重新理解用户的问题 存在重复 工业级做法一般把QueryIntent 作为Agent State保存。 后续节点都可以消费这个状态

## 如何注入SQL prompt
不能把完整的json都塞进去。 比如用户问题 +QueryIntent都注入 会让LLM过度依赖解析结果。

推荐prompt：
```
你是SQL生成专家。 
用户需求: 查询浙江2025年垃圾运输量 
已解析业务语义: 
指标: - 垃圾运输量 
维度: - 城市 
过滤: - 
时间=2025 - 
地区=浙江 
可用Schema: 
table: project 
columns: transport_weight city_id create_time 
join: project.city_id=city.id 

生成SQL
```

## 关键

**混合解析出来的结果：**

QueryIntent并非事实 他只是上游理解结果  所以 Prompt 里应该告诉 LLM：
`以下是系统解析出的业务意图， 请结合用户原始问题和Schema进行校验。`
避免LLM盲信错误解析。

**规则解析出来的结果：**

属于高可信 可以直接进入schema linking的约束

## 总结：

QueryIntent 不仅用于 Schema Retrieval，还作为 Agent State 注入后续 SQL Generation。
规则解析结果作为高置信约束参与 Schema Linking，
LLM解析结果作为语义上下文辅助 SQL生成。

最终 Prompt 中同时包含原始用户问题、结构化 QueryIntent、裁剪后的 Schema 和 Join Hint。


