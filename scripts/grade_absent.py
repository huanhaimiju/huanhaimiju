# -*- coding: utf-8 -*-
"""对 audit_all 报出的 ABSENT 片段做相似度分级，区分
  [转述] 相似度高(>=0.75) => 上一代建库时的删节/换词，语义可回源，属可接受
  [存疑] 相似度中(0.45~0.75) => 需人工核对
  [无源] 相似度低(<0.45) => 疑似非原文，须处理
用法: grade_absent.py <片段长度下限> [章名过滤]
  语料指定：--corpus PATH，或环境变量 HUANHAI_CORPUS
"""
import difflib
import glob
import io
import os
import re
import sys

# 语料默认路径（原作者本机）；移植后请用 --corpus PATH 或环境变量 HUANHAI_CORPUS。
CORPUS = r'H:\幻海迷局文章\幻海迷局\大合集\总合集-全量.md'
# 章节目录：默认取本仓库的 chapters/
CHAP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chapters')
DROP_Q = r'[\s*　\'’‘“”「」『』]'
DROP_P = DROP_Q + r'[，。、；：？！,.;:?!（）()【】《》…—\-～~]'
PAIRS = [('「', '」'), ('“', '”')]


def best_ratio(seg, corpus_norm, corpus_plain):
    """seg 与语料的最佳相似度：用语料中的滑动窗口粗配 + difflib 精算。"""
    if not seg:
        return 0.0, ''
    n = len(seg)
    best, best_ctx = 0.0, ''
    # 用 seg 的前 8 字做锚点找候选窗口
    anchor = seg[:8]
    for m in re.finditer(re.escape(anchor), corpus_plain):
        s = m.start()
        for w in (n, n + 10, n + 20, n + 30):
            win = corpus_plain[s:s + w]
            if not win:
                continue
            r = difflib.SequenceMatcher(None, seg, win).ratio()
            if r > best:
                best, best_ctx = r, win
        if best >= 0.95:
            break
    return best, best_ctx


def main():
    minlen = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    only = sys.argv[2] if len(sys.argv) > 2 else ''
    with io.open(CORPUS, encoding='utf-8', errors='replace') as f:
        raw = f.read()
    nq = re.sub(DROP_Q, '', raw)
    np_ = re.sub(DROP_P, '', raw)

    files = [p for p in sorted(glob.glob(os.path.join(CHAP_DIR, '*.md')))
             if not only or only in os.path.basename(p)]
    buckets = {'转述': [], '存疑': [], '无源': []}
    for path in files:
        with io.open(path, encoding='utf-8') as f:
            content = f.read()
        quotes = []
        for a, b in PAIRS:
            quotes += re.findall(a + r'([^' + a + b + r']+)' + b, content)
        for q in quotes:
            for seg in re.split(r'…+|\.\.\.+', q):
                seg = re.sub(DROP_Q, '', seg).strip('，,。；;：:、#|-—')
                if len(seg) < minlen:
                    continue
                if seg in nq:
                    continue
                r, ctx = best_ratio(seg, nq, np_)
                tag = '转述' if r >= 0.75 else ('存疑' if r >= 0.45 else '无源')
                buckets[tag].append((os.path.basename(path), round(r, 2), seg, ctx))
    for tag in ('转述', '存疑', '无源'):
        print('=' * 70)
        print('【%s】%d 条' % (tag, len(buckets[tag])))
        for name, r, seg, ctx in sorted(buckets[tag], key=lambda x: x[1]):
            print('  %-22s %.2f  %s' % (name, r, seg[:60]))
            if tag in ('存疑', '无源'):
                print('        原文近似: %s' % ctx[:70])
    print('=' * 70)
    print('转述=%d  存疑=%d  无源=%d  (合计 %d)'
          % (len(buckets['转述']), len(buckets['存疑']), len(buckets['无源']),
             sum(len(v) for v in buckets.values())))


if __name__ == '__main__':
    main()
