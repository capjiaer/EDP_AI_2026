#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit 基本功能测试

测试核心功能是否正常工作。
"""

import unittest
import tempfile
import os
from pathlib import Path

# 导入我们的新实现
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from configkit import (
    merge_dict,
    value_format_py2tcl,
    value_format_tcl2py,
    DictOperations,
    ValueConverter,
    TclBridge,
    ConversionMode,
)
from configkit.exceptions import ConversionError


class TestMergeDict(unittest.TestCase):
    """测试字典合并功能"""

    def test_merge_simple_dicts(self):
        """测试简单字典合并"""
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'b': 3, 'c': 4}
        result = merge_dict(dict1, dict2)
        self.assertEqual(result, {'a': 1, 'b': 3, 'c': 4})

    def test_merge_nested_dicts(self):
        """测试嵌套字典合并"""
        dict1 = {'a': 1, 'b': {'c': 2, 'd': 3}}
        dict2 = {'b': {'c': 4, 'e': 5}, 'f': 6}
        result = merge_dict(dict1, dict2)
        self.assertEqual(result, {'a': 1, 'b': {'c': 4, 'd': 3, 'e': 5}, 'f': 6})

    def test_merge_lists(self):
        """测试列表合并"""
        dict1 = {'a': [1, 2], 'b': 3}
        dict2 = {'a': [3, 4], 'c': 5}
        result = merge_dict(dict1, dict2)
        self.assertEqual(result, {'a': [1, 2, 3, 4], 'b': 3, 'c': 5})


class TestValueConversion(unittest.TestCase):
    """测试值转换功能"""

    def test_py2tcl_basic_types(self):
        """测试基本类型 Python → Tcl 转换"""
        converter = ValueConverter()
        self.assertEqual(converter.py_to_tcl(None), '""')
        self.assertEqual(converter.py_to_tcl(True), '1')
        self.assertEqual(converter.py_to_tcl(False), '0')
        self.assertEqual(converter.py_to_tcl(42), '42')
        self.assertEqual(converter.py_to_tcl(3.14), '3.14')
        self.assertEqual(converter.py_to_tcl("hello"), 'hello')
        self.assertEqual(converter.py_to_tcl("hello world"), '{hello world}')

    def test_py2tcl_lists(self):
        """测试列表 Python → Tcl 转换"""
        converter = ValueConverter()
        self.assertEqual(converter.py_to_tcl([1, 2, 3]), '[list 1 2 3]')
        self.assertEqual(converter.py_to_tcl(["a", "b", "c"]), '[list a b c]')

    def test_tcl2py_basic_types(self):
        """测试基本类型 Tcl → Python 转换"""
        converter = ValueConverter()
        self.assertEqual(converter.tcl_to_py('""'), '')  # 无类型上下文，空字符串就是空字符串
        self.assertEqual(converter.tcl_to_py('1'), 1)
        self.assertEqual(converter.tcl_to_py('0'), 0)
        self.assertEqual(converter.tcl_to_py('42'), 42)
        self.assertEqual(converter.tcl_to_py('3.14'), 3.14)
        self.assertEqual(converter.tcl_to_py('hello'), 'hello')

    def test_tcl2py_lists(self):
        """测试列表 Tcl → Python 转换"""
        converter = ValueConverter()
        self.assertEqual(converter.tcl_to_py('[list 1 2 3]'), [1, 2, 3])
        self.assertEqual(converter.tcl_to_py('[list a b c]'), ['a', 'b', 'c'])


class TestDictOperations(unittest.TestCase):
    """测试字典操作类"""

    def test_yaml_loading(self):
        """测试 YAML 文件加载"""
        # 创建临时 YAML 文件
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False, mode='w') as f:
            f.write("""
server:
  host: localhost
  port: 8080
database:
  url: postgres://localhost/db
""")
            yaml_file = f.name

        try:
            dict_ops = DictOperations()
            result = dict_ops.load_yaml(yaml_file)

            self.assertEqual(result['server']['host'], 'localhost')
            self.assertEqual(result['server']['port'], 8080)
            self.assertEqual(result['database']['url'], 'postgres://localhost/db')
        finally:
            os.unlink(yaml_file)

    def test_variable_expansion(self):
        """测试变量引用展开"""
        # 创建包含变量引用的 YAML 文件
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False, mode='w') as f:
            f.write("""
base_url: "http://example.com"
api_url: "${base_url}/api"
port: 8080
admin_port: $port
""")
            yaml_file = f.name

        try:
            dict_ops = DictOperations()
            result = dict_ops.load_yaml(yaml_file, expand_variables=True)

            self.assertEqual(result['base_url'], 'http://example.com')
            self.assertEqual(result['api_url'], 'http://example.com/api')
            self.assertEqual(result['admin_port'], '8080')  # string 类型，展开后仍是 string
        finally:
            os.unlink(yaml_file)


class TestTclBridge(unittest.TestCase):
    """测试 Tcl 桥接器"""

    def test_dict_to_interp(self):
        """测试 Python 字典到 Tcl 解释器的转换"""
        bridge = TclBridge()
        data = {
            'server': {'host': 'localhost', 'port': 8080},
            'enabled': True,
            'ports': [80, 443, 8080]
        }

        interp = bridge.dict_to_interp(data)

        # 验证变量设置
        self.assertEqual(interp.eval('set server(host)'), 'localhost')
        self.assertEqual(interp.eval('set server(port)'), '8080')
        self.assertEqual(interp.eval('set enabled'), '1')

    def test_interp_to_dict(self):
        """测试 Tcl 解释器到 Python 字典的转换"""
        bridge = TclBridge()
        data = {
            'server': {'host': 'localhost', 'port': 8080},
            'enabled': True,
            'ports': [80, 443, 8080]
        }

        # 转换到 Tcl 解释器
        interp = bridge.dict_to_interp(data)

        # 转换回 Python 字典
        result = bridge.interp_to_dict()

        # 验证数据
        self.assertEqual(result['server']['host'], 'localhost')
        self.assertEqual(result['server']['port'], 8080)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['ports'], [80, 443, 8080])

    def test_roundtrip_conversion(self):
        """测试往返转换（Python → Tcl → Python）"""
        bridge = TclBridge()
        original_data = {
            'string': 'hello',
            'number': 42,
            'float': 3.14,
            'bool': True,
            'none': None,
            'list': [1, 2, 3],
            'nested': {'a': 1, 'b': [2, 3]}
        }

        # Python → Tcl
        interp = bridge.dict_to_interp(original_data)

        # Tcl → Python
        result_data = bridge.interp_to_dict()

        # 验证数据一致性
        self.assertEqual(result_data['string'], 'hello')
        self.assertEqual(result_data['number'], 42)
        self.assertEqual(result_data['float'], 3.14)
        self.assertTrue(result_data['bool'])
        self.assertIsNone(result_data['none'])
        self.assertEqual(result_data['list'], [1, 2, 3])
        self.assertEqual(result_data['nested']['a'], 1)
        self.assertEqual(result_data['nested']['b'], [2, 3])

    def test_rejects_unsafe_tcl_key(self):
        """危险 Tcl 变量名应被拒绝，避免注入。"""
        bridge = TclBridge()
        with self.assertRaises(ConversionError):
            bridge.dict_to_interp({'bad;name': 'value'})


class TestBackwardCompatibility(unittest.TestCase):
    """测试向后兼容性"""

    def test_value_format_functions(self):
        """测试值格式转换函数"""
        # 使用函数式接口
        self.assertEqual(value_format_py2tcl(None), '""')
        self.assertEqual(value_format_py2tcl(42), '42')
        self.assertEqual(value_format_tcl2py('42'), 42)
        self.assertEqual(value_format_tcl2py('[list 1 2 3]'), [1, 2, 3])

    def test_merge_dict_function(self):
        """测试字典合并函数"""
        dict1 = {'a': 1, 'b': {'c': 2}}
        dict2 = {'b': {'d': 3}, 'e': 4}
        result = merge_dict(dict1, dict2)
        self.assertEqual(result, {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4})

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
