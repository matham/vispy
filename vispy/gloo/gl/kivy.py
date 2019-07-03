# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

""" GL ES 2.0 API implemented via Kivy library. Intended for use with Kivy.
"""

from kivy.graphics import opengl
from ...util import logger
import ctypes


def glBindAttribLocation(program, index, name):
    name = name.encode('utf-8')
    return opengl.glBindAttribLocation(program, index, name)


def glBufferData(target, data, usage):
    """ Data can be numpy array or the size of data to allocate.
    """
    if isinstance(data, int):
        size = data
        data = b''
    elif isinstance(data, bytes):
        size = len(data)
    else:
        size = data.nbytes
        data = data.tobytes()
    opengl.glBufferData(target, size, data, usage)


def glBufferSubData(target, offset, data):
    size = data.nbytes
    opengl.glBufferSubData(target, offset, size, data.tobytes())


def glCompressedTexImage2D(target, level, internalformat, width, height, border, data):
    # border = 0  # set in args
    size = data.size
    opengl.glCompressedTexImage2D(target, level, internalformat, width, height, border, size, data.tobytes())


def glCompressedTexSubImage2D(target, level, xoffset, yoffset, width, height, format, data):
    size = data.size
    opengl.glCompressedTexSubImage2D(target, level, xoffset, yoffset, width, height, format, size, data.tobytes())


def glTexImage2D(target, level, internalformat, format, type, pixels):
    border = 0
    if isinstance(pixels, (tuple, list)):
        height, width = pixels
        pixels = b''
    else:
        height, width = pixels.shape[:2]
    opengl.glTexImage2D(
        target, level, internalformat, width, height, border, format, type,
        pixels)


def glTexSubImage2D(target, level, xoffset, yoffset, format, type, pixels):
    height, width = pixels.shape[:2]
    opengl.glTexSubImage2D(
        target, level, xoffset, yoffset, width, height, format, type, pixels.tobytes())


def glDrawElements(mode, count, type, offset):
    if isinstance(offset, (int, ctypes.c_int)):
        offset = int(offset)
    return opengl.glDrawElements(mode, count, type, offset)


def glGetParameter(pname):
    if pname in [33902, 33901, 32773, 3106, 2931, 2928,
                 2849, 32824, 10752, 32938]:
        # GL_ALIASED_LINE_WIDTH_RANGE GL_ALIASED_POINT_SIZE_RANGE
        # GL_BLEND_COLOR GL_COLOR_CLEAR_VALUE GL_DEPTH_CLEAR_VALUE
        # GL_DEPTH_RANGE GL_LINE_WIDTH GL_POLYGON_OFFSET_FACTOR
        # GL_POLYGON_OFFSET_UNITS GL_SAMPLE_COVERAGE_VALUE
        return opengl.glGetFloatv(pname)
    elif pname in [7936, 7937, 7938, 35724, 7939]:
        # GL_VENDOR, GL_RENDERER, GL_VERSION, GL_SHADING_LANGUAGE_VERSION,
        # GL_EXTENSIONS are strings
        pass  # string handled below
    else:
        return opengl.glGetIntegerv(pname)
    res = opengl.glGetString(pname)
    return res.decode('utf-8')


def glGetUniform(program, location):
    n = 16
    d = float('Inf')
    params = (ctypes.c_float*n)(*[d for i in range(n)])
    opengl.glGetUniformfv(program, location, params)
    params = [p for p in params if p != d]
    if len(params) == 1:
        return params[0]
    else:
        return tuple(params)


def glGetVertexAttrib(index, pname):
    # From PyOpenGL v3.1.0 the glGetVertexAttribfv(index, pname) does
    # work, but it always returns 4 values, with zeros in the empty
    # spaces. We have no way to tell whether they are empty or genuine
    # zeros. Fortunately, pyopengl also supports the old syntax.
    n = 4
    d = float('Inf')
    params = (ctypes.c_float*n)(*[d for i in range(n)])
    opengl.glGetVertexAttribfv(index, pname, params)
    params = [p for p in params if p != d]
    if len(params) == 1:
        return params[0]
    else:
        return tuple(params)


def _make_unavailable_func(funcname):
    def cb(*args, **kwargs):
        raise RuntimeError('OpenGL API call "%s" is not available.' % funcname)
    return cb

def wrapper(func):
    def inner(*largs, **kwargs):
        print('calling', func)
        largs = [arg.encode() if isinstance(arg, str) else arg for arg in largs]
        res = func(*largs, **kwargs)
        if func.__name__ in ('glGetActiveAttrib', 'glGetActiveUniform'):
            return res[0].decode(), res[1], res[2]
        return res
    return inner

def _get_function_from_opengl(funcname):
    """ Try getting the given function from Kivy opengl, return
    a dummy function (that shows a warning when called) if it
    could not be found.
    """
    func = None

    # Get function from GL
    try:
        func = getattr(opengl, funcname)
    except AttributeError:
        func = None

    # Try using "alias"
    if not bool(func):
        # Some functions are known by a slightly different name
        # e.g. glDepthRangef, glClearDepthf
        if funcname.endswith('f'):
            try:
                func = getattr(opengl, funcname[:-1])
            except AttributeError:
                pass

    # Set dummy function if we could not find it
    if func is None:
        func = _make_unavailable_func(funcname)
        logger.warning('warning: %s not available' % funcname)
    return func


def _inject():
    """ Copy functions from opengl into this namespace.
    """
    ignore = {
        'gl_init_symbols', 'glBufferData', 'glTexImage2D', 'glTexSubImage2D',
        'glBindAttribLocation', 'glBufferSubData', 'glCompressedTexImage2D',
        'glCompressedTexSubImage2D', 'glGetVertexAttrib', 'glGetUniform',
        'glGetParameter', 'glDrawElements', }
    namespace = globals()

    for key, val in opengl.__dict__.items():
        if key in ignore:
            continue
        if key.startswith('GL_'):
            if isinstance(val, int):
                namespace[key] = val
        elif key.startswith('gl'):
            if callable(val):
                namespace[key] = wrapper(val)


_inject()
