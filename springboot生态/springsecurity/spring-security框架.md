# spring-security框架

## 责任链模式 (Chain of Responsibility)

核心是filter接口 构建某个过滤器一定要实现filter接口 重写其中的doFilter方法。该方法需要传三个参数 ServletRequest servletRequest, ServletResponse servletResponse,FilterChain chain 

客户端请求 客户端答复  过滤链。

然后在内部编写过滤条件。

一般采用4层过滤链结构 

第一层是上下文清理 使用tryfinally机制 保证请求结束后强制清楚ThreadLocal 防止tomcat线程复用导致的内存泄漏和污染。

第二层是全局异常转换器 负责捕获后续所有的filter抛出的异常 转换成json格式。

第三层是 token校验过滤器 提取token 封装为authentication对象（未认证） 交给manager去校验。 校验成功 就把信息存入上下文。

第四层是 兜底校验 如果是访问的是白名单接口 直接放行 其他的：如果此时第三层发来的authentication对象仍然是未认证状态 则token无效 不放行。

这几层过滤层的组装 通过FilterChainProxy来组装。 这个类要维护一个变量 虚拟过滤链条。也就是一个List<Filter>的变量。

所以在FilterChainProxy的构造函数中 就要把所有层add到虚拟过滤链中 并且有些层需要的一些参数 比如全局异常转换器 需要传入队不同异常的handler 比如 401 403的。还有token校验filter需要传入 manager。 而manager需要providerlist 所以也要初始化providerlist 传入初始化manager。 也就是把所有的东西都初始化。

虚拟过滤链条内部是一个递归的形式 所以最早入栈的过滤器最后出栈 所以上下文清理能最后再清理 全局异常转换器能捕获后面层的异常 所以不能用for循环去做过滤 丧失了递归的属性。

最后 由于上面那些类都是普通类 必须写一个filterconfig配置类 自定义配置规则 注册一个过滤器 把过滤规则放入 然后配置。

## **策略模式 (Strategy Pattern)** 

首先很重要的是 校验的东西 要被包装成authentication凭证对象。

authentication有三个核心字段

1. credentials 凭证 比如密码 token

2. principal 	当事人  认证前可能是username 认证后 可能是 userdetail 所以这两个都是object类

3. authenticated 是否被认证 boolean变量。



然后有一个manager大队长 他内部要传入一个provider list 检票员的list。 

大队长的作用就是遍历 看哪个检票员能处理这个authentication。 分发给providers。

provider是一个接口 有两个方法 一个是检验 一个是判断某个类的属性能不能验票。

provider才是实际执行验票的 比如对于token校验 首先重写检验方法。 再重写校验类方法 。

所以manager只要调用每一个provider的检验类方法 传入要校验的对象进去 哪个为true 就调用哪个provider。



