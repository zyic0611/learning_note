相似歌曲检索系统
这套相似歌曲搜索系统，不同于传统的基于文本（例如艺术家姓名或歌曲名称）进行搜索的系统，也不同于基于购买记录推荐歌曲的协同过滤系统。它的独特之处在于：直接以音乐波形本身（例如 WAVE 或 MP3 文件）作为输入。例如，当你不知道具体的艺术家或歌曲名称，但想要找到旋律或氛围与某首歌相似的歌曲时，这套系统就非常方便。

这一研究领域被称为“音乐信息检索”（Music Information Retrieval，简称 MIR）。

概述
本实验中参考的材料包括：

E. Pampalk: Computational Models of Music Similarity and their Application in Music Information Retrieval (PDF), Doctoral Thesis, Vienna University of Technology, Austria, March 2006.

B. Logan and A. Salomon: A Content-based Music Similarity Function, Technical report, Compaq Cambridge Research Lab, 2001.

这两篇论文分别是：第一篇是一篇条理清晰的关于相似歌曲搜索的综述论文；第二篇是Logan论文中描述的方法，该方法在Pampalk的论文中有所介绍。

Logan提出了一种利用语音局部特征的方法，其概念与基于视觉词的相似图像搜索非常类似。在相似图像搜索中，SIFT和SURF等局部特征被聚类以创建视觉词。然后，每幅图像都被表示为视觉词的直方图，并通过直方图交集计算直方图之间的距离。

在这个音乐项目中，我们使用梅尔频率倒谱系数（MFCC）的频谱特征 。对每首歌曲的MFCC向量进行聚类，将每首歌曲表示为一组聚类，然后使用动土距离（Earth mover's distance，EMD）计算聚类集之间的距离。EMD值相近的歌曲将被认为彼此相似。

尽管内容呈现方式和距离定义略有不同，但方法非常相似。现在，我们按照论文的步骤来尝试一下吧！

准备 MP3 文件
由于这是搜索相似歌曲，所以首先需要一个歌曲文件。一开始，尝试使用配乐，但效果并不理想。尝试了各种方法后，似乎有人声的歌曲比纯音乐效果更好。

我们整理了一份大约500首歌曲的歌单。当然，因为版权的原因，没办法分享这500首MP3文件数据，所以请用你自己的歌曲来实验吧。

这里所有歌曲都归类到一个名为“mp3”的文件夹中。如果有非 MP3 格式的歌曲，则需要将其转换为 MP3 格式，请在线搜索相关教程。

MFCC的提取
首先，从 MP3 文件中提取梅尔频率倒谱系数 (MFCC)，它是频谱特征。由于 MFCC 代表频谱的整体形状，可以将其理解为音色的代表。

以下Python脚本用于从指定MP3目录（mp3）中的所有MP3文件中提取MFCC数据，并将其保存到MFCC目录（mfcc）。该脚本使用sox和lame进行音频格式转换，并使用SPTK进行波形提取和MFCC提取（SPTK 提供了约 120 条用于语音分析的丰富命令）。

脚本运行需要安装sox和lame。


#coding:utf-8
import os
import sys

# mp3_to_mfcc.py
# usage: python mp3_to_mfcc.py [mp3dir] [mfccdir] [rawdir]
# 从目录中的 MP3 文件提取 MFCC

def mp3ToRaw(mp3File, rawFile):
    # 将 MP3 重采样为 16 kHz、32-bit
    os.system("lame --resample 16 -b 32 -a '%s' temp.mp3" % mp3File)
    # 将 MP3 转换为 WAV
    os.system("lame --decode temp.mp3 temp.wav")
    # 将 WAV 转换为 RAW
    os.system("sox temp.wav %s" % rawFile)
    os.remove("temp.mp3")
    os.remove("temp.wav")

def calcNumSample(rawFile):
    # 由于单个样本属于short型（2 byte），因此将文件大小除以 2
    filesize = os.path.getsize("temp.raw")
    numsample = filesize / 2
    return numsample

def extractCenter(inFile, outFile, period):
    # 求波形样本的数量
    numsample = calcNumSample(inFile)

    fs = 16000
    center = numsample / 2
    start = center - fs * period
    end = center + fs * period
    
    # 如果未满 period*2 秒，则缩小范围
    if start < 0: start = 0
    if end > numsample - 1: end = numsample - 1

    # 使用 SPTK 的 `bcut` 命令进行提取
    os.system("bcut +s -s %d -e %d < '%s' > '%s'" \
              % (start, end, "temp.raw", rawFile))

def calcMFCC(rawFile, mfccFile):
    # 采样频率: 16kHz
    # 帧长: 400样本
    # 帧移: 160样本
    # 通道数: 40
    # MFCC: 19 维 + 能量
    os.system("x2x +sf < '%s' | frame -l 400 -p 160 | mfcc -l 400 -f 16 -n 40 -m 19 -E > '%s'"
              % (rawFile, mfccFile))

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "usage: python mp3_to_mfcc.py [mp3dir] [mfccdir] [rawdir]"
        sys.exit()

    mp3Dir = sys.argv[1]
    mfccDir = sys.argv[2]
    rawDir = sys.argv[3]

    if not os.path.exists(mfccDir):
        os.mkdir(mfccDir)
    if not os.path.exists(rawDir):
        os.mkdir(rawDir)

    for file in os.listdir(mp3Dir):
        if not file.endswith(".mp3"): continue
        mp3File = os.path.join(mp3Dir, file)
        mfccFile = os.path.join(mfccDir, file.replace(".mp3", ".mfc"))
        rawFile = os.path.join(rawDir, file.replace(".mp3", ".raw"))

        try:
            # 转换 MP3
            mp3ToRaw(mp3File, "temp.raw")
        
            # 仅提取中间 30 秒并保存至 rawFile
            extractCenter("temp.raw", rawFile, 15)

            # 计算 MFCC
            calcMFCC(rawFile, mfccFile)

            print "%s => %s" % (mp3File, mfccFile)

            # 清理
            os.remove("temp.raw")
        except:
            continue
从整首歌曲中提取 MFCC 的计算量过大，因此在参考 Pampalk 论文的基础上，将分析范围限定在曲目的中间 30 秒。理想情况下，希望能从最能代表歌曲特征的部分（比如副歌？）提取特征，这类似于 SIFT 算法处理图像局部特征的方式，但目前还不确定具体该如何实现。

这些 MFCC 文件采用 SPTK 二进制格式。你可以使用以下脚本 print_mfcc.py 来输出文件内容。


#coding:utf-8
import struct
import sys
import numpy as np

# print_mfcc.py

if len(sys.argv) != 3:
    print "usage: python print_mfcc.py [mfcc_file] [m]"
    sys.exit()

mfccfile = sys.argv[1]
m = int(sys.argv[2])

mfcc = []
f = open(mfccfile, "rb")
while True:
    b = f.read(4)
    if b == "": break;
    val = struct.unpack("f", b)[0]
    mfcc.append(val)
f.close()

mfcc = np.array(mfcc)
numframe = len(mfcc) / m

if numframe * m != len(mfcc):
    print "ERROR: #mfcc:%d #frame:%d m:%d" % (len(mfcc), numframe, m)
    sys.exit(1)

mfcc = mfcc.reshape(numframe, m)
for i in range(len(mfcc)):
    print "\t".join("%.2f" % x for x in mfcc[i,])
下面我们试着以 20 维为一组，输出 西海情歌.mfc 的数据。


> python print_mfcc.py mfcc/西海情歌.mfc 20
-14.77  -8.78   -6.70   ...    3.45    7.37    1.44    2.80    22.29
-13.84  -9.71   -3.28   ...    -0.82   6.72    2.70    1.92    22.85
-15.45  -12.54  -7.64   ...    -5.64   3.45    2.31    6.03    22.67
-14.64  -10.72  -4.96   ...    -5.24   3.64    0.71    5.49    22.78
每一行代表单帧音频的 20 维 MFCC 向量（包含 19 个维度及能量值）。若采样频率为 16 kHz，帧移为 160 个采样点，且歌曲时长为 30 秒，则总帧数为 
 帧。换言之，《西海情歌》这首歌对应的 MFC 文件包含 3,000 行 20 维 MFCC 向量。

对于表示单首歌曲而言，这一向量规模过于庞大。

无法显示图片时显示的文字
从 MP3 文件提取特征指纹的过程
特征指纹计算
代表单首歌曲的特征向量规模过大，包含 3000 个 20 维向量（共计 
 个浮点数），因此可以使用向量量化算法进一步压缩信息。该算法本质上是对这 3000 个向量进行聚类，将相似的向量归为同一类。随后，假设每个聚类服从正态分布，我们计算其均值向量与方差-协方差矩阵，并将其作为新的特征。

用公式表示，歌曲 P 的特征如下：

 表示聚类数。

我们使用了常用的 k-means 聚类方法。聚类数设置为 16，与上述论文一致。换句话说，3000 个向量被划分为 16 个类。每个类的均值向量是一个 20 维向量，方差-协方差矩阵是一个 
 维矩阵。因此，通过


(20维均值向量 + 20×20维方差-协方差矩阵) × 16个类 = 6,720个浮点数
从而实现信息压缩。但在实际操作中，除了每个聚类的均值和方差外，还包含权重信息，即分配给每个类的向量数量。因此，最终结果实际上包含 6,736 个浮点数。与最初的 60,000 个数据相比，这已大幅减少。

下面的脚本用于将各站点的 MFCC 文件转换为特征文件。


#coding:utf-8
import os
import struct
import sys
import numpy as np
import scipy.cluster

# mfcc_to_signature.py
# usage: python mfcc_to_signature.py [mfccdir] [sigdir]
# 将每首歌曲的 MFCC 转换为特征标识

def loadMFCC(mfccFile, m):
    """加载 MFCC，其中 m 为 MFCC 的维度"""
    mfcc = []
    fp = open(mfccFile, "rb")
    while True:
        b = fp.read(4)
        if b == "": break
        val = struct.unpack("f", b)[0]
        mfcc.append(val)
    fp.close()

    # 每一行代表一帧的 MFCC
    # 转换为包含 numFrame 行和 m 列的矩阵格式
    mfcc = np.array(mfcc)
    numFrame = len(mfcc) / m
    mfcc = mfcc.reshape(numFrame, m)

    return mfcc

def vq(mfcc, k):
    """将 MFCC 向量集矢量量化为 k 个聚类"""
    codebook, destortion = scipy.cluster.vq.kmeans(mfcc, k)
    code, dist = scipy.cluster.vq.vq(mfcc, codebook)
    return code

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print "usage: python mfcc_to_signature.py [mfccdir] [sigdir]"
        sys.exit()

    mfccDir = sys.argv[1]
    sigDir  = sys.argv[2]

    if not os.path.exists(sigDir):
        os.mkdir(sigDir)

    for file in os.listdir(mfccDir):
        if not file.endswith(".mfc"): continue
        mfccFile = os.path.join(mfccDir, file)
        sigFile = os.path.join(sigDir, file.replace(".mfc", ".sig"))

        print mfccFile, "=>", sigFile

        fout = open(sigFile, "w")

        # 加载 MFCC
        # 每一行对应一帧的 MFCC 向量
        mfcc = loadMFCC(mfccFile, 20)

        # 通过对 MFCC 进行矢量量化来获取编码
        code = vq(mfcc, 16)

        # 计算每个聚类的数据点数量、均值向量和协方差矩阵，
        # 作为其特征标识
        for k in range(16):
            # 仅提取属于类 k 的帧
            frames = np.array([mfcc[i] for i in range(len(mfcc)) if code[i] == k])
            # 通过对每个 MFCC 维度求平均值来计算均值向量
            m = np.apply_along_axis(np.mean, 0, frames)  # 0 表示垂直轴
            # 计算 MFCC 维度间的方差-协方差矩阵
            sigma = np.cov(frames.T)
            # 权重（该类中的数据点数量）
            w = len(frames)
            # 以扁平化格式输出该类的特征
            # 单行包含 421 个值的序列：1 个权重、20 个均值向量元素以及 400 个方差-协方差矩阵元素
            features = np.hstack((w, m, sigma.flatten()))
            features = [str(x) for x in features]
            fout.write(" ".join(features) + "\n")
        fout.close()
输出结果：即歌曲的特征文件，包含16行数据；每一行包含421个数值，分别代表一个权重、一个20维均值向量以及一个20×20维的方差-协方差矩阵。

特征之间的距离与歌曲之间的距离
接下来，计算两首歌曲特征之间的距离。为此，我们采用“推土机距离”（Earth Mover's Distance）。

无法显示图片时显示的文字
从 MP3 文件提取特征指纹的过程
左侧展示了歌曲 P 的特征表示（signature），右侧展示了歌曲 Q 的特征表示。任务是计算歌曲 P 与歌曲 Q 之间的距离。关于 EMD（推土机距离）的详细解释，请参阅相关文献。当每个特征表示都是一个简单的向量时，可以使用欧几里得距离来计算各特征间的距离。然而，在本例中，每个特征并非向量，而是一个正态分布。因此，无法直接使用简单的欧几里得距离……

有一种名为“Kullback-Leibler 散度”（Kullback-Leibler Divergence）的指标，可用于衡量正态分布之间的距离。根据维基百科中关于 Kullback-Leibler divergence - Wikipedia的定义，针对正态分布 N1 和 N2（两者均由均值向量和方差-协方差矩阵定义），其 Kullback-Leibler 散度的定义如下：

这里，
 代表均值向量的维度。通常情况下，Kullback-Leibler 散度（KL 散度）不具备对称性；也就是说，
 和 
 的值并不相等。因此，如果直接使用该公式，从歌曲 P 到歌曲 Q 的距离与从歌曲 Q 到歌曲 P 的距离就会出现差异，从而导致使用不便。正因如此，多数论文采用了对称形式的 Kullback-Leibler 散度。

只需将翻转的距离加起来即可，这保持了对称性。对于Kullback-Leibler散度， R 准备了函数，但SciPy/NumPy中没有，所以我们自己来创建它。在Kullback-Leibler信息的定义中，常数乘数和常数项被省略，因为它们对于距离比较不是必需的。此外，行列式项被省略，因为它在使用对称 Kullback-Leibler 信息时被抵消。tr 是trace 的缩写，是矩阵对角线元素的总和。在脚本中，使用 diag() 提取对角线分量并使用 sum() 求和。


import numpy as np
import numpy.linalg

def KLDiv(mu1, S1, mu2, S2):
    """正态分布之间的 Kullback-Leibler 散度"""
    # 计算逆矩阵
    try:
        invS1 = np.linalg.inv(S1)
    except numpy.linalg.linalg.LinAlgError:
        raise;
    try:
        invS2 = np.linalg.inv(S2)
    except numpy.linalg.linalg.LinAlgError:
        raise;

    # 计算 KL Divergence
    t1 = np.sum(np.diag(np.dot(invS2, S1)))
    t2 = (mu2 - mu1).transpose()
    t3 = mu2 - mu1
    return t1 + np.dot(np.dot(t2, invS2), t3)

def symKLDiv(mu1, S1, mu2, S2):
    """对称 Kullback-Leibler 散度"""
    return 0.5 * (KLDiv(mu1, S1, mu2, S2) + KLDiv(mu2, S2, mu1, S1))
既然已经定义了正态分布之间的距离，接下来编写一个函数来计算 EMD（推土机距离）。在 R  中已有求解 EMD 运输问题的函数，因此使用了 rpy2 库，以便在 Python 中调用该R的函数。


import rpy2.robjects as robjects

# 用于在 R 中求解运输问题的程序包
# 由于它不是 R 的默认程序包，因此需要进行安装
# 在 R 中使用 install.packages("lpSolve") 进行安装
robjects.r['library']('lpSolve')
transport = robjects.r['lp.transport']

def calcEMD(sigFile1, sigFile2):
    # 加载该程序包
    sig1 = loadSignature(sigFile1)
    sig2 = loadSignature(sigFile2)

    # 计算距离矩阵
    numFeatures = sig1.shape[0]                 # 类数量
    dist = np.zeros(numFeatures * numFeatures)  # 距离矩阵（扁平格式

    for i in range(numFeatures):
        mu1 = sig1[i, 1:21].reshape(20, 1)   # 列向量
        S1 = sig1[i, 21:421].reshape(20, 20)
        for j in range(numFeatures):
            mu2 = sig2[j, 1:21].reshape(20, 1)
            S2 = sig2[j, 21:421].reshape(20, 20)
            # 计算特征 i 与特征 j 之间的 KL 散度
            dist[i * numFeatures + j] = symKLDiv(mu1, S1, mu2, S2)

    # 获取特征权重（第 0 列）
    w1 = sig1[:,0]
    w2 = sig2[:,0]

    # 根据权重和距离矩阵计算 EMD
    # 准备 transport() 函数所需的参数
    costs = robjects.r['matrix'](robjects.FloatVector(dist),
                                 nrow=len(w1), ncol=len(w2),
                                 byrow=True)
    row_signs = ["<"] * len(w1)
    row_rhs = robjects.FloatVector(w1)
    col_signs = [">"] * len(w2)
    col_rhs = robjects.FloatVector(w2)
    
    t = transport(costs, "min", row_signs, row_rhs, col_signs, col_rhs)
    flow = t.rx2('solution')
    
    dist = dist.reshape(len(w1), len(w2))
    flow = np.array(flow)
    work = np.sum(flow * dist)
    emd = work / np.sum(flow)
    return emd
现在已经能够计算两首乐曲之间的距离。接下来，实现搜索功能，找出与目标查询歌曲距离相近的歌曲。

相似歌曲搜索
由于搜索库中仅包含约 500 首歌曲，采用简单的线性搜索方法即可。系统会计算查询歌曲与库中所有 500 首歌曲之间的 EMD，并根据距离远近输出排序列表。此外，使用了 eyeD3（一个用于读写 MP3 标签信息的库）来提取并显示 MP3 文件中的艺术家名称。鉴于纯文本输出难以直观验证，系统还会生成包含嵌入式音频标签的 HTML 页面，以便更方便地查看搜索结果。

此处省略了前文提到的三个函数（KLDiv、symKLDiv 和 calcEMD），务必将它们添加到下方的脚本中。


#coding:utf-8
import os
import sys
import numpy as np
import numpy.linalg
import rpy2.robjects as robjects
from collections import defaultdict

# mir.py
# usage: python mir.py [sig file] [sig dir] [html file]
# sig file  : 待查询歌曲的特征文件
# sig dir   : 包含待搜索特征文件的目录
# html file : 用于输出搜索结果的 HTML 文件

# 输出与参数指定的特征文件
# 最相似的前 N ••首歌曲

def loadSignature(sigFile):
    """加载特征文件"""
    mat = []
    fp = open(sigFile, "r")
    for line in fp:
        line = line.rstrip()
        mat.append([float(x) for x in line.split()])
    fp.close()
    return np.array(mat)

def getArtist(mp3Path):
    """从 MP3 文件中提取艺术家信息"""
    import eyeD3
    try:
        tag = eyeD3.Tag()
        tag.link(mp3Path)
        artist = tag.getArtist()
    except:
        artist = "None"
    # 如果为空
    if artist == "": artist = "None"
    return artist

def makeHTML(ranking, htmlFile, N=10):
    """以 HTML 格式输出排名结果"""
    import codecs
    fout = codecs.open(htmlFile, "w", "utf-8")

    # 输出 HTML 头部信息
    fout.write('<!DOCTYPE html>\n')
    fout.write('<html lang="cn">\n')
    fout.write('<head><meta charset="UTF-8" /><title>%s</title></head>\n' % htmlFile)
    fout.write('<body>\n')
    fout.write('<table border="1">\n')
    fout.write(u'<thead><tr><th>排名</th><th>EMD</th><th>标题</th>')
    fout.write(u'<th>艺术家</th><th>音频</th></tr></thead>\n')
    fout.write(u'<tbody>\n')

    # 输出排序
    rank = 1
    for sigFile, emd in sorted(ranking.items(), key=lambda x:x[1], reverse=False)[:N]:
        prefix = sigFile.replace(".sig", "")

        # 将原始文件转换为 WAV 格式（用于 HTML 播放器）
        rawPath = os.path.join("raw", prefix + ".raw")
        wavPath = os.path.join("wav", prefix + ".wav")
        if not os.path.exists("wav"): os.mkdir("wav")
        os.system('sox -r 16000 -e signed-integer -b 16 "%s" "%s"' % (rawPath, wavPath))

        # 获取艺术家名称
        mp3Path = os.path.join("mp3", prefix + ".mp3")
        artist = getArtist(mp3Path)

        # 输出 HTML
        # 嵌入 HTML5 音频播放器
        audio = '<audio src="%s" controls>' % wavPath
        fout.write("<tr><td>%d</td><td>%.2f</td><td>%s</td><td>%s</td><td>%s</td></tr>\n"
                   % (rank, emd, prefix, artist, audio))
        rank += 1

    fout.write("</tbody>\n");
    fout.write("</table>\n")
    fout.write("</body>\n")
    fout.write("</html>\n")
    fout.close()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "python mir.py [sig file] [sig dir] [html file]"
        sys.exit()

    targetSigPath = sys.argv[1]
    sigDir = sys.argv[2]
    htmlFile = sys.argv[3]

    ranking = defaultdict(float)
    
    # 计算与所有其他曲目的距离
    for sigFile in os.listdir(sigDir):
        sigPath = os.path.join(sigDir, sigFile)
        emd = calcEMD(targetSigPath, sigPath)
        if emd < 0: continue
        ranking[sigFile] = emd

    # 按 EMD 值降序排列并输出结果
    N = 10
    rank = 1
    for sigFile, emd in sorted(ranking.items(), key=lambda x:x[1], reverse=False)[:N]:
        print "%d\t%.2f\t%s" % (rank, emd, sigFile)
        rank += 1

    # 按 EMD 值升序排列，输出前 10 项的 HTML 内容
    makeHTML(ranking, htmlFile, N)
实验
让我们选取几首曲目作为查询对象，来看看结果如何！

如果不亲自试听音频，恐怕很难直观理解这些结果，因此需要制作一个 HTML 页面，可以从中播放每首曲目中间部分的 30 秒 WAV 片段。结果列表的第二列显示了相对于查询曲目的 EMD 值。排名第一的结果正是查询曲目本身。

输出结果的样式如下（此处对歌曲名做了处理，仅展示实验效果）


python mir.py sig/西海情歌.sig sig ai_ha_katu.html
1    20.00    西海情歌.sig
2    51.51    WILL.sig
3    51.67    Vermillion.sig
4    52.30    Good Day.sig
5    52.51    zzzz.sig
6    53.26    xxx.sig
7    53.50    tyree.sig
8    53.65    ttttt.sig
9    54.25    mmmm.sig
10    55.17   e4ree.sig
总结
本项目构建了一个用于检索相似音乐曲目的系统。该系统较为基础，仅依赖于 MFCC 特征。显然，系统仍有很大的改进空间，例如可以纳入旋律和节奏方面的相似度考量。此外，若要在海量音乐库中进行检索，则需要采用并行处理技术或更高效的算法；事实上，这些方面很可能才是实际应用中面临的主要挑战。