# -*- coding: utf-8 -*-
"""回源校验：检查章节文件里每段引语是否真实存在于语料中。
用法: verify_quotes.py <章节文件>
规则：中文连续片段（>=8 字）必须能在语料中原样找到。
先按引号切出引语，再对两侧做同样的归一化（去空白/markdown符号/引号字符）后比对。
"""
import io
import os
import re
import sys

# 语料默认路径（原作者本机）；移植后请用 --corpus PATH 或环境变量
# HUANHAI_CORPUS 指向自己的「总合集-全量.md」。
CORPUS = r'H:\幻海迷局文章\幻海迷局\大合集\总合集-全量.md'
# 归一化时剔除的字符：空白、markdown 强调/标题符、各类引号
DROP = r'[\s*　\'’‘“”「」『』]'
# 用于从章节中提取引语的成对引号
PAIRS = [('「', '」'), ('“', '”')]


def norm(s):
    return re.sub(DROP, '', s)


def resolve_corpus(argv):
    if '--corpus' in argv:
        p = argv[argv.index('--corpus') + 1]
        if os.path.exists(p):
            return p
        sys.exit('找不到语料文件：%s' % p)
    env = os.environ.get('HUANHAI_CORPUS')
    if env and os.path.exists(env):
        return env
    if os.path.exists(CORPUS):
        return CORPUS
    sys.exit('找不到语料文件。请用 --corpus PATH 或环境变量 HUANHAI_CORPUS 指定「总合集-全量.md」。')


def main():
    chap = sys.argv[1]
    minlen = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 8
    with io.open(resolve_corpus(sys.argv), encoding='utf-8', errors='replace') as f:
        corpus_norm = norm(f.read())

    with io.open(chap, encoding='utf-8') as f:
        content = f.read()

    quotes = []
    for a, b in PAIRS:
        quotes += re.findall(a + r'([^' + a + b + r']+)' + b, content)

    bad = []
    total = 0
    for q in quotes:
        # 省略号拼接的引语拆成多段分别校验
        for seg in re.split(r'…+|\.\.\.+', q):
            seg = norm(seg).strip('，,。；;：:、#|-—')
            if len(seg) < minlen:
                continue
            total += 1
            if seg not in corpus_norm:
                bad.append(seg)
    print('%s -> checked %d fragments (from %d quotes), NOT FOUND: %d'
          % (chap.rsplit('\\', 1)[-1], total, len(quotes), len(bad)))
    for b in bad:
        print('  [MISSING] %s' % b[:70])
    return len(bad)


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
