# -*- coding: utf-8 -*-
"""全库引语体检：报告每个章节的引语回源命中情况，区分
  [OK]      原文可原样命中
  [REFORM]  去标点后命中 => 上一代建库时的删节/标点改写，语义属实
  [ABSENT]  去标点后仍不命中 => 需人工核对
用法: audit_all.py [最短片段长度] [-v]
  语料指定：--corpus PATH，或环境变量 HUANHAI_CORPUS
"""
import glob
import io
import os
import re
import sys

# 语料默认路径（原作者本机）；移植后请用 --corpus PATH 或环境变量 HUANHAI_CORPUS。
CORPUS = r'H:\幻海迷局文章\幻海迷局\大合集\总合集-全量.md'
# 章节目录：默认取本仓库的 chapters/
CHAP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chapters')
# 归一化：去空白、markdown 符号、引号；【去标点】模式额外去标点
DROP_Q = r'[\s*　\'’‘“”「」『』]'
DROP_P = DROP_Q + r'[，。、；：？！,.;:?!（）()【】《》…—\-～~]'
PAIRS = [('「', '」'), ('“', '”')]


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
    minlen = int(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 8
    with io.open(resolve_corpus(sys.argv), encoding='utf-8', errors='replace') as f:
        raw = f.read()
    nq = re.sub(DROP_Q, '', raw)
    np_ = re.sub(DROP_P, '', raw)

    files = sorted(glob.glob(os.path.join(CHAP_DIR, '*.md')))
    tot_ok = tot_re = tot_bad = 0
    rows = []
    for path in files:
        with io.open(path, encoding='utf-8') as f:
            content = f.read()
        quotes = []
        for a, b in PAIRS:
            quotes += re.findall(a + r'([^' + a + b + r']+)' + b, content)
        ok = reform = bad = 0
        bads = []
        for q in quotes:
            for seg in re.split(r'…+|\.\.\.+', q):
                seg = re.sub(DROP_Q, '', seg).strip('，,。；;：:、#|-—')
                if len(seg) < minlen:
                    continue
                if seg in nq:
                    ok += 1
                elif re.sub(DROP_P, '', seg) in np_:
                    reform += 1
                else:
                    bad += 1
                    bads.append(seg)
        tot_ok += ok
        tot_re += reform
        tot_bad += bad
        rows.append((os.path.basename(path), ok, reform, bad, bads))

    print('%-26s %6s %8s %7s' % ('chapter', 'OK', 'REFORM', 'ABSENT'))
    print('-' * 52)
    for name, ok, reform, bad, _ in rows:
        flag = '' if bad == 0 else '   <-- 需核对'
        print('%-26s %6d %8d %7d%s' % (name, ok, reform, bad, flag))
    print('-' * 52)
    print('%-26s %6d %8d %7d' % ('TOTAL', tot_ok, tot_re, tot_bad))
    print()
    print('说明：OK=原文原样命中；REFORM=仅标点/删节差异（上一代建库的转述，语义可回源）；ABSENT=需人工核对。')
    if '-v' in sys.argv:
        for name, ok, reform, bad, bads in rows:
            if bads:
                print('\n### %s' % name)
                for b in bads:
                    print('  [ABSENT] %s' % b[:72])


if __name__ == '__main__':
    main()
