当我们在浏览器点击按钮时，本质是前端 JS 向某个接口发起请求，比如 `http://localhost:8080/hello。 `

localhost:8080 是本机 IP + 端口。Spring Boot 启动时，会创建并启动内嵌的 Tomcat，由 Tomcat 真正监听 8080 端口，等待连接。

用户点击后，浏览器发起一个 HTTP 请求。这个请求本质是一段符合 HTTP 协议的报文，有文本形态（你能看懂的 GET /hello HTTP/1.1...），在网络上传输时会被编码成字节流（二进制）。

这里详细说一下HTTP请求 HTTP报文（请求/响应）有两种形式 
一种是文本形式：
GET /hello HTTP/1.1
Host: localhost:8080
User-Agent: Chrome

一种是字节流形式 按照编码要求 通常是 ASCII或者UTF-8 变成二进制形式 在网络上传输 因为跨网络传输必须编码成字节流。

浏览器和 Tomcat 是两个独立的应用，它们之间的数据传输涉及 TCP/IP 四层模型。访问 localhost 时，数据走回环接口，不出本机，但协议栈仍要走一遍。

经过四层协议栈后，Tomcat：

拆帧头、IP 头、TCP 头，拿到 HTTP 字节流

在应用层按 HTTP 协议解码 + 解析，得到结构化字段（方法、路径、头、体）

四层网络协议栈后 tomcat获取到了http报文 也就是结构化的文本形式 就像上面的get... 

把字段封装成 HttpServletRequest 这个 Java 对象  

这个对象就是 Tomcat 交给后续 Spring MVC（DispatcherServlet） 的产物。

所以 Tomcat 的核心作用可以概括为：
监听端口 → 接收请求 → 解析 HTTP（字节流 → 结构化字段 → Java 对象）→ 交给后续流程处理 → 把响应发回浏览器。