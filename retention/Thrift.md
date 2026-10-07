## 1. Thrift 是什么

Thrift 是一个 RPC 框架，让客户端能够像调用本地方法一样调用远程服务。

它主要提供：

- IDL：定义远程方法、参数、返回值和异常。
- 代码生成：生成客户端代理、服务端接口及 Processor。
- 序列化：把请求和响应对象转换成可传输的字节。
- 网络通信：发送请求、接收响应。
- 服务端分发：找到对应方法并调用业务实现。

## 2. 一次 RPC 调用

```text
客户端业务代码
-> 调用生成的 Client 方法
-> 序列化请求参数
-> 通过网络发送
-> 服务端 Processor 反序列化
-> 调用 Iface 的业务实现
-> 序列化返回值
-> 客户端反序列化并获得 Response
```

客户端看到的是：

```java
DeleteResponse response = client.HardDelete(request);
```

但 `client` 是生成的远程代理，不是真正的业务实现。

## 3. 项目中的代码关系

### 接口合同

文件：

```text
retention-spi/src/main/thrift/ad/data_retention_thrift_service.thrift
```

其中定义：（需要RPC的方法 都需在这里定义）

```thrift
service BizDataRetentionService {
DeleteResponse HardDelete(1: DeleteRequest request)
RestoreResponse Restore(1: RestoreRequest request)
VerifyResponse Verify(1: VerifyRequest request)
}
```

### 开启服务端

`RetentionThriftServiceApplication` 使用：

```java
@EnableThriftServices(
basePackages = {
"com.bytedance.ad.data.retention.thrift_service.thrift"
}
)
```

它会启动 Thrift 服务端，并扫描指定包中的 `@ThriftService` Bean。
### RPC 实现入口

```java
@ThriftService
public class RetentionThriftService
implements BizDataRetentionService.Iface {
}
```

- `BizDataRetentionService.Iface`：根据 Thrift IDL 生成的 Java 接口。
- `RetentionThriftService`：项目编写的 RPC 接入层。
- `HardDeleteService` 等：真正的本地业务服务。

典型调用关系：

```text
Thrift Processor
-> RetentionThriftService.HardDelete()
-> 参数校验和对象转换
-> HardDeleteService.hardDelete()
```

## 4. 反序列化在哪里

反序列化不在 `RetentionThriftService` 中手写。

Thrift 生成的 `BizDataRetentionService.Processor` 负责：

1. 从网络协议读取参数。
2. 反序列化为 `DeleteRequest` 等 Java 对象。
3. 调用 `Iface` 的对应方法。
4. 序列化返回结果。

生成代码通常位于：

```text
retention-spi/target/generated-sources/thrift/
```

生成命令：

```bash
./mvnw -pl retention-spi generate-sources
```

### 本项目的 `.thrift` 文件

主要服务定义文件：

```text
retention-spi/src/main/thrift/ad/data_retention_thrift_service.thrift
```

需要新增 RPC 方法时，先在其中的 `BizDataRetentionService` 中定义请求、响应和方法，再执行生成命令。

### 代码生成是什么意思

生成命令的输入是 `.thrift` IDL 文件，不是已有的 Java 本地方法。

例如，在 IDL 中定义：

```thrift
service BizDataRetentionService {
DeleteResponse HardDelete(1: DeleteRequest request)
}
```

执行 `generate-sources` 后，Thrift Maven 插件会根据这份定义生成 Java 通信框架代码，主要包括：

- `DeleteRequest`、`DeleteResponse` 等请求和响应 DTO。
- `BizDataRetentionService.Iface` 服务端接口。
- `BizDataRetentionService.Client` 客户端代理。
- `BizDataRetentionService.Processor` 服务端协议解析和方法分发代码。
- 参数读写、结果读写及序列化相关辅助代码。

### 生成代码的关系

- `Iface`：服务端接口，服务端实现对应方法。
- `Client`：客户端代理，调用同名方法发起 RPC。
- `Processor`：读取方法名和参数，反序列化后调用 `Iface`，再序列化返回值。
- DTO：数据传输对象，例如 `DeleteRequest` 和 `DeleteResponse`，用于承载请求和响应数据。

调用关系：

```text
Client 方法
-> 序列化方法名和请求 DTO
-> Processor 反序列化并分发
-> 调用 Iface 的实现
-> 返回响应 DTO
```

客户端需要使用匹配版本的生成代码，并建立 Thrift 连接后才能调用新增方法。

生成目录位于 `target` 下，属于构建产物，不应手动修改。修改 `.thrift` 文件后，应重新执行生成命令。

### 本地方法不能直接生成 Thrift 接口

假设项目中已经存在本地业务方法：

```java
localService.delete(userId);
```

执行 `generate-sources` 不会扫描这个方法，也不会自动将它发布成 RPC 接口。需要依次完成：

1. 在 `.thrift` 文件中定义请求、响应和远程方法。
2. 执行 `generate-sources`，生成 `Iface`、`Client`、`Processor` 和 DTO。
3. 在 `RetentionThriftService` 中实现生成的 `Iface` 方法。
4. 在该实现中校验和转换参数，然后调用已有的本地业务方法。

示意代码：

```java
@Override
public DeleteResponse HardDelete(DeleteRequest request) {
localService.delete(request.getUserId());
return new DeleteResponse();
}
```

因此，代码生成只负责把 IDL 合同转换为客户端和服务端通信所需的框架代码；业务逻辑及其与本地 Service 的连接仍需手动实现。

## 5. RPC 接入层的职责

`RetentionThriftService` 一般负责：

- 参数校验。
- 监控和日志。
- Thrift DTO 与内部业务对象转换。
- 调用本地 Service。
- 将业务结果或错误包装成 Thrift Response。

它不负责手动处理网络字节和序列化协议。

并非所有本地方法都需要放在这里。只有需要通过该 Thrift 服务对外暴露的方法，才需要定义在 IDL 并实现 `Iface`。

## 6. 返回值与异常

需要区分两类失败：

- 业务失败：通常通过 `BaseResp.statusCode/statusMessage` 返回。
- RPC 失败：连接失败、超时、协议错误等，通常抛出 `TException` 或框架异常。

因此，RPC 方法正常返回不代表业务一定成功，调用方仍需检查业务状态码。

## 7. 新增一个 Thrift 接口

1. 确认需要对外暴露的本地业务能力，并设计 RPC 请求和响应。
2. 在 `.thrift` 文件中增加请求、响应和 service 方法。不能只新增 Java 本地方法。
3. 保持接口兼容：不要修改已有字段编号或复用废弃编号；新增字段优先使用 `optional`。
4. 执行 `./mvnw -pl retention-spi generate-sources`，根据 IDL 生成 Java 代码。
5. 在 `RetentionThriftService` 中实现生成的 `Iface` 方法。
6. 在实现中完成校验和对象转换，并调用本地业务 Service。
7. 补充接口层和业务层单元测试。
8. 执行 `mvn verify`，通过编译、测试、覆盖率和静态检查。
9. 调用方更新 SPI 版本或重新生成代码后，通过生成的 Client 调用。

其中，第 4 步只生成通信框架代码，不会生成第 5、6 步中的业务实现。

## 8. 定位一个 Thrift 接口

```text
@EnableThriftServices
-> 查看 basePackages
-> 搜索 @ThriftService
-> 查看 implements XxxService.Iface
-> 找到对应的 @Override 方法
-> 继续追踪它调用的本地 Service
```

## 9. 核心结论

- `.thrift` 是客户端和服务端共同遵守的接口合同。
- 客户端调用的是生成的代理对象，看起来像本地方法，实际是网络请求。
- 请求参数、返回值和声明异常都可以通过 Thrift 传输。
- 序列化、反序列化和方法分发由生成代码及框架完成。
- `RetentionThriftService` 是 RPC 接入层，不是序列化实现层。
- 只有通过该 Thrift 服务暴露的请求才走这个入口；HTTP、MQ 和定时任务有各自入口。
