## channel

通道 实现全双工通信。

在传统的 JAVA BIO 也就是 InputStream / OutputStream 中 数据流向 死 单向的 读写必须分开。

在channel中 既可以读 也可以写 也可以异步读写。

常见的：

- `SocketChannel`：对应 TCP 的客户端。
- `ServerSocketChannel`：对应 TCP 的服务端。
- `FileChannel`：对应文件 IO。



## Buffer

在NIO 中 所有的数据都是通过 `buffer` 处理的 。 chanel不会直接与字节打交到。 数据总是先读入buffer or 从buffer写入channel。

**三个核心指针：**

- Capacity 容量 ：当前buffer的固定大小 一旦分配不能更改。
- Position 位置：当前正在读或者写的索引位置
- Limit 限制：在写模式下 等于Capacity/ 在读模式下 表示最多能读取到多少数据。

**flip()方法**:

​	JDK原生的 `ByteBuffer` 读写是共用一个指针。  

​	读模式：数据写入buffer后 如果想把里面的数据读出来 必须调用一次 flip()方法。 把limit设置成当前的Position 再把Position归零。  

​	写模式：就是往position位置追加写。切换成写模式就需要把position设置为limit。

​	读写模式切换非常容易出错 所以Netty自己造 `ByteBuf` 读写双指针。



## Seletctor

对应Redis里的多路复用器。

作用是不断轮询注册在其上的`Channel` 如果某个channel发生了读写或者连接事件  selector就会挑出来处理。 所以一个单线程的seletor可以管理成千上万个连接。