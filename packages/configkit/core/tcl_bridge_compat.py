#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigKit TclBridge 向后兼容函数入口。
"""

from pathlib import Path
from tkinter import Tcl
from typing import Any, Dict, Optional, Union

from ..exceptions import TclError
from ..types import ConversionMode
from .tcl_bridge import TclBridge


def dict2tclinterp(data: Dict[str, Any], interp: Optional[Tcl] = None) -> Tcl:
    """Python 字典转 Tcl 解释器（向后兼容函数）。"""
    bridge = TclBridge(interp=interp)
    return bridge.dict_to_interp(data)


def tclinterp2dict(interp: Tcl,
                   mode: ConversionMode = ConversionMode.AUTO) -> Dict[str, Any]:
    """Tcl 解释器转 Python 字典（向后兼容函数）。"""
    bridge = TclBridge(interp=interp)
    return bridge.interp_to_dict(mode=mode)


def tclinterp2tclfile(interp: Tcl, output_file: Union[str, Path]) -> None:
    """Tcl 解释器转 Tcl 文件（向后兼容函数）。"""
    bridge = TclBridge(interp=interp)
    bridge.save_tcl_file(output_file=output_file)


def tclfiles2tclinterp(*tcl_files: Union[str, Path]) -> Tcl:
    """Tcl 文件转 Tcl 解释器（向后兼容函数）。"""
    result_interp = Tcl()

    for tcl_file in tcl_files:
        try:
            result_interp.eval(f"source {{{tcl_file}}}")
        except Exception as e:
            raise TclError(
                f"Failed to load Tcl file: {str(e)}",
                tcl_command=f"source {{{tcl_file}}}",
                context={'file_path': str(tcl_file)}
            )

    return result_interp


def expand_variable_references(interp: Tcl) -> None:
    """展开 Tcl 解释器中的变量引用（向后兼容函数）。"""
    bridge = TclBridge(interp=interp)
    bridge.expand_variables()


def files2tcl(*input_files: Union[str, Path],
              output_file: Union[str, Path],
              edp_vars: Optional[Dict[str, str]] = None) -> Path:
    """向后兼容入口：委托给 TclBridge.files_to_tcl。"""
    bridge = TclBridge()
    return bridge.files_to_tcl(
        *input_files,
        output_file=output_file,
        edp_vars=edp_vars,
    )
