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
    files_to_tcl,
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

class TestFilesToTcl(unittest.TestCase):
    """files_to_tcl 函数测试"""

    def test_basic_yaml_to_tcl(self):
        """单个 YAML 文件转 Tcl"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "config.yaml"
            out = tmp_path / "config.tcl"
            src.write_text(
                "pv_calibre:\n  lsf:\n    cpu_num: 4\n",
                encoding="utf-8",
            )
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set pv_calibre(lsf,cpu_num) {4}", content)

    # ---- 类型编码正确性 ----

    def test_bool_true_encoded_as_1(self):
        """YAML true 应编码为 Tcl 1，而非字符串 True"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "c.tcl"
            src.write_text("lsf_mode: true\n", encoding="utf-8")
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set lsf_mode {1}", content)
            self.assertNotIn("True", content)

    def test_bool_false_encoded_as_0(self):
        """YAML false 应编码为 Tcl 0"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "c.tcl"
            src.write_text("debug: false\n", encoding="utf-8")
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set debug {0}", content)
            self.assertNotIn("False", content)

    def test_list_encoded_as_tcl_list_command(self):
        """YAML list 应编码为 [list ...] 命令，而非字面字符串"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "c.tcl"
            src.write_text("extra_args:\n  - -verbose\n  - -turbo\n", encoding="utf-8")
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            # 必须是 set ... [list ...] 而非 set ... {[list ...]}
            self.assertIn("set extra_args [list", content)
            self.assertNotIn("set extra_args {[list", content)

    def test_string_with_spaces_brace_quoted(self):
        """含空格的字符串用花括号保护"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "c.tcl"
            src.write_text('msg: "hello world"\n', encoding="utf-8")
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set msg {hello world}", content)

    def test_var_ref_expanded_in_strings(self):
        """字符串中的 $var 引用在写出时展开"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.yaml"
            overlay = tmp_path / "overlay.yaml"
            out = tmp_path / "out.tcl"
            base.write_text("base_path: /work/proj\n", encoding="utf-8")
            overlay.write_text("report_dir: $base_path/reports\n", encoding="utf-8")
            files_to_tcl(base, overlay, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set report_dir {/work/proj/reports}", content)

    def test_int_not_brace_wrapped(self):
        """整数值直接写出，无需花括号（Tcl 可正确识别）"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "c.tcl"
            src.write_text("cpu_num: 8\n", encoding="utf-8")
            files_to_tcl(src, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("set cpu_num {8}", content)

    def test_overlay_marks_override_and_new(self):
        """后层文件覆盖前层时标注 [override]，新增变量标注 [new]"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            base = tmp_path / "base.yaml"
            overlay = tmp_path / "overlay.yaml"
            out = tmp_path / "out.tcl"
            base.write_text("cpu_num: 4\n", encoding="utf-8")
            overlay.write_text("cpu_num: 8\nextra: yes\n", encoding="utf-8")
            files_to_tcl(base, overlay, output_file=out)
            content = out.read_text(encoding="utf-8")
            self.assertIn("[override]", content)
            self.assertIn("[new]", content)

    def test_edp_vars_written_to_header(self):
        """edp_vars 写入文件头"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "c.yaml"
            out = tmp_path / "out.tcl"
            src.write_text("k: v\n", encoding="utf-8")
            files_to_tcl(src, output_file=out, edp_vars={"foundry": "SAMSUNG"})
            content = out.read_text(encoding="utf-8")
            self.assertIn("set edp(foundry) {SAMSUNG}", content)

    def test_missing_file_warns_and_skips(self):
        """不存在的输入文件发出警告并跳过，不崩溃"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out = tmp_path / "out.tcl"
            import logging
            with self.assertLogs("configkit.core.tcl_file_emit", level="WARNING") as cm:
                files_to_tcl(
                    tmp_path / "nonexistent.yaml",
                    output_file=out,
                )
            self.assertTrue(any("nonexistent" in msg for msg in cm.output))

    def test_list_of_dicts_raises(self):
        """list 内嵌 dict 应抛出 ValueError"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "bad.yaml"
            out = tmp_path / "out.tcl"
            src.write_text(
                "items:\n  - key: val\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                files_to_tcl(src, output_file=out)


class TestTclBridgeExtra(unittest.TestCase):
    """TclBridge 补充测试"""

    def test_save_tcl_file_requires_output(self):
        """save_tcl_file 不传 output_file 应抛出 ValueError"""
        bridge = TclBridge()
        bridge.dict_to_interp({"x": 1})
        with self.assertRaises(ValueError):
            bridge.save_tcl_file()

    def test_save_and_reload(self):
        """save_tcl_file 写出后可被 load_tcl_file 读回"""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.tcl"
            bridge = TclBridge()
            bridge.dict_to_interp({"a": {"b": 42}})
            bridge.save_tcl_file(output_file=out)
            result = bridge.load_tcl_file(out)
            self.assertEqual(result["a"]["b"], 42)

    def test_merge_and_expand_preserves_base_types(self):
        """merge_and_expand 第二次加载不清空 base 的类型元数据"""
        bridge = TclBridge()
        base = {"count": 3}
        overlay = {"label": "hello"}
        result = bridge.merge_and_expand(base, overlay)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["label"], "hello")

    def test_merge_and_expand_overlay_overrides(self):
        """merge_and_expand overlay 值覆盖 base 值"""
        bridge = TclBridge()
        result = bridge.merge_and_expand({"x": 1}, {"x": 99})
        self.assertEqual(result["x"], 99)


if __name__ == '__main__':
    unittest.main(verbosity=2)
