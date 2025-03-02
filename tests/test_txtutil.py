import pytest
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# sys.path.append("..")

from utils.txtutil import split_into_chapters

def test_split_text_normal():

    article = """
    第一章 介绍
    这是一个测试文档的第一部分内容。

    第二章 内容
    这是第二部分的内容。

    第三章 结论
    这是最后一部分内容。
    """

    # 调用函数并打印结果
    chapters = split_into_chapters(article)
    for i, chapter in enumerate(chapters):
        print(f"章节 {i + 1}:\n{chapter}\n")
                