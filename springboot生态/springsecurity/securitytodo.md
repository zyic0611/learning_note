# TodoList

### . 解决 JWT 的阿喀琉斯之踵：真正的“退出登录” (结合 Redis 黑名单)

- **痛点**：因为 JWT 是无状态的，只要签发了，在过期之前它就是永远合法的。如果用户点击了“退出登录”，或者管理员强制封禁了某个用户，**你怎么让这个依然没过期的 JWT 失效？**
- **开发方向**：引入缓存机制。用户退出时，把这个 JWT 丢进 Redis 的“黑名单（Blacklist）”里，并设置与 JWT 剩余存活时间相同的 TTL（过期时间）。修改 `TokenAuthenticationFilter`，每次验签成功后，再去 Redis 里查一下这个 Token 是不是在黑名单里。

### 2. 高并发与异步陷阱：上下文丢失 (ThreadLocal 穿透)

- **痛点**：你现在的 `SecurityContextHolder` 是基于 `ThreadLocal` 的，它和当前线程强绑定。如果业务开发人员在 Controller 里使用多线程池并发处理任务，或者加了 `@Async` 注解开启了异步线程，**子线程里是拿不到登录用户信息的！**
- **开发方向**：开发一个 `TransmittableThreadLocal` 或者提供一个 `ContextCopyingRunnable` 工具类，让主线程在派发任务给子线程时，能够自动把安全上下文“复制”过去。这是体现框架健壮性的高级特性。

### 3. 前端体验升级：双 Token 架构 (无感刷新)

- **痛点**：出于安全考虑，Access Token（访问令牌）的过期时间通常很短（比如 30 分钟）。如果用户填表单填了 40 分钟，一提交报错 401 让他重新登录，用户会崩溃的。
- **开发方向**：在 `/login` 接口返回两个 Token：短期的 `accessToken` 和长期的 `refreshToken`（比如 7 天）。当前端发现 `accessToken` 过期时，静默调用框架提供的新接口 `/api/auth/refresh`，用长期的 `refreshToken` 换取一个新的 `accessToken`。

### 4. 极致解耦：基于 URL 的动态 RBAC 鉴权

- **痛点**：现在的 `@MiniPreAuthorize("Admin")` 虽然好用，但权限是**写死在代码里**的。如果业务系统上线后，老板突然要求“把 `deleteUser` 接口的访问权开放给特定普通用户”，开发人员必须改代码、重新打包、重新发布。
- **开发方向**：除了 AOP 之外，在 `AuthorizationFilter` 中增加动态规则匹配引擎。系统启动时把“哪个 URL 需要哪个 Role”的映射关系加载到内存里，实现只要在后台管理系统中点点鼠标，就能实时改变接口的访问权限，完全不需要改代码。