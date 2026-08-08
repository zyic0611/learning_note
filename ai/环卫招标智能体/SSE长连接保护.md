## SSE本质

Server-Sent Events 本质是 HTTP 长连接 + 服务器持续往同一个 response 写数据

Client  ───── HTTP request (keep-alive) ─────>  Server
Client  <──── stream chunk chunk chunk chunk ─── Server

客户端简历http连接 服务端发chunk

关键点：

- 不是 WebSocket（不能双向实时）
- 是 HTTP response 一直不关闭

## SSE断掉

“代理 / Nginx idle timeout”就是核心问题。

### idle timeout

很多中间层会认为：这个连接好久没数据 → 可能死了 → 我帮你断

比如nginx这种中间件 默认超时时间大概60～120s 超过这个时间 server都没有chunk输出 连接会被杀死

### TCP keepalive ≠ HTTP keepalive

也就是底层网络没死 不等于 业务连接没死

```markdown
应用层：HTTP / SSE（你写代码的层）
-----------------------------------
传输层：TCP（操作系统管）
-----------------------------------
网络层：IP（路由器管）
```

TCP keepalive  属于：操作系统层  如果一条 TCP 连接“很久没动静”，操作系统会偷偷发包问一下。

- 很慢（几十分钟级别）
- 默认不开或很晚才触发
- 不关心 HTTP 内容
- 只是“底层网络活没死”

举例  浏览器连着服务器：TCP连接建立了 但 30 分钟没数据 操作系统可能才会： 发一个探测包。

HTTP keepalive / SSE 心跳 属于应用层 是真正能控制的 是主动告诉中间件 该应用还在工作。 



## SSE 心跳包

定期发“非业务数据”，让连接保持活跃

心跳频率（关键工程参数）  一般：10s ~ 30s 一次 

- 心跳不能太频繁（浪费带宽）
- 不能和业务 token 混淆

## 请求总时长 deadline 全局超时控制

本质是 即使 SSE 不断流，也不能让请求无限挂着

原因：

因为 Agent 有可能：

- 卡在 tool call
- API 死循环
- LLM hang

超时策略一般不是直接断 一般是分级处理

- 0-60 正常stream

- 60-120 警告/降级

- \>120 断掉 反馈