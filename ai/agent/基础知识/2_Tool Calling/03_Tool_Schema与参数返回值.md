Tool Schema本质上是工具对外暴露的结构化契约 
模型根据它来生成候选参数  
runtime根据它来校验参数结构 
开发者根据它来维护工具接口

eg：

```
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "需要查询天气的城市名称"
    },
    "date": {
      "type": "string",
      "format": "date",
      "description": "查询日期，格式为 YYYY-MM-DD"
    }
  },
  "required": ["city", "date"],
  "additionalProperties": false
}
```

定义了输入必须是对象 允许两个字段 并且都是必填。 不允许生成其他的字段。


## 三个作用

### 给模型提供生成边界

让模型知道 
- 字段叫什么
- 类型是什么
- 哪些必填
- 允许哪些取值



### 给runtme提供结构校验标准

runtime可以检查
- 是否缺少必填字段
- 是否出现未知字段
- 类型是否正确
- 数值是否超出类型范围
- 枚举是否合法

但是通常不能判断 业务和权限

### 形成稳定接口

只要对模型暴露的schema不变 agent的上层逻辑就不需要改变 就可以替换工具的供应商接口。 因此Tool Schema也是工具的稳定抽象边界。

## 核心字段

### type

定义数据类型 

object
array
string
integer
number
boolean
null

### properties

定义对象的允许的字段

### required

定义必须提供的字段

### additionalProperties

是否允许模型生成未定义字段 。 

大部分业务是不允许的。因为就算这些字段不去执行，也容易造成协议歧义和安全风险。

### enum

type:
enum: "a","b","c"

在取有限个值的时候 优先使用枚举 更稳定

可以减少不同表达的不稳定

### 数值范围

type:integer
maximum:
minimum：

适用于人数 分页大小 重试次数 评分 数量

业务限额仍应由后端验证 不能只依赖schema

### 字符串格式

type:string
format:
- data
- date-time
- email
- uuid

不同模型api和schema实现 对format的强制程度可能不同 因此runtime还需要验证

### 数组

type：array
items：{
	type:string 描述数组里面的数据类型
}
minItem:1 最小元素个数
maxItem: 20

必须限制数组长度 避免llm一次生成过多资源


## 参数来源

### llm生成参数

来自用户的自然语言 需要llm理解后生成参数

### runtime注入参数

来自可信的运行环境 不应让模型生成
比如 用户id 时间 traceid 会话id 访问令牌 权限角色 token等等

### 工具内部派生参数

根据其他数据来计算 但不需要暴露给llm。 一般是只需要内部理解即可。

比如 llm提供城市为上海 工具内部映射为city_code=112341

没必要让llm记忆或生成内部城市编码。

## 常见参数设计

### 时间：

一般不用自然语言 描述 

转换成明确结构 
- start_at:具体时间
- end_at：具体时间

时间参数要明确：
- 绝对时间还是相对时间
- 是否包含时区
- 是一个时间点 还是时间范围

### 金额

不推荐使用浮点数 会存在精度问题

一般转换成 整数 并且说明货币单位 币种


## 返回值 toolresult

{
	status:代表工具执行状态
	data:工具返回数据
	error: 工具执行 结构化错误错误 通常包含错误信息 错误类型 是否可重复 
	metadata: 不是核心业务数据 一般帮助理解结果
	warnings: 结果可用 但是存在注意事项
}

## 总结

Tool Schema 是模型生成候选参数和 Runtime 校验输入结构之间的接口契约。高质量 Schema 应使用明确类型、必填字段、枚举、范围和 `additionalProperties: false` 降低生成歧义。只有需要模型理解用户意图的参数才应暴露给模型；用户身份、租户、权限、访问令牌和幂等键应由 Runtime 从可信环境注入。工具输出也应有稳定 Schema，通过 `status、data、error、metadata、warnings` 区分业务数据、错误和来源信息。输入 Schema （是对工具允许的参数做结构化定义 约束tool call里的argument 参数）通常约束模型输出，输出 Schema （是对工具执行后返回结果的结构化定义）则约束工具实现，两者都需要 Runtime 验证。