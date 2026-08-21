## Recall@k 

召回率 ：看正确答案有没有被召回

公式：
	Recall@k= 前k个结果中 正确的相关文档 / 该query的全部相关文档

我会将 Recall@K 分层看。

- Retriever 关注 Recall@100 或 Recall@200，确保正确结果进入 reranker 候选集
- reranker 关注 Recall@5、MRR@10、nDCG@10，确保用户和 LLM 实际使用的前几名质量足够高。

一些细节：
1、 同一文档命中了多个chunk 只能算一次文档命中 聚焦于文档 不是chunk
2、如果知识库里答案没标注好 recall的分母不完整 指标会失真
3、不能只看recall 还要看排序 正确文档在第几个被召回

## Precision@K 

精确率： 前k个结果里 有多少是真的相关
公式：

​	前k个结果中 命中的文档数 / k

使用场景：
1、搜索结果页
2、RAG实际传给LLM的 Topk chunk
3、上下文窗口有限、无关文档代价高的情况



Recall 与 Precision 的关系：

​	天然有取舍关系 K增大 Precision通常下降 Recall通常提升。

所以二者没有谁更重要 主要要看当前目标是什么
- 初召回：优先Recall

- Rerank后 优先Prec 减少噪声

- 最终LLM 优先高Prec

  

## F1@K
公式是Prec和Recall的调和平均 表示的是两者的差距程度。

如果这个值很高 说明Recall和Precision差不多。 
如果低 就有两种情况 。噪声多或者遗漏信息。

一般会用 但不是核心首选指标。



## MRR@K

第一个正确结果排的多前
Mean Reciprocal Rank 平均倒数排名

RR= 1 / rank_first  
没有结果的话 RR=0

MRR就是所有query求mean

因为对首个正确结果很敏感 所以适合
-  每个query 有 唯一目标文档
-  用户一般只点击第一、第二点
-  RAG最后只使用最相关的一部分数据

局限性就是无法区分后续排序是否优秀
所以需要多个结果 多个证据的任务 就不能只看MRR

## MAP@K 

多个相关结果是否排名都靠前
Mean average precision 适合一个query 有多个二元相关文档

核心就是检索过程中 每出现一个相关文档 就计算 当前时刻当前位置的precision 就是P 检索结束后 对所有precision求平均 就是AP 最后对所有query求平均 就是MAP

它同时奖励 找到更多相关结果 并且把相关结果放在更靠前的位置

但是相关性 是二元的 相关or不相关 没有分级相关性排序 如果需要的话 更适合nDCG

## DCG/nDCG@K 

考虑相关程度的排序质量
nDCG的意思是 归一化折损累计增益  使用分级相关性 可以标识出 每个文档出现的位置和相关性 

本质是：在k个结果中 最有价值的内容是否被排到最前面 整体排序是否合理

## 证据级指标

因为文档命中 不代表chunk对  

额外指标： 
Evidence Recall@K
=被召回的证据 chunk 数 / 标注证据 chunk 总数
=前 K 个 chunks 中，包含支持答案的证据 chunk 的 query 比例
回答LLM是否拿到了真正支持答案的依据。

Context Precision
前 K 个送入 LLM 的 chunks 中，有多少确实与回答相关、能支持答案。
回答上下文有多少噪声
