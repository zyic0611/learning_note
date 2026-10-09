Active profiles 设置有效配置文件 主要设置环境配置 

program augument 程序实参 也就是启动参数  一般是指定端口 适合临时覆盖端口 优先级高于 YAML 

Environment variables 环境变量 使用 System.getenv()的时候必须

working directory 工作目录 决定了相对路径从哪里开始 写 `$PROJECT_DIR$` 会自动解析为当前项目的根目录
 
VM options 控制jvm内存 系统属性