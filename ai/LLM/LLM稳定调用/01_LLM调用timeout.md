

如果一个用户请求 agent线程 然后调用llm 等待了5分钟 会导致 线程一直被占用 。 如果100个用户 就是100个线程被占用。

最后结果： 线程池被耗尽 服务不可用。 所以必须设置 timeout超时时间限制。

## timeout类型

1.连接超时 connect_timeout

建立TCP连接时间超时 也就是客户端连接不上llm服务器

一般设置为3s 超过3s连接不上llm服务器 返回失败

2.读取超时 read_timeout

连接成功了 但是llm生成的token迟迟没有返回

3.总超时 total_timeout

整个调用期间 耗时限制