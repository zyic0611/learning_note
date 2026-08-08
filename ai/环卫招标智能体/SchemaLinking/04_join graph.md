连接图使用**无向图 (Undirected Graph)** 的数据结构来直观地表示数据库中多张表之间的关联关系。

- **节点 (Vertices/Nodes)** 代表数据库中的**表 (Tables)** 或查询语句中的表别名。

- **边 (Edges)** 代表表与表之间的**连接条件 (Join Conditions)**，通常由外键 (Foreign Key) 或 SQL 语句中的 `ON` 子句来定义。

## 物理模式连接图

Schema Join Graph 

基于数据库物理建表语句（DDL）自动生成的全局网络图。它描绘了整个数据库系统内所有表通过外键或逻辑关联构成的完整网络。

**核心作用**：在构建 **NL2SQL (自然语言转 SQL)** 系统时，大模型经常会在多表跨度查询中产生“幻觉”（例如强行把两张没有关系的表 JOIN 在一起）。通过将全局 Schema 抽象为 Join Graph 注入到 Agent 的工作流中，Agent 可以利用**图算法（如最小生成树/Steiner Tree 算法）\**自动寻找从目标 A 表到目标 D 表的最短合法连接路径，从而实现精准的\**模式链接 (Schema Linking)**。

## 查询连接图

Query Join Graph

这是由用户输入的一条具体 SQL 查询语句所动态生成的局部图。它仅包含该条 SQL 中涉及的表和 JOIN 条件。

**核心作用**：传统数据库**优化器 (Optimizer)** 会对其进行解析。优化器通过遍历 Query Join Graph，结合各表的统计信息（行数、索引），利用动态规划或贪心算法来决定最优的**连接顺序 (Join Order)**（例如是生成左深树 Left-Deep Tree 还是稠密树 Bushy Tree），以此最小化内存开销并避免产生灾难性的笛卡尔积。



## 最短Join路径

指的是为了将两张或多张在物理层面上没有直接外键关联的表拼接在一起，所需要经过的**最少中间表**或**最低计算成本**的连通路径。

大语言模型通常擅长识别出用户问题中涉及的实体（例如“用户”和“商品”），但极度缺乏数据库内在拓扑的先验知识。如果强制大模型自己去“猜”表与表之间的关系，往往会生成 `Users JOIN Products ON Users.id = Products.user_id` 这种引发 SQL 报错的“幻觉”代码。

因此，在 Agent 的工程工作流中，必须在模型生成 SQL 之前，通过图算法在后台自动推导出一条**最短 Join 路径**（例如：`Users -> Orders -> OrderItems -> Products`），并将其作为上下文 (Context) 注入到 Prompt 中。

### 依赖算法

BFS 

Dijkstra 

Stenier Tree