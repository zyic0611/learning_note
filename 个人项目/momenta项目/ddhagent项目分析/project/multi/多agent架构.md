# Multi-Agent 编排 · 叙事版

## 30 秒故事线（开场直接背这个）

> 用户请求进来，LeadAgent 把它拆成任务清单——每个任务只声明自己产出什么、消费什么，依赖关系由服务端从 produces/consumes 自动推导，不让 LLM 连边。服务端解析成 DAG，三层校验：结构、环、数据流完整性，全过才执行。执行按拓扑序，无依赖节点并行、有依赖的等上游输出落库；节点状态热态在 Redis，PG 做持久化兜底崩溃恢复。聚合前仲裁层检测跨 Agent 矛盾。整体原则一句话：**LLM 只声明关系，正确性交给确定性代码。**

---

## 核心设计：produces/consumes（最重要的一个点）

LeadAgent 输出的不是"谁依赖谁"，而是每个任务的 I/O 描述：

```json
{"tasks":[
  {"id":"A","agent":"selection","goal":"筛满足功耗的候选",
   "produces":["selected_part_number"]},
  {"id":"B","agent":"test","goal":"列出该型号测试项",
   "consumes":["selected_part_number"]},
  {"id":"C","agent":"project","goal":"查项目进度",
   "produces":[],"consumes":[]}
]}
```

服务端发现 B 消费的恰好是 A 产出的 → 自动推导出 A→B 依赖边；C 无消费无生产 → 独立，与 A 并行。

**为什么这样设计**：让 LLM 直接声明依赖边容易漏连/瞎连；produces/consumes 更贴近自然语言，而且带来一个 LLM 直接连边时没有的校验——数据流完整性检查。

---

## 三层校验

```
① Schema 校验      结构化输出强制，字段/枚举在生成时就锁死，不是生成完再校验
② 环检测           Kahn's 算法（BFS 拓扑排序），顺带拿到拓扑序，O(V+E) 一次搞定
③ 数据流完整性      某任务 consumes 的字段没有人 produces、也不在用户请求里 → 幻觉输入，拒绝
```

第三层最深：能抓"LLM 编造了一个不存在的上游输出"的问题，前两层抓不到。

---

## 执行与工作记忆

- **调度**：拓扑排序后同层节点用 `asyncio.TaskGroup` 并行，跨层串行
- **工作记忆**：节点状态 + 专家 Agent 输出热态存 Redis（task_id Hash，任务级 TTL）；同时持久化到 PG 四张表，崩溃后从 PG 恢复
- **派发前检查**：所有 consumes 字段都有 SUCCESS 的 producer 输出才入队，不是 sleep 等
- **专家 Agent 无状态**：它只做"读自己的输入 → 执行 → 写回输出"，状态全在底座

---

## 节点失败处理

**两件事必须分清：**

- **abstention**（查不到/低置信度）= 正常终态，不阻断下游，触发 replan 评估
- **FAILED**（工具/LLM 调用异常、超时重试耗尽）= 其 produces 值不存在 → 消费它的下游自然 SKIPPED，不需要额外判断

一个上游 SUCCESS 一个 FAILED → 下游直接 SKIPPED，契约全有或全无。

---

## 仲裁层

聚合前、所有相关节点到达终态后触发，独立校验步骤。

**规则是实体中心的，不是 Agent 对的：**

```yaml
entity: component
rules:
  - condition:
      conflict_if: selection.recommended_part IN test.known_issues[*].part_number
    action: trigger_replan          # 可收敛 → 局部重规划
  - condition:
      conflict_if: selection.delivery_date > project.deadline
    action: present_to_user         # 价值权衡 → 不替用户决定，原样呈现
```

加第 4 个 Agent 时，已有规则自动生效，O(1) 扩展。  
第一层确定性规则，第二层轻量 LLM 兜底规则覆盖不到的类型。

---

## 与 RAG 的闭环（面试时主动说这句）

视觉检索 MaxSim 低置信度 + 结构化查询 abstention，正好是仲裁/replan 的触发信号：

```
选型 Agent 内部：MaxSim 分低 → abstention → 上报编排层
编排层：收到 abstention → 评估是否 replan（扇出多候选 / 转人工澄清）
```

三个亮点在质量信号上闭环，不是三个独立模块。

---

## 降级链路

| 触发 | 降级动作 |
|---|---|
| 计划生成失败 | 先把校验报错喂回 LLM 自修一次，再降级单 Agent |
| 专家 Agent FAILED | 阻断下游 SKIPPED + 聚合时明确标注部分完成 |
| 跨 Agent 矛盾 | 可收敛 → 局部 replan；价值权衡 → 呈现用户 |
| 成本超限 | 预算熔断，未派发标 SKIPPED，说明原因 |

---

## 最高频追问 · 一句话答案

**Q：为什么不让 LLM 直接声明依赖边？**  
→ 容易漏连/瞎连，produces/consumes 更贴近自然语言，而且换来数据流完整性检查这层 LLM 连边时没有的保障。

**Q：为什么不用单 Agent 挂一堆工具？**  
→ 每个 DAG 节点是完整的独立推理循环，内部自己判断重试/换路；单 Agent 是扁平并行 + 事后统一判断，一个上下文装所有域的检索结果，又长又容易互相干扰。

**Q：环检测为什么用 Kahn's 不用 BFS 判重？**  
→ 有向图里汇聚点（A→C、B→C）会被误判为环，Kahn's 入度机制才是标准做法，而且顺带拿到拓扑序，一次两用。

**Q：崩溃恢复怎么做？**  
→ SUCCESS 复用缓存；PENDING 且上游全成功重新入队；RUNNING 先查 tool_calls 有没有已发出的副作用操作，不能无脑重跑；FAILED/SKIPPED 维持原状。

**Q：60s→35s 怎么来的？**  
→ 真实请求抽样 + 构造跨部门复合任务集，对比改造前串行执行的基线，加速来自两点：同层并行砍掉串行等待 + 局部 replan 避免整体重来。（注意：这个数字是单请求执行维度，不要和并发治理的 P95 15s→5s 混）