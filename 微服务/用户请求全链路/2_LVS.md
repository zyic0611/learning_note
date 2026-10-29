DNS解析出来的ip 实际上是VIP 虚拟IP。
虚拟IP指向LVS集群。 而不是直接指向某台Nginx的IP。
LVS管理着整个Nginx集群。 内部有调度算法 把请求调度到具体的nginx机器。
因为一台Nginx大概抗 5w～10w QPS 。能力有限 所以必须堆集群 但是用户请求只认ip 所以必须用lvs管理集群 提供一个虚拟ip。


LVS只接受上行流量 也就是用户发过来的请求 比如用户的TCP SYN包。
他不需要解析包 瞬间转发所以单台LVS可以抗的起百万QPS。

当lvs选定nginx机器后 就把请求包里的mac地址改成nginx （DR直接路由模式）后续的响应 nginx直接返回用户。
只有请求流量经过一次lvs 响应流量就不经过了。 请求流量一般很小 响应流量一般很大。 所以lvsqps高

并且lvs可以容灾 如果直接指向nginx机器的话 nginx机器挂的话 dns直接失效了。 指向lvs lvs还可以做自动摘除失效的nginx实例 所以lvs就类似于一个注册中心。

