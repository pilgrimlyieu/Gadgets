#!/usr/bin/python3

import argparse
import os
import re
import sys
import signal
import magic
from collections import Counter
from fnmatch import fnmatch

__version__ = "v1.0.1"
__year__    = 2024
__license__ = "MIT"
__author__  = "Lyieu"

libraries = {
    "c":     r"[^\W]",           # 所有可打印字符
    "cp":    r"[^\W]|[\s]",      # 所有可打印字符和空格字符
    "cn":    r"[\u4e00-\u9fff]", # 所有常用汉字
    "en":    r"[a-zA-Z]",        # 所有英文字母
    "alnum": r"[a-zA-Z\d]",      # 字母和数字字符
    "num":   r"[\d]",            # 所有数字
    "sp":    r"[\s]",            # 空白字符
    "punc":  r"[^\w\s]",         # 标点字符
}

def debug_info(message, verbose=False):
    if verbose:
        print(message)

def signal_handler(signum, frame):
    raise TimeoutError("Execution time exceeded the timeout.")

def file_statistics(file, regex, library, ignore_space, ignore_case, verbose):
    debug_info(f"Processing file: {file}", verbose)
    file_type = magic.from_file(file)
    if "text" not in file_type:
        debug_info(f"Skipping file due to non-text type: {file}", verbose)
        return None
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if ignore_space and not regex and  library not in ["cp", "sp"]:
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
    except UnicodeDecodeError:
        print(f"Skipping file due to encoding error: {file}")
        return None
    except TimeoutError:
        print(f"Execution time exceeded the timeout.")
        sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(
                        description='Count the occurrences of characters in files.',
                        epilog=
f'''
libraries:
  c           All printable characters.
  cp          All printable and space characters.
  cn          All common Chinese characters.
  en          All English alphabetic characters.
  alnum       Alphabetic and numeric characters.
  num         Numeric characters.
  sp          Space characters.
  punc        Punctuation characters.

Copyright (c) {__year__} {__author__} under {__license__} license.
''',
                        formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-e', '--expression',
        metavar="regex",
        type=str,
        default="",
        help='The regular expression to match.'
    )
    group.add_argument(
        '-l', '--library',
        metavar="library",
        type=str,
        choices=libraries.keys(),
        help='The character set library to use.'
    )
    parser.add_argument(
        '-f', '--format',
        metavar="format",
        type=str,
        default="",
        help='The file formats to process. Use \',\' to separate multiple formats (e.g. "-f txt,md").'
    )
    parser.add_argument(
        '-n', '--number',
        metavar="number",
        type=int,
        default=0,
        help='The number of most common characters to display.'
    )
    parser.add_argument(
        '-r', '--reverse',
        action='store_true',
        default=False,
        help='Reverse the order of the output.'
    )
    parser.add_argument(
        '-R', '--recursive',
        action='store_true',
        default=False,
        help='Recursively process directories.'
    )
    parser.add_argument(
        '-S', '--show-space',
        action='store_true',
        default=False,
        help='Show whitespace characters.'
    )
    parser.add_argument(
        '-i', '--case-insensitive',
        action='store_true',
        default=False,
        help='Ignore case when matching.'
    )
    parser.add_argument(
        '-p', '--display-percent',
        action='store_true',
        default=False,
        help='Display the percentage of occurrences for each character.'
    )
    parser.add_argument(
        '-t', '--timeout',
        metavar="seconds",
        type=int,
        default=60,
        help='The maximum time to process a file. (default: 60)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        default=False,
        help='Display verbose output.'
    )
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
        help='Display version information and exit.'
    )
    parser.add_argument(
        '-o', '--output',
        metavar="output",
        type=str,
        default="",
        help='The output file.'
    )
    parser.add_argument(
        'path',
        nargs='+',
        type=str,
        default="",
        help='The files or directories to process.'
    )
    args = parser.parse_args()
    return args

def process_file(file, expression, library, ignore_space, ignore_case, verbose, results, processed_files):
    statistics = file_statistics(file, expression, library, ignore_space, ignore_case, verbose)
    if statistics is not None:
        results.extend(statistics)
        processed_files.append(file)

def process_directory(directory, expression, library, ignore_space, ignore_case, recursive, file_formats, verbose, results, processed_files):
    for root, dirs, files in os.walk(directory):
        for name in files:
            if not file_formats or any(fnmatch(name, f'*.{fmt}') for fmt in file_formats):
                process_file(os.path.join(root, name), expression, library, ignore_space, ignore_case, verbose, results, processed_files)
        if not recursive:
            break

def main():
    args = parse_args()
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(args.timeout)

    file_formats = args.format.split(',') if args.format else []

    results = []
    processed_files = []
    for path in args.path:
        if os.path.isfile(path):
            process_file(path, args.expression, args.library, not args.show_space, args.case_insensitive, args.verbose, results, processed_files)
        elif os.path.isdir(path):
            process_directory(path, args.expression, args.library, not args.show_space, args.case_insensitive, args.recursive, file_formats, args.verbose, results, processed_files)

    counter = Counter(results)
    most_common = counter.most_common(args.number if args.number > 0 else None)
    most_common.sort(key=lambda x: (x[1], x[0]) if args.reverse else (-x[1], x[0]))

    f = open(args.output, 'w', encoding='utf-8') if args.output else sys.stdout
    last_count = None
    j = 0
    chars_count = 0
    chars_sum = sum(count for _, count in most_common) if args.display_percent else 0
    if args.display_percent:
        print(f"{'Rank':<5}\t{'Rank (tie)':<10}\t{'Character':<10}\t{'Count':<10}\t{'Percent':<10}", file=f)
    else:
        print(f"{'Rank':<5}\t{'Rank (tie)':<10}\t{'Character':<10}\t{'Count':<10}", file=f)
    for i, (char, count) in enumerate(most_common, start=1):
        chars_count += 1
        if count != last_count:
            j = i
        last_count = count
        escape_dict = {" ": r"\s", "\n": r"\n", "\t": r"\t", "\r": r"\r", "\f": r"\f", "\v": r"\v", "\b": r"\b"}
        char = escape_dict.get(char, char)
        if args.display_percent:
            percent = count / chars_sum * 100
            print(f"{i:<5}\t{j:<10}\t{char:<10}\t{count:<10}\t{percent:.4f}%", file=f)
        else:
            chars_sum += count
            print(f"{i:<5}\t{j:<10}\t{char:<10}\t{count:<10}", file=f)
    if args.output:
        f.close()

    print(f"Total characters: {chars_count}")
    print(f"Total occurrences: {chars_sum}\n")
    print("Processed files:")
    for file in processed_files:
        print(file)

if __name__ == "__main__":
    main()
