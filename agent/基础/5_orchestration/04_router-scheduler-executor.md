加上state 这4个是编排中 一次执行的核心组件  
## router
一般是2种路由 都是根据state去做。

当state里面有明确字段映射到路由时 直接路由 这种就是**确定性规则**

只有路径选择自然语言语义的时候 才需要**模型路由** 但是模型也只能从runtime提供的白名单中选择。

- **置信度不足 或 语义歧义** 应请求澄清。
    
- **超出能力边界或者高风险** 转人工or stop

禁止把未知请求分配给最近路径。
## scheduler

scheduler就是orchestration里的 负责编排runtime的调度者 核心负责

**在一条路径上 根据依赖关系和state 找出哪些节点具备执行条件 可以执行**

在workflow的简单串行模式里 scheduler可能只是几行状态判断 不一定是独立组件。

在dag/并行节点/等待恢复 这类复杂情况下 才值得明确抽象出来

## Executor

实际的运行组件，来调用对应的能力，返回执行结果。 scheduler只是找到可运行的节点 需要由executor把节点描述转换成真操作。

所以scheduler 给executor是节点描述。

executor内部执行4步

1. 找到对应的handler：这个也是orchestration预先定义好的 根据不同的节点 设置不同的处理类（所以executor并非一个固定的执行逻辑 是一个统一入口+一组具体handler executor做分发的作用）
    
2. 准备执行输入：从state里提取出当前节点所需要的数据 由runtime统一注入
    
3. 调用节点具体的能力
    
4. 标准化 handler的结果 executor应该返回统一结果 然后runtime把结果写入state scheduler 再通过state判断后续可运行节点。
    

简单情况下 executor只是一个switch（node.type） 即可 只有节点类型、worker、并发和隔离请求增加 需要独立的executor抽象。

## 搭配

orchestration编排一次执行的流程：

router选择路由-->scheduler放行节点-->executor执行节点-->state记录进度