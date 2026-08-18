cookie 就是 浏览器保存的一个凭证 每次请求后端服务器的时候 带过去。

服务器通过响应头 让前端客户端 也就是浏览器里保存 cookie 内容一般是一个键值对 Cookie：user_id=xxx

Cookie里可以保存 登陆标志、个性化设置等等。大小一般只有4KB 不能存大量的数据。



最常见的登陆方案 就是cookie带着session id 去服务器找具体的session