模型是“按 token 输出”，但 UI 不能“按 token 乱刷”，所以需要 buffer 做“整理后再显示”。

## token-level streaming

LLM 输出不是一句话 是一个一个token吐出来。

不能直接一个 token 就显示 会出现jitter抖动问题 中文会变成一列 很奇怪 。

并且如果tool call ，LLM输出的是json格式 ，逐token输出 前端会直接崩溃。

所以必须有缓冲区，

## buffer flush

决定什么时候推给前端 不是每个 token 都输出，而是**满足条件才 flush 一次**

- 策略1：按句子 flush
- 策略2：按标点 flush
- 策略3：时间窗口 flush（更高级）
- 策略4：token 数量 flush

实际工程一般是混合策略