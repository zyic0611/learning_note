Token 本质是一串凭证： 

Authorization: Bearer abc123



典型的一个流程 ： 

用户登陆 服务器校验账号密码后 签发token

客户端保存token 请求的时候携带token 服务器每次验证token



token可以是

- 随机字符串：服务器收到后去 Redis 或数据库查询
- JWT：Token 自己携带用户信息，服务器可以直接验证

`Bearer` 的含义是：

> 谁拿到 Token，谁就能使用。