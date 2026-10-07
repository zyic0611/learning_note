Spring MVC 是一个基于 Servlet 的 Web 开发框架，它负责处理 HTTP 请求，并把请求映射到你写的 Controller 方法。



和tomcat的分工：

- Tomcat：负责“把 HTTP 请求接进来” 
- Spring MVC：负责“这个请求应该调用谁、怎么处理、怎么返回”



## 分析接口的相关注解

```java
@RestController
@RequestMapping("/user")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.getUser(id);
    }
}
```

@RestController 是springmvc的 组合注解 本质上是 

@Controller ： SpringMVC 控制器 会被扫描 注册为bean 管理

@ResponseBody ： 返回值会被序列化为json 写入1响应体 

@RequestMapping("/user")+@GetMapping("/{id}")：说明是get方法  路由为 GET /user/id



## 核心指责

当一个http请求 被tomcat解析后 （根据http请求里的ip和端口 比如localhost:8080 找到对应的服务 比如userservice的tomcat）形成request java对象 

然后 把网络请求交给springMVC 核心的 DispatchServlet 这一步的核心是根据 http请求里的后缀 也就是GET /user/123

**寻找到对应的 Controller** 然后调用具体方法

最后得到方法返回值 **包装成htttp响应返回**



## 本质

spring MVC 并不是一个应用  是一个基于 Servlet 的 Web 开发框架 它的核心组建及负责事情为：



- DispatcherServlet： 专门调度所有操作 核心调度的作用
- HandlerMapping 根据 URL HTTPMethod 找到对应的controller方法
- 调用具体的controller方法
- 解析http请求里的参数 绑定到java方法上
- json-java对象 的序列化和反序列化 
- controller 也是 springmvc的一部份 负责业务入口



