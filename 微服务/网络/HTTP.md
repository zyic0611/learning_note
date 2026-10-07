
HTTP 负责定义应用层消息的 语义和格式 。

规定应用层 发出的消息 收到的消息 都是什么格式的。 规定里面的字节代表是什么 以及请求和响应 需要以什么格式组织。

比如：

```
POST /users HTTP/1.1
Content-Type: application/json

{"name":"Tom"}

```

POST 请求方法
/users 资源路径
Content-Type 请求头
{}json  请求体
200/400/500 响应状态码

这些都是http定义的规则 