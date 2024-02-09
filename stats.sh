#!/bin/bash

# DEPRECATED: Use `stats.py` instead.

# 定义变量来存储参数的值
number=0
regex=""
library=""
reverse=false
recursive=false
ignore_space=true
ignore_case=false
debug=false
file_formats=()
output_file=""
temp_file=$(mktemp)

# 定义 Perl 正则表达式字符集库
declare -A libraries=(
  [c]="[:graph:]" # 所有可打印字符
  [cp]="[:print:]"  # 所有可打印字符和空格字符
  [cn]="\\p{Script=Han}"  # 所有常用汉字
  [en]="a-zA-Z"  # 所有英文字母
  [alnum]="[:alnum:]"  # 字母和数字字符
  [num]="[:digit:]"  # 所有数字
  [sp]="[:space:]"  # 空白字符
  [punc]="[:punct:]"  # 标点字符
)

# 定义一个函数来显示使用方法
usage() {
  echo -e "Usage: $0 [-n number] [-e regex] [-l library] [-f format] [-o output] [-d] [-r] [-R] [-S] [-i] [-h] file | dir [file | dir ...]

Options:
  -n number   Display the top number of results.
  -e regex    Use the specified regular expression.
  -l library  Use the specified character set library. This option cannot be used with the -e option.
  -f format   Process files of the specified format(s).
  -o output   Write the results to the specified output file.
  -d          Debug mode.
  -r          Reverse the order of the results.
  -R          Process directories recursively.
  -S          Show whitespace characters.
  -i          Ignore case.
  -h          Display this help message.

Arguments:
  file        The file(s) to process.
  dir         The directory to process.

Libraries:
  c           All printable characters.
  cp          All printable and space characters.
  cn          All common Chinese characters.
  en          All English alphabetic characters.
  alnum       Alphabetic and numeric characters.
  num         Numeric characters.
  sp          Space characters.
  punc        Punctuation characters."
}

process_file() {
  file=$1
  echo "$file" >> "$temp_file"
  # 根据是否设置了 -e 或 -l 选项来决定如何处理文件
  if [ -n "$regex" ]; then
    # 如果设置了 -e 选项，则使用正则表达式来过滤字符
    perl -C -ne "while (/$regex/g) {print \"\$&\n\"}" "$file"
  elif [ -n "$library" ]; then
    # 如果设置了 -l 选项，则只显示字符集库中的字符
    perl -C -ne 'while (/(['${libraries[$library]}'])/g) {print "$1\n"}' "$file"
  else
    # 如果没有设置 -e 或 -l 选项，则显示所有字符
    cat "$file"
  fi
}

# 使用 getopts 循环来处理命令行参数
while getopts "n:e:l:f:o:drRSih" opt; do
  case $opt in
    n) number=$OPTARG
       # 检查 number 是否为正整数
       if ! [[ "$number" =~ ^[0-9]+$ ]]; then
         echo "Error: -n option requires a positive integer argument." >&2
         exit 1
       fi ;;
    e) regex=$OPTARG
        # 检查 -e 和 -l 选项是否同时使用
        if [ -n "$library" ]; then
          echo "Error: -e and -l options cannot be used together." >&2
          exit 1
        fi ;;
    l) library=$OPTARG
       # 检查 -e 和 -l 选项是否同时使用
       if [ -n "$regex" ]; then
         echo "Error: -e and -l options cannot be used together." >&2
         exit 1
       fi
       # 检查指定的字符集库是否存在
       if ! [[ -v libraries["$library"] ]]; then
         echo "Error: Unknown library -$library" >&2
         exit 1
       fi ;;
    d) debug=true ;;
    r) reverse=true ;;
    R) recursive=true ;;
    S) ignore_space=false ;;
    i) ignore_case=true ;;
    f) IFS=',' read -ra formats <<< "$OPTARG"
       for format in "${formats[@]}"; do
         file_formats+=("$format")
       done ;;
    o) output_file=$OPTARG ;;
    h) usage
       exit 0 ;;
    \?) echo "Invalid option -$OPTARG" >&2
        usage
        exit 1 ;;
  esac
done

# 使用 shift 命令来移除已处理的参数
shift $((OPTIND -1))

# 检查是否提供了至少一个文件参数
if [ $# -eq 0 ]; then
  echo "Error: At least one file argument is required." >&2
  usage
  exit 1
fi

# 处理每个输入的文件或目录
(
  for input in "$@"; do
    # 如果输入是目录
    if [ -d "$input" ]; then
      if $recursive; then
        # 如果开启了递归选项，使用 find 命令递归地查找并处理目录中的文件
        while IFS= read -r -d '' file
        do
          # 检查文件是否符合扩展名限制
          if [ ${#file_formats[@]} -eq 0 ] || [[ " ${file_formats[@]} " =~ " ${file##*.} " ]]; then
            process_file "$file"
          fi
        done < <(find "$input" -type f -print0)
      else
        # 如果没有开启递归选项，只处理该目录下的文件
        for file in "$input"/*; do
          if [ ! -f "$file" ]; then
            continue
          fi
          # 检查文件是否符合扩展名限制
          if [ ${#file_formats[@]} -eq 0 ] || [[ " ${file_formats[@]} " =~ " ${file##*.} " ]]; then
            process_file "$file"
          fi
        done
      fi
    # 如果输入是文件
    elif [ -f "$input" ]; then
      # 检查文件是否符合扩展名限制
      if [ ${#file_formats[@]} -eq 0 ] || [[ " ${file_formats[@]} " =~ " ${input##*.} " ]]; then
        process_file "$input"
      fi
    else
      echo "Error: $input is not a valid file or directory." >&2
    fi
  done
) | {
  # 根据是否设置了 -S 选项来决定是否显示空白字符
  if $ignore_space; then
    tr -d '[:space:]'
  else
    cat
  fi
} | {
  # 根据是否设置了 -i 选项来决定是否忽略大小写
  if $ignore_case; then
    tr '[:upper:]' '[:lower:]'
  else
    cat
  fi
} | rg -o .| sort | uniq -c | {
  # 根据是否设置了 -r 选项来决定结果的排序顺序
  if $reverse; then
    sort -k1n
  else
    sort -k1nr
  fi
} | {
  i=1  # 初始化序号
  while IFS=' ' read -ra line; do
    # 使用数组切片来忽略开头的空字段
    count=${line[0]}
    char=${line[1]}  # 获取第二个字段，即字符
    printf "%d\t%s\t%d\n" "$i" "$char" "$count"
    ((i++))  # 增加序号
  done
} | {
  if [ "$number" -gt 0 ]; then
    # 如果设置了数量选项，则只显示指定数量的结果
    head -n "$number"
  else
    cat
  fi
} > "${output_file:-/dev/stdout}"

# 显示调试信息
if $debug; then
  echo -e "
Debug Information
=================
Number:\t$number
Regex:\t$regex
Library:\t$library
Reverse:\t$reverse
Recursive:\t$recursive
Ignore Space:\t$ignore_space
Ignore Case:\t$ignore_case
File Formats:\t${file_formats[@]}
Processed Files:" | tee --append ${output_file:-/dev/null}
  cat "$temp_file" | tee --append ${output_file:-/dev/null}
fi

rm "$temp_file"  # 删除临时文件

