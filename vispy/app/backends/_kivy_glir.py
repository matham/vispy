# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""
Vispy backend for Kivy.
"""

from __future__ import division

from ..base import (BaseApplicationBackend, BaseCanvasBackend,
                    BaseTimerBackend)
from ...util import logger, keys
from ...gloo.glir import GlirParser, convert_shader
from vispy.gloo import gl

# -------------------------------------------------------------------- init ---

capability = dict(  # things that can be set by the backend
    title=True,  # But it only applies to the dummy window :P
    size=True,  # We cannot possibly say we dont, because Canvas always sets it
    position=True,  # Dito
    show=True,
    vsync=False,
    resizable=True,
    decorate=True,
    fullscreen=True,
    context=False,
    multi_window=False,
    scroll=True,
    parent=False,
    always_on_top=False,
)

# Try importing Kivy
try:
    import kivy
    gl.use_gl('kivy')
except Exception as exp:
    available, testable, why_not, which = False, False, str(exp), None
else:
    available, testable, why_not, which = True, False, None, None


class ApplicationBackend(BaseApplicationBackend):

    def __init__(self):
        BaseApplicationBackend.__init__(self)

    def _vispy_reuse(self):
        pass

    def _vispy_get_backend_name(self):
        return 'kivy_glir'

    def _vispy_process_events(self):
        # TODO: may be implemented later.
        raise NotImplementedError()

    def _vispy_run(self):
        pass

    def _vispy_quit(self):
        pass

    def _vispy_get_native_app(self):
        return self


class KivyGlirParser(GlirParser):

    kivy_widget = None

    _kivy_gl_compat = 'es2'

    def set_kivy_widget(self, kivy_widget):
        self.kivy_widget = kivy_widget

    @property
    def shader_compatibility(self):
        if self._kivy_gl_compat is not None:
            return self._kivy_gl_compat

        try:
            from kivy.graphics.cgl import opengl_compatibility
            self._kivy_gl_compat = opengl_compatibility()
        except ImportError:
            self._kivy_gl_compat = 'es2'
        return self._kivy_gl_compat


class CanvasBackend(BaseCanvasBackend):
    # args are for BaseCanvasBackend, kwargs are for us.

    kivy_widget = None

    kivy_draw_trigger = None

    def __init__(self, *args, **kwargs):
        BaseCanvasBackend.__init__(self, *args)

        p = self._process_backend_kwargs(kwargs)
        self._context = p.context

        # TODO: do something with context.config
        # Take the context.
        p.context.shared.add_ref('kivy', self)
        if p.context.shared.ref is self:
            pass  # ok
        else:
            raise RuntimeError("WebGL doesn't yet support context sharing.")

        #self._vispy_canvas.context.shared.parser = KivyGlirParser()

        # only draw once at the end of the frame
        from kivy.clock import Clock
        self.kivy_draw_trigger = Clock.create_trigger(self._on_draw, -1)

    def link_kivy_widget(self, kivy_widget):
        self.kivy_widget = kivy_widget
        #self._vispy_canvas.context.shared.parser.set_kivy_widget(kivy_widget)

    def reinit_from_widget(self):
        assert self.kivy_widget is not None
        self._vispy_canvas.set_current()

        self._vispy_canvas.events.initialize()
        self._vispy_canvas.events.resize(size=self.kivy_widget.size)
        self.kivy_draw_trigger()

    def _vispy_warmup(self):
        pass

    # Uncommenting these makes the backend crash.
    def _vispy_set_current(self):
        pass

    def _vispy_swap_buffers(self):
        if self.kivy_widget is None:
            return
        self.kivy_widget.canvas.ask_update()
        # TODO: fill in
        return
        if self._vispy_canvas is None:
            return
        # Send frontend a special "you're allowed to swap buffers now" command
        context = self._vispy_canvas.context
        context.shared.parser.parse([('SWAP',)])

    def _vispy_set_title(self, title):
        raise NotImplementedError()

    def _vispy_get_fullscreen(self):
        # We don't want error messages to show up when the user presses
        # F11 to fullscreen the browser.
        pass

    def _vispy_set_fullscreen(self, fullscreen):
        # We don't want error messages to show up when the user presses
        # F11 to fullscreen the browser.
        pass

    def _vispy_get_size(self):
        if self.kivy_widget is None:
            return 100, 100
        return self.kivy_widget.size

    def _vispy_set_size(self, w, h):
        pass

    def _vispy_get_position(self):
        raise NotImplementedError()

    def _vispy_set_position(self, x, y):
        logger.warning('Kivy canvas cannot be repositioned.')

    def _vispy_set_visible(self, visible):
        logger.warning('Kivy canvas cannot be hidden/displayed.')

    def _vispy_update(self):
        if self.kivy_widget is None:
            return
        self.kivy_draw_trigger()

    def _on_draw(self, *largs):
        self._vispy_canvas.set_current()
        self._vispy_canvas.events.draw()

    def _vispy_close(self):
        raise NotImplementedError()

    def _vispy_mouse_release(self, **kwargs):
        # HACK: override this method from the base canvas in order to
        # avoid breaking other backends.
        kwargs.update(self._vispy_mouse_data)
        ev = self._vispy_canvas.events.mouse_release(**kwargs)
        if ev is None:
            return
        self._vispy_mouse_data['press_event'] = None
        # TODO: this is a bit ugly, need to improve mouse button handling in
        # app
        ev._button = None
        self._vispy_mouse_data['buttons'] = []
        self._vispy_mouse_data['last_event'] = ev
        return ev

    # Generate vispy events according to upcoming JS events
    _modifiers_map = {
        'ctrl': keys.CONTROL,
        'shift': keys.SHIFT,
        'alt': keys.ALT,
    }

    def _gen_event(self, ev):
        return
        if self._vispy_canvas is None:
            return
        event_type = ev['type']
        key_code = ev.get('key_code', None)
        if key_code is None:
            key, key_text = None, None
        else:
            if hasattr(keys, key_code):
                key = getattr(keys, key_code)
            else:
                key = keys.Key(key_code)
            # Generate the key text to pass to the event handler.
            if key_code == 'SPACE':
                key_text = ' '
            else:
                key_text = six.text_type(key_code)
        # Process modifiers.
        modifiers = ev.get('modifiers', None)
        if modifiers:
            modifiers = tuple([self._modifiers_map[modifier]
                               for modifier in modifiers
                               if modifier in self._modifiers_map])
        if event_type == "mouse_move":
            self._vispy_mouse_move(native=ev,
                                   button=ev["button"],
                                   pos=ev["pos"],
                                   modifiers=modifiers,
                                   )
        elif event_type == "mouse_press":
            self._vispy_mouse_press(native=ev,
                                    pos=ev["pos"],
                                    button=ev["button"],
                                    modifiers=modifiers,
                                    )
        elif event_type == "mouse_release":
            self._vispy_mouse_release(native=ev,
                                      pos=ev["pos"],
                                      button=ev["button"],
                                      modifiers=modifiers,
                                      )
        elif event_type == "mouse_wheel":
            self._vispy_canvas.events.mouse_wheel(native=ev,
                                                  delta=ev["delta"],
                                                  pos=ev["pos"],
                                                  button=ev["button"],
                                                  modifiers=modifiers,
                                                  )
        elif event_type == "key_press":
            self._vispy_canvas.events.key_press(native=ev,
                                                key=key,
                                                text=key_text,
                                                modifiers=modifiers,
                                                )
        elif event_type == "key_release":
            self._vispy_canvas.events.key_release(native=ev,
                                                  key=key,
                                                  text=key_text,
                                                  modifiers=modifiers,
                                                  )
        elif event_type == "resize":
            self._vispy_canvas.events.resize(native=ev,
                                             size=ev["size"])
        elif event_type == "paint":
            self._vispy_canvas.events.draw()


# ------------------------------------------------------------------- Timer ---
class TimerBackend(BaseTimerBackend):

    kivy_event = None

    def __init__(self, *args, **kwargs):
        super(TimerBackend, self).__init__(*args, **kwargs)
        from kivy.clock import Clock
        self.kivy_event = Clock.create_trigger(
            self._vispy_timer._timeout, 0, True)

    def _vispy_start(self, interval):
        self.kivy_event.timeout = interval
        self.kivy_event()

    def _vispy_stop(self):
        self.kivy_event.cancel()
