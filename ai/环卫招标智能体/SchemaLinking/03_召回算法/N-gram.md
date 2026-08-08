把连续的 N 个 Token（词、字或字符）作为一个整体。

其中：

- 1-gram = Unigram（一个）
- 2-gram = Bigram（两个）
- 3-gram = Trigram（三个）
- 4-gram = Four-gram

可以理解成一个滑动窗口，或者说是保留局部上下文的文本切分方式。


# 为什么要用 N-gram？

最大的作用就是：

**保留上下文。**

## 在 RAG / 向量检索中的应用

很多检索系统都会：

```
文本        │Tokenize        │生成 2/3-gram        │BM25        │倒排索引
```

例如：

```
Java 后端 高并发 Redis
```

生成：

2-gram

```
Java 后端后端 高并发高并发 Redis
```

3-gram

```
Java 后端 高并发后端 高并发 Redis
```

这样可以提高：

- Phrase Search（短语搜索）
- BM25 排序
- Hybrid Search（关键词 + 向量）
- RAG 的召回效果

---

# 为什么很多 RAG 都提到 2/3-gram？

因为**只按单个词（1-gram）检索容易丢失短语语义**。

例如：

```
machine learning
```

如果拆成：

```
machinelearning
```

搜索：

```
machine learning
```

可能会把：

```
machine repair
```

```
deep learning
```

都召回来。

如果建立：

2-gram：

```
machine learning
```

那么搜索精度会高很多。