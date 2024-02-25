import os
import json
import copy


def tran_com(obj, obj_type, tran_func, default):
    ret = copy.deepcopy(default)
    if obj is None:
        return ret
    if type(obj) == obj_type:
        return obj
    try:
        ret = tran_func(obj)
    except BaseException as e:
        pass
    return ret


def tran_int(obj, default=-1):
    ret = tran_com(obj, int, int, default)
    return ret


def tran_str(obj, default=''):
    ret = tran_com(obj, str, str, default)
    return ret


def tran_dict(obj):
    ret = {}
    if obj is None or type(obj) not in [dict]:
        return ret
    return obj


def tran_list(obj):
    ret = []
    if obj is None or type(obj) not in [list]:
        return ret
    return obj


def get_int(dictInfo, key, default=-1):
    cur_dict = tran_dict(dictInfo)
    ret = tran_int(cur_dict.get(key), default=default)
    return ret


def get_str(dictInfo, key, default=''):
    cur_dict = tran_dict(dictInfo)
    ret = tran_str(cur_dict.get(key), default=default)
    return ret


def get_dict(dictInfo, key):
    cur_dict = tran_dict(dictInfo)
    ret = tran_dict(cur_dict.get(key))
    return ret


def get_list(dictInfo, key):
    cur_dict = tran_dict(dictInfo)
    ret = tran_list(cur_dict.get(key))
    return ret


def write_file(filename, info):
    fd = open(filename, 'w')
    fd.write(info)
    fd.close()


def read_file(filename, coding='utf-8'):
    fd = open(filename, 'r', encoding=coding)
    info = fd.read()
    fd.close()
    return info


def parse_json_config(filename, recursive=True):
    config_str = read_file(filename)
    config_json = json.loads(config_str)
    if recursive and 'include' in config_json:
        include_file_list = get_list(config_json, 'include')
        config_dir, _ = os.path.split(filename)
        for subfile in include_file_list:
            abs_subfile = os.path.join(config_dir, subfile)
            includeJson = parse_json_config(abs_subfile)
            config_json.update(includeJson)
        config_json.pop('include')
    return config_json


def write_json_config(filename, configJson):
    config_str = json.dumps(configJson, indent=2)
    write_file(filename, config_str)


if __name__ == '__main__':
    print(tran_str(None))
    print(tran_str(7))
