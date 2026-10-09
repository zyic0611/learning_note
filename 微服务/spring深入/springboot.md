学会了spring、springmvc、tomcat


就知道spring boot 就是实现自动装配 组装 启动 不需要自己大量配置的一个大框架 

它内部有 spring、spring mvc、tomcat 架构关系如下

```
                 Spring Boot
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
      Spring      Spring MVC    Tomcat
        │            │            │
     管理对象       处理Web请求     接收网络请求
        │            │            │
      IoC/DI      DispatcherServlet  TCP/HTTP
        │            │
        ↓            ↓
 UserService     UserController
```

客户端一次请求的生命周期

客户端
-> tcp
-> tomcat
-> spring mvc
-> controller
-> service