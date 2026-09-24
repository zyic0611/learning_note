# ES基本概念

- index 索引 相当于把医生表的信息存进去 存所有医生的治疗
- document 文档 相当于表里的每一行 但是他是json格式 json格式就必然有key value
- fiedl 字段 也就是json里的key
- mapping 映射规则 是最重要的  不仅规定数据类型 还规定了这个字段被搜索的规则 也决定了分词



## mapping

- keyword类型 需要完全匹配 不需要分分词
- double 数字类型 可以range过滤
- text类型 允许被分词 中文常用分词器为IK分词器 分词后存入倒排索引里

## analyzer分词器的工作原理

1. 字符过滤 去掉html标签等没用的东西 过滤成纯文本
2. 分词 tokenizer  分词器内部有词库 根据词库 分词
3. 词元加工：
   - 停用词过滤 过滤 的 了 是等词
   - 同义词替换 如果配备专业同义词典 一个词可能会被关联上别的相似词
4. 产生倒排索引 key为词 value为index里的document id 表。

## 跨字段匹配 Match Term

Match

- 适合模糊查询 搜索框模糊搜索
- 拿到词汇后 会先分词 比如分成2个词
- 然后去倒排索引里面去查找这两个词对应的document
- 适用于Mapping中定义为text的字段

term

- 适用于 下拉框 精确选择
- 不会分词 会去倒排索引里整体查询该词
- 适用于maaping中定义为keyword 树枝 布尔值

陷阱： 对一个text类型的字段使用 term查长句子 查不到 因为text类型肯定被切碎了 倒排索引里存放的是切碎的词。



## Range与 Filter过滤器

range

是实现范围查询的 数字或者时间

查询：

query上下文

 是计算分数的 比如match搜高血压 不仅在倒排索引里找出医生的documentId 

还会使用BM25算法 计算id和词的相关性得分:计算这个词在这个document里出现了多少次【词频TF 以及在所有document库里多稀有【逆文档频率IDF 然后算出谁最匹配 然后按得分排序  还有文档的长度 也就是一个词在越短的document里出现 权重越大

这个过程非常消耗CPU 性能低 并且每次查询的关键词和得分都不同 ES无法缓存Query的结果

filter 上下文 

不计算分数 只回答yes/no 当term等值查询或者范围查询的时候 他不需要计算分数。并且es会将filter结果放在内存中 下次患者加了这个筛选条件 es直接从内存中返回  实现毫秒级筛选.

并且为filter在倒排索引中的查询结果生成一个紧凑的数据结构存储 bitset 位图数组全部都是01二进制存储。

下次使用到这个筛选条件 直接去内存里去bitset数组 有多个filter 则底层直接对多个bitset进行and操作



**面试话术总结：** “在处理跨字段检索时，我将不需要模糊匹配和算分的条件（如科室、价格区间）全部放入 Filter 上下文。利用 ES 底层的 Bitset 缓存机制，避免了无意义的 BM25 算分开销，同时大幅减少了磁盘 I/O，从而支撑了海量数据的毫秒级筛选。”



## Bool query

多条件查询 组合查询 使用Bool Query包裹。 4个关键字

- must 必须满足 相当于AND 使用Match 并且参与算分
- filter 必须满足 但是不计算分数 一般适用于不需要模糊查询的字段 比如范围查询 等值查询
- should 最好满足 相当于OR 
- must_not 相当于NOt 排除

## highlight 高亮字段

## DSL语言

是ES底层的语言 是json格式的

```json
GET medical_experts/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "specialty": "高血压" } } 
      ],
      "filter": [
        { "term": { "department": "心血管内科" } },
        { "range": { "consultation_fee": { "lte": 200 } } }
      ]
    }
  },
  "highlight": {
    "fields": { "specialty": {} }
  }
}
```

所以外部记住 must必须是必须满足的条件 参与打分  所以内部一般写match 适合模糊查询 分词去倒排索引里查找 filter是 必须满足 但是不参与打分 所以内部适合写term 等值查找 range 范围查找

must不走缓存 参与算分 filter走缓存 不参与算分

## 倒排索引 数据结构

1. Posting List 倒排表 
   - 是记录documentId的数组 
   - 数据量一般很大 所以只能存放在Disk里 
   - 为了节省空间 es会使用咆哮位图算法压缩
2. Term Dictionary 词典
   - 把分词器切分好的词汇 按字典序大小排序好
   - 很大 只能存放在disk 
   - 问题：虽然有序 可以用二分查找 但是在disk上进行多次二分查找 磁盘I/O 会成为性能瓶颈
3. Term Index 词典索引 内存里的神级结构Fst
   - 每次去disk里查term dictionnary 太慢 也不能把其放进内存 会OOM
   - 在内存中建立一个Term Index 作为Term Dictionary的目录 采用FST的数据结构
   - 理解为是极致压缩的前缀树 甚至可以共享后缀相同的路径
   - 搜索词 先去内存的FST里 找到这个词的大致前缀位置
   - fst会提供磁盘偏移量 精准去disk里的term dictionary 顺序读取一点点就找了完整词汇
   - 然后拿到对应的value 数组