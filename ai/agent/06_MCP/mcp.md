MCP：

主要解决的问题是模型接入工具过于碎片化。 

工具方按照协议提供一个server 任何mcp支持的ai客户端都可以直接接进来使用 一次实现 到处使用。 采用标准的client-server架构 

协议定义三类能力 

- tools用于执行有副作用的操作 
- resouces 是只读数据 
- prompts是提示词模板。 

底层通信使用 JSON-RPC 2.0



## 底层通信

json-rpc 是轻量级的远程函数调用协议 

传输层支持两种方式

**stdio** 标准输入输出 server作为本地子进程运行 client通过管道通信。 适合本地工具 启动快 延迟低 

**streamable HTTP** server作为http服务部署在远程 client通过http连接通信。 适合部署在远端的工具服务 或者多个client共享一个server的情况。（老版使用http+sse 双断电 先版本单端点就行 更简单 短请求直接返回json响应 长请求则把http响应升级为sse流）



## 组成

角色层： host就是ai应用本身 client就是host里负责和server通信的模块 server是工具提供方实现的独立进程 一个host可以同时连接多个server



能力层：server暴露的三个能力 tools resouces prompts



协议层：底层通信 消息格式json-rpc2.0 传输方式：stdio和streamable http



