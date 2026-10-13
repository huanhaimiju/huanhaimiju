# -*- coding: utf-8 -*-
"""从全量语料生成 article-index.md：日期 / 系列 / 主题标签 / 原文行号。
流式处理，正文不驻内存（只保留标题级元数据）。
"""
import argparse
import collections
import io
import os
import re
import sys

# 语料默认路径（原作者本机）；移植后请用 --corpus PATH 或环境变量 HUANHAI_CORPUS。
CORPUS = r'H:\幻海迷局文章\幻海迷局\大合集\总合集-全量.md'
# 输出默认写到本仓库根目录的 article-index.md
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'article-index.md')

ART_RE = re.compile(r'^# (\d{4}-\d{2}-\d{2})_(.+)$')

# 系列识别（按优先级顺序匹配）
SERIES = [
    (r'楞严经.{0,4}五阴十魔|五阴十魔', '楞严经·五阴十魔'),
    (r'楞严经.{0,6}(精研|七趣)', '楞严经·精研七趣'),
    (r'楞严经.{0,6}四种清净明诲|四种清净明诲', '楞严经·四种清净明诲'),
    (r'楞严经', '楞严经·其他'),
    (r'法华经', '法华经略说'),
    (r'八大人觉经', '八大人觉经'),
    (r'地藏菩萨本愿经|地藏经略谈|地藏经略说', '地藏经略谈'),
    (r'轮转五道|罪福报应经', '轮转五道罪福报应经'),
    (r'法灭尽经', '法灭尽经'),
    (r'十善业道经', '十善业道经'),
    (r'念佛圆通', '念佛圆通'),
    (r'阿弥陀经', '阿弥陀经析'),
    (r'觉林菩萨偈', '觉林菩萨偈'),
    (r'普门品', '普门品三研'),
    (r'普门超度|普门系统', '普门超度/普门系统'),
    (r'九字读经', '九字读经练习'),
    (r'量子纠缠', '量子纠缠与佛法'),
    (r'佛法讲堂', '佛法讲堂'),
    (r'宝林札记', '宝林札记'),
    (r'【音频】|音频', '音频短文'),
    (r'碎演慈香|答疑', '人间天答疑'),
    (r'感应|记$', '感应记'),
    (r'小故事|故事', '因果故事'),
    (r'学佛|修行|答疑|答问', '学佛答疑'),
    (r'感应记', '感应记'),
]

# 主题标签（按优先级，取最多 3 个）
TOPICS = [
    (r'回向', '回向'),
    (r'小回向', '小回向'),
    (r'消业|业力|罪业|业障', '消业/业力'),
    (r'债主|讨债|欠债|还债|债务', '债主'),
    (r'超度|普门|召请|佛光|往生咒', '超度/普门'),
    (r'忏悔|悔过', '忏悔'),
    (r'往生|极乐|阿弥陀|十念|接引', '往生'),
    (r'信愿行|信愿|疑佛|信仰', '信愿行'),
    (r'福报|培福|资粮|布施|放生|供僧', '福报/培福'),
    (r'读经|听经|诵经|讲经|抄经|九字', '读经'),
    (r'楞严|五阴|五十阴|七趣', '楞严义理'),
    (r'法华|法华经', '法华义理'),
    (r'地藏经|地藏菩萨|阎浮|地狱', '地藏义理'),
    (r'礼敬|顶礼|恭敬|供养', '礼敬供养'),
    (r'素食|吃肉|杀生|荤', '素食/不杀'),
    (r'家庭|父母|孝|夫妻|子女|教育', '家庭'),
    (r'疾病|病|养生|长寿|医药', '疾病养生'),
    (r'考试|坚持|三分钟热血|懈怠', '学佛坚持'),
    (r'三部走|学佛次第|阶段', '三部走/次第'),
    (r'邪见|误区|陷阱|骗局|兜售', '误区辨析'),
    (r'金钱|钱财|财富|布施|生意', '金钱'),
    (r'打坐|静坐|禅定|专注', '打坐/定力'),
    (r'音声|音频|音乐|唱歌', '音声/音频'),
    (r'量子|科学|物理|纠缠', '科学探讨'),
    (r'梦|感应|神通|灵感', '感应/神通'),
    (r'愿|发愿|发心', '发愿/发心'),
    (r'戒|持戒|五戒|八关斋', '戒律'),
    (r'神通|变化|加持', '神通加持'),
    (r'净土|经中|经论|圆顿|法门', '经论法门'),
    (r'神识|唯识|阿赖耶|识', '唯识/神识'),
    (r'时间|空间|四维|三维', '时空'),
    (r'气|能量|磁场|身体', '气/能量'),
    (r'忏|悔', '忏悔'),
    (r'临终|助念|死亡|往生', '临终/助念'),
]

# 为控制体积，索引中省略的正文不影响定位
def classify_series(t):
    for pat, name in SERIES:
        if re.search(pat, t):
            return name
    return '综合/其他'


def classify_topics(t):
    out = []
    for pat, name in TOPICS:
        if re.search(pat, t):
            if name not in out:
                out.append(name)
        if len(out) >= 3:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description='从总合集生成 article-index.md')
    ap.add_argument('--corpus', default=os.environ.get('HUANHAI_CORPUS') or CORPUS,
                    help='语料「总合集-全量.md」路径')
    ap.add_argument('--out', default=OUT, help='输出索引路径')
    args = ap.parse_args()
    if not os.path.exists(args.corpus):
        sys.exit('找不到语料文件：%s' % args.corpus)

    rows = []
    f = io.open(args.corpus, encoding='utf-8', errors='replace')
    for i, line in enumerate(f, 1):
        s = line.strip()
        m = ART_RE.match(s)
        if m:
            date, title = m.group(1), m.group(2).strip()
            rows.append((date, classify_series(title), classify_topics(title), title, i))
    f.close()

    print('articles:', len(rows), file=sys.stderr)
    year = collections.Counter(r[0][:4] for r in rows)
    ser = collections.Counter(r[1] for r in rows)
    print('years:', sorted(year.items()), file=sys.stderr)

    with io.open(args.out, 'w', encoding='utf-8', newline='\n') as out:
        out.write('# 幻海迷局全量文章索引\n\n')
        out.write('> 语料：%s（2015—2026，共 %d 篇）\n' % (args.corpus, len(rows)))
        out.write('> 行号为**该文件内**的行号。回源取原文：读该行向下约 200 行，或用标题 grep。\n')
        out.write('> 图例：`日期 | 系列 | 主题标签 | 行号 | 标题`\n\n')
        out.write('## 年份分布\n\n')
        out.write('| 年 | 篇数 |\n|---|---|\n')
        for y, c in sorted(year.items()):
            out.write('| %s | %d |\n' % (y, c))
        out.write('\n## 系列分布\n\n| 系列 | 篇数 |\n|---|---|\n')
        for s, c in ser.most_common():
            out.write('| %s | %d |\n' % (s, c))

        out.write('\n## 全量索引\n\n')
        cur_year = None
        for date, s, tp, title, ln in rows:
            if date[:4] != cur_year:
                cur_year = date[:4]
                out.write('\n### %s\n\n' % cur_year)
            out.write('- %s｜%s｜%s｜L%d｜%s\n' % (date, s, '/'.join(tp) if tp else '—', ln, title))
    print('written', args.out, file=sys.stderr)


if __name__ == '__main__':
    main()
