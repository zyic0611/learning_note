Network Address Translation，网络地址转换 。

核心： 把内网 IP 转换成公网 IP，让多个内网设备共用一个公网 IP 上网。

路由器会维护一张“映射表”：
`内网 IP + 端口` ↔`公网 IP + 端口`

nat的存在可以让 ipv4可以支持的数量更大