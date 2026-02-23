import json
import sys

from typing import Literal

type JsonType = dict[str, JsonType] | list[JsonType] | str | int | float | bool | None
type Fingerprint = Literal["list", "primitive"] | frozenset[str]

# 若一个 dict 中所有值都是相同的 primitive 类型，且条目数超过此阈值，
# 则视为均匀映射表（如 id→url、uid→avatar），只保留第一条作为示例。
UNIFORM_MAP_THRESHOLD = 10


def get_structure_fingerprint(value: JsonType) -> Fingerprint:
    """
    获取值的结构指纹，用于判断是否重复。
    - 字典：返回 frozenset(keys)
    - 列表：返回 'list' 字符串
    - 其他：返回 'primitive'，表示保留所有基本字段（如 name, age 不互斥）
    """
    if isinstance(value, dict):
        # 如果 value 是字典，它的结构由它的 keys 决定
        # 例如：{'mid': 1, 'name': 'a'} 的指纹是 keys('mid', 'name')
        return frozenset(value.keys())
    elif isinstance(value, list):
        return "list"
    else:
        # 基本类型不参与结构去重，防止误删不同含义的字段 (如 name 和 face 都是 string)
        return "primitive"


def _is_uniform_primitive_map(data: dict) -> bool:
    """
    判断一个 dict 是否为均匀 primitive 映射表：
    所有值均为 primitive 且类型完全一致，且条目数超过阈值。
    """
    if len(data) <= UNIFORM_MAP_THRESHOLD:
        return False
    prim_type = None
    for v in data.values():
        if isinstance(v, (dict, list)):
            return False
        vt = type(v)
        if prim_type is None:
            prim_type = vt
        elif vt is not prim_type:
            return False
    return True


def simplify(data: JsonType) -> JsonType:
    if isinstance(data, list):
        if not data:
            return []
        # 数组只保留第一个元素，并递归处理
        return [simplify(data[0])]

    elif isinstance(data, dict):
        # 检测均匀 primitive 映射表（键、值均为简单类型且高度重复）
        # 例如：{uid: base64_avatar, uid2: base64_avatar2, ...} → 只保留第一条
        if _is_uniform_primitive_map(data):
            first_k, first_v = next(iter(data.items()))
            omitted = len(data) - 1
            return {first_k: first_v, f"<+{omitted} 条同类条目已省略>": None}

        new_dict: dict[str, JsonType] = {}
        # 用来记录已经遇到过的复杂对象结构
        seen_structures: set[Fingerprint] = set()

        for k, v in data.items():
            fingerprint = get_structure_fingerprint(v)

            # 逻辑：
            # 1. 如果是基本类型，直接保留（比如 id, name, url 都要留着）
            # 2. 如果是复杂类型，检查指纹是否出现过。
            #    没出现过 -> 保留并记录指纹
            #    出现过   -> 认为是 Map 中的重复项，丢弃
            if fingerprint == "primitive":
                new_dict[k] = v
            else:
                if fingerprint not in seen_structures:
                    seen_structures.add(fingerprint)
                    new_dict[k] = simplify(v)  # 递归处理
                else:
                    # 指纹已存在，说明这个 key 对应的 value 结构
                    # 和之前的某个 key 的 value 结构完全一致（大概率是 Map），跳过。
                    pass

        return new_dict

    else:
        return data


def main():
    # 支持管道输入或文件参数
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File '{sys.argv[1]}' not found.")
            return
    else:
        if sys.stdin.isatty():
            print("请提供文件路径或通过管道输入 JSON 数据")
            return
        content = sys.stdin.read()

    try:
        data = json.loads(content)
        simplified = simplify(data)
        print(json.dumps(simplified, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
