'''文本处理工具'''
import re
def split_text_by_length(text, max_len):
    return [text[i: i + max_len] for i in range(0, len(text), max_len)]

def split_text_by_sentence(text, max_len):
    sentences = re.split(r'(?<=[。！？])', text)
    result = []
    current_chunk = ''

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_len:
            current_chunk += sentence
        else:
            result.append(current_chunk)
            current_chunk = sentence

def split_text_by_count(text, count):
    '''给定分割数量进行分割'''
    sentences = re.split(r'(?<=[。！？，])', text) 
    result = []
    n = len(sentences) // count
    if n == 0:
        n = 1
    for i in range(0, len(sentences), n):
        result.append(''.join(sentences[i: i + n]))

    return result


def split_into_chapters(text):
    # 定义章节标题的正则表达式模式
    chapter_pattern = r'^\s*(第?\d+[章节编篇]|\d+\.|[\u4e00-\u9fa5]+)\s*'

    # 初始化结果列表和临时存储变量
    chapters = []
    current_chapter = ""

    # 按行分割文本
    lines = text.splitlines()

    for line in lines:
        # 判断当前行是否匹配章节标题
        if re.match(chapter_pattern, line):
            # 如果已经有内容，则保存上一个章节
            if current_chapter.strip():
                chapters.append(current_chapter.strip())
                current_chapter = ""
            # 将当前章节标题加入到新的章节内容中
            current_chapter += line + "\n"
        else:
            # 否则，将当前行添加到当前章节内容中
            current_chapter += line + "\n"

    # 添加最后一个章节
    if current_chapter.strip():
        chapters.append(current_chapter.strip())

    return chapters


