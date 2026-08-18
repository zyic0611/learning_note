session 是服务器 为对应的用户保存的一份会话数据。 比如具体名字 登陆状态 权限

客户端一般在cookie里存储session_id 

服务端收到客户端的请求后 根据id 查找用户的具体信息。

一般在用户登陆以后 后端服务器会创建Session 会话数据。 然后生成唯一的SessionId作为标识 通过cookie交给浏览器。 浏览器请求后端 都自动携带session id



session不是强依赖cookie session id也可以放在url或者请求头中。