import os
import re


# 起始位置开始匹配
# re.I : 使匹配对大小写不敏感
# re.L : 做本地化识别（locale-aware）匹配
# re.M : 多行匹配，影响 ^ 和 $
# re.S : 使 . 匹配包括换行在内的所有字符
# re.U : 根据Unicode字符集解析字符。这个标志影响 \w, \W, \b, \B.
# re.X : 该标志通过给予你更灵活的格式以便你将正则表达式写得更易于理解。

# 多数字母和数字前加一个反斜杠时会拥有不同的含义。
# 标点符号只有被转义时才匹配自身，否则它们表示特殊的含义。
# 反斜杠本身需要使用反斜杠转义
# 由于正则表达式通常都包含反斜杠，所以你最好使用原始字符串来表示它们。模式元素(如 r'\t'，等价于 '\\t')匹配相应的特殊字符。

# ^  匹配字符串的开头
# $	 匹配字符串的末尾。
# .	匹配任意字符，除了换行符，当re.DOTALL标记被指定时，则可以匹配包括换行符的任意字符。
# [...]	用来表示一组字符,单独列出：[amk] 匹配 'a'，'m'或'k'
# [^...]	不在[]中的字符：[^abc] 匹配除了a,b,c之外的字符。
# re*	匹配0个或多个的表达式。
# re+	匹配1个或多个的表达式。
# re?	匹配0个或1个由前面的正则表达式定义的片段，非贪婪方式
# re{ n}	精确匹配 n 个前面表达式。例如， o{2} 不能匹配 "Bob" 中的 "o"，但是能匹配 "food" 中的两个 o。
# re{ n,}	匹配 n 个前面表达式。例如， o{2,} 不能匹配"Bob"中的"o"，但能匹配 "foooood"中的所有 o。"o{1,}" 等价于 "o+"。"o{0,}" 则等价于 "o*"。
# re{ n, m}	匹配 n 到 m 次由前面的正则表达式定义的片段，贪婪方式
# a| b	匹配a或b
# (re)	对正则表达式分组并记住匹配的文本
# (?imx)	正则表达式包含三种可选标志：i, m, 或 x 。只影响括号中的区域。
# (?-imx)	正则表达式关闭 i, m, 或 x 可选标志。只影响括号中的区域。
# (?: re)	类似 (...), 但是不表示一个组
# (?imx: re)	在括号中使用i, m, 或 x 可选标志
# (?-imx: re)	在括号中不使用i, m, 或 x 可选标志
# (?#...)	注释.
# (?= re)	前向肯定界定符。如果所含正则表达式，以 ... 表示，在当前位置成功匹配时成功，否则失败。但一旦所含表达式已经尝试，匹配引擎根本没有提高；模式的剩余部分还要尝试界定符的右边。
# (?! re)	前向否定界定符。与肯定界定符相反；当所含表达式不能在字符串当前位置匹配时成功
# (?> re)	匹配的独立模式，省去回溯。
# \w	匹配字母数字及下划线
# \W	匹配非字母数字及下划线
# \s	匹配任意空白字符，等价于 [ \t\n\r\f]。
# \S	匹配任意非空字符
# \d	匹配任意数字，等价于 [0-9].
# \D	匹配任意非数字
# \A	匹配字符串开始
# \Z	匹配字符串结束，如果是存在换行，只匹配到换行前的结束字符串。
# \z	匹配字符串结束
# \G	匹配最后匹配完成的位置。
# \b	匹配一个单词边界，也就是指单词和空格间的位置。例如， 'er\b' 可以匹配"never" 中的 'er'，但不能匹配 "verb" 中的 'er'。
# \B	匹配非单词边界。'er\B' 能匹配 "verb" 中的 'er'，但不能匹配 "never" 中的 'er'。
# \n, \t, 等.	匹配一个换行符。匹配一个制表符。等
# \1...\9	匹配第n个分组的内容。
# \10	匹配第n个分组的内容，如果它经匹配。否则指的是八进制字符码的表达式。

# .	匹配除 "\n" 之外的任何单个字符。要匹配包括 '\n' 在内的任何字符，请使用象 '[.\n]' 的模式。
# \d	匹配一个数字字符。等价于 [0-9]。
# \D	匹配一个非数字字符。等价于 [^0-9]。
# \s	匹配任何空白字符，包括空格、制表符、换页符等等。等价于 [ \f\n\r\t\v]。
# \S	匹配任何非空白字符。等价于 [^ \f\n\r\t\v]。
# \w	匹配包括下划线的任何单词字符。等价于'[A-Za-z0-9_]'。
# \W	匹配任何非单词字符。等价于 '[^A-Za-z0-9_]'。


def r_compile(m, flags=0):
    c = re.compile(m, flags)
    return c


def r_match(m, s, flags=0):
    c = r_compile(m, flags)
    g = c.match(s)
    print(g)
    if g:
        print(g.groups())
        print(g.pos)


def r_search(m, s, flags=0):
    c = r_compile(m, flags)
    g = c.search(s)
    print(g)
    if g:
        print(g.groups())
        print(g.start())
        print(g.end())
        print(g.pos)


def r_sub(m, rep, s, count=0, flags=0):
    c = r_compile(m, flags)
    g = c.sub(rep, s, count)
    print(g)


def r_findall(m, s, flags=0):
    c = r_compile(m, flags)
    g = c.findall(s)
    print(g)
    if g:
        print(len(g))


def r_finditer(m, s, flags=0):
    c = r_compile(m, flags)
    g = c.finditer(s)
    print(g)
    if g:
        for sub in g:
            print(sub.groups())
            print(sub.group(0))


def r_spit(m, s, flags=0):
    c = r_compile(m, flags)
    g = c.split(s)
    print(g)


def mytest():
    # r_match('hai', 'gaohaibao')
    # r_search('hai', 'gaohaibao')
    # r_match('(.*ai)gao(.+)o', 'gaohaigaobaofa')
    # r_search('(.*ai)gao(.+)o', 'gaohaigaobaofa')
    # r_sub('(.*ai)gao(.+)o','fuck', 'gaohaigaobaofa')
    # r_findall('(.*)gao(.*)o', 'agaohaigaobaofagaosealod')
    # r_findall('(.*)gao', 'agaohaigaobaofagaosealod')
    # r_finditer('(.*)gao', 'agaohaigaobaofagaosealod')
    # r_findall('gao(.*)', 'agaohaigaobaofagaosealod')
    # r_spit('gao', 'agaohaigaobaofagaosealod')
    # r_search('22 is connected to Host port no: (.*) ', '504:Guest port no: 22 is connected to Host port no: 10042 ')
    r_findall('22 is connected to Host port no: (.*) ', '504:Guest port no: 22 is connected to Host port no: 10042 ')


def main():
    fd = os.popen('ifconfig wifi0')
    info = fd.read()
    fd.close()
    # print(info)
    r_search('ether (.*) +', info)


def read_file(filename, coding='utf-8'):
    fd = open(filename, 'r', encoding=coding)
    info = fd.read()
    fd.close()
    return info


def main2():
    info = read_file('cc.xml')
    print(info)
    r_findall('fpga([\\w]+).zip', info)


if __name__ == '__main__':
    mytest()
