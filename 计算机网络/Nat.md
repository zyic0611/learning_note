Network Address Translation，网络地址转换 。

核心： 把内网 IP 转换成公网 IP，让多个内网设备共用一个公网 IP 上网。

当原始数据包访问 内网IP+端口的时候 如果经过NAT NAT就会返回映射关系
所以NAT这个设备有一个映射表。

路由器内部可以实现NAT 负责更改地址 并且记录映射关系 Nat的存在可以让 ipv4可以支持的数量更大