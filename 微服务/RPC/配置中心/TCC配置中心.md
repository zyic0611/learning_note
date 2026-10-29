TCC 是以 KV 为基础的动态配置管理系统。
配置按照服务、区域、配置空间和 key 组织，同一个 key 的历次修改形成版本链，所以可以版本管理。
平台负责修改、校验、灰度和发布配置。

Java 服务通过 TCC SDK 消费已发布配置。
本质在java后端服务中跑一个客户端 作为媒介去访问tcc服务端。
SDK就是software development kit 软件开发工具包。
SDK通过 Consul发现 TCC后端实例，将配置拉取到本地缓存，并通过定时刷新和 Listener让业务感知配置变化；后端异常时继续使用旧缓存。所以有容灾的能力。

consul接近于= nacos naming
tcc接近于= nacos config
