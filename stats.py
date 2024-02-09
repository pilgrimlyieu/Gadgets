#!/usr/bin/python3

import argparse
import os
import re
import sys
from collections import Counter
from fnmatch import fnmatch

# 定义 Perl 正则表达式字符集库
libraries = {
    "c": r"\w",  # 所有可打印字符
    "cp": r"\S",  # 所有可打印字符和空格字符
    "cn": r"[\u4e00-\u9fff]",  # 所有常用汉字
    "en": r"[a-zA-Z]",  # 所有英文字母
    "alnum": r"\w",  # 字母和数字字符
    "num": r"\d",  # 所有数字
    "sp": r"\s",  # 空白字符
    "punc": r"[^\w\s]",  # 标点字符
}

def process_file(file, regex, library, ignore_space, ignore_case, verbose):
    if verbose:
        print(f"Processing file: {file}")
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        if ignore_space:
            content = re.sub(r'\s', '', content)
        if ignore_case:
            content = content.lower()
        if regex:
            matches = re.findall(regex, content)
        elif library:
            matches = re.findall(libraries[library], content)
        else:
            matches = list(content)
        return matches

def main():
    parser = argparse.ArgumentParser(description='Count the occurrences of characters in files.',
                                     epilog='''libraries:
  c           All printable characters.
  cp          All printable and space characters.
  cn          All common Chinese characters.
  en          All English alphabetic characters.
  alnum       Alphabetic and numeric characters.
  num         Numeric characters.
  sp          Space characters.
  punc        Punctuation characters.''',
  formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-n', '--number', metavar="number", type=int, default=0, help='The number of most common characters to display.')
    parser.add_argument('-e', '--expression', metavar="regex", type=str, default="", help='The regular expression to match.')
    parser.add_argument('-l', '--library', metavar="library", type=str, choices=libraries.keys(), help='The character set library to use.')
    parser.add_argument('-f', '--format', metavar="format", type=str, default="", help='The file formats to process.')
    parser.add_argument('-o', '--output', metavar="output", type=str, default="", help='The output file.')
    parser.add_argument('-r', '--reverse', action='store_true', help='Reverse the order of the output.')
    parser.add_argument('-R', '--recursive', action='store_true', help='Recursively process directories.')
    parser.add_argument('-S', '--show-space', action='store_true', help='Show whitespace characters.')
    parser.add_argument('-i', '--case-sensitive', action='store_true', help='Ignore case when matching.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display verbose output.')
    parser.add_argument('paths', nargs='+', help='The files or directories to process.')
    args = parser.parse_args()

    if args.expression and args.library:
        print("Error: --expression and --library options cannot be used together.")
        sys.exit(1)

    if args.library and args.library not in libraries:
        print(f"Error: Unknown library --{args.library}")
        sys.exit(1)

    file_formats = args.format.split(',') if args.format else []

    results = []
    processed_files = []  # 新增一个列表用于存储处理过的文件
    for path in args.paths:
        if os.path.isfile(path):
            if not file_formats or any(fnmatch(path, f'*.{fmt}') for fmt in file_formats):
                results.extend(process_file(path, args.expression, args.library, not args.show_space, not args.case_sensitive, args.verbose))
                processed_files.append(path)  # 处理完一个文件后，将其添加到列表中
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for name in files:
                    if not file_formats or any(fnmatch(name, f'*.{fmt}') for fmt in file_formats):
                        results.extend(process_file(os.path.join(root, name), args.expression, args.library, not args.show_space, not args.case_sensitive, args.verbose))
                        processed_files.append(os.path.join(root, name))  # 处理完一个文件后，将其添加到列表中
                if not args.recursive:
                    break

    counter = Counter(results)
    most_common = counter.most_common(args.number if args.number > 0 else None)
    most_common.sort(key=lambda x: (x[1], x[0]) if args.reverse else (-x[1], x[0]))

    with open(args.output, 'w', encoding='utf-8') if args.output else sys.stdout as f:
        for i, (char, count) in enumerate(most_common, start=1):
            escape_dict = {" ": r"\s", "\n": r"\n", "\t": r"\t", "\r": r"\r", "\f": r"\f", "\v": r"\v"}
            char = escape_dict.get(char, char)
            print(f"{i}\t{char}\t{count}", file=f)

    # 在所有文件处理完后，输出处理过的文件列表
    print("Processed files:")
    for file in processed_files:
        print(file)

if __name__ == "__main__":
    main()
