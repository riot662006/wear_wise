# slider_helper.py
import cv2
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Union

Number = Union[int, float]
OnChange = Callable[[str, Number], None]
GlobalOnChange = Callable[[Dict[str, Number]], None]

@dataclass
class SliderSpec:
    name: str
    min: Number
    max: Number
    default: Number
    step: Number = 1
    on_change: Optional[OnChange] = None
    # If True, value is treated as float using integer trackbar under the hood
    as_float: bool = True

class SliderManager:
    """
    Fast creation of OpenCV trackbars with float support and clean callbacks.
    Usage:
        sm = SliderManager("Smart Mirror")
        sm.add_many([
            SliderSpec("Hue", 0, 360, 180, step=1),
            SliderSpec("Sat", 0, 255, 160, step=5),
            SliderSpec("Val", 0, 255, 200, step=5),
            SliderSpec("MaskTh", 0.0, 1.0, 0.5, step=0.01),
        ], on_any_change=lambda vals: print(vals))
        while True:
            # your drawing code...
            if cv2.waitKey(1) == 27:
                break
    """
    def __init__(self, window: str):
        self.window = window
        self._specs: Dict[str, SliderSpec] = {}
        self._int_max: Dict[str, int] = {}
        self._global_cb: Optional[GlobalOnChange] = None
        # Ensure window exists
        cv2.namedWindow(self.window, cv2.WINDOW_AUTOSIZE)

    def add(self, spec: SliderSpec) -> "SliderManager":
        if spec.max <= spec.min:
            raise ValueError(f"{spec.name}: max must be > min")
        # Decide int resolution for float sliders
        if spec.as_float:
            # choose resolution based on step (e.g., 0.01 -> 100 steps per unit)
            scale = max(1, int(round(1.0 / float(spec.step))))
            int_max = int(round((spec.max - spec.min) * scale))
        else:
            # integer slider: range directly
            if spec.step < 1:
                raise ValueError(f"{spec.name}: integer slider step must be >= 1")
            scale = 1
            int_max = int(round(spec.max - spec.min))
        self._int_max[spec.name] = int_max
        self._specs[spec.name] = spec

        # compute initial int position
        init_pos = self._to_int(spec.name, spec.default)

        def _cb(pos: int, _name: str=spec.name):
            # snap to step & emit callbacks
            val = self._to_value(_name, pos)
            # snap to declared step precisely
            snapped = self._snap(_name, val)
            # keep UI in sync if snapping moved it
            if snapped != val:
                self.set(_name, snapped)
            # per-slider callback
            s = self._specs[_name]
            if s.on_change:
                s.on_change(_name, snapped)
            # global callback with all current values
            if self._global_cb:
                self._global_cb(self.values())

        cv2.createTrackbar(spec.name, self.window, init_pos, int_max, _cb)
        # Ensure label shows default immediately (OpenCV calls callback once on creation in many builds,
        # but to be safe we call it explicitly)
        _cb(init_pos)
        return self

    def add_many(self, specs: list[SliderSpec], on_any_change: Optional[GlobalOnChange] = None) -> "SliderManager":
        self._global_cb = on_any_change
        for s in specs:
            self.add(s)
        return self

    def get(self, name: str) -> Number:
        pos = cv2.getTrackbarPos(name, self.window)
        return self._to_value(name, pos)

    def set(self, name: str, value: Number) -> None:
        pos = self._to_int(name, value)
        cv2.setTrackbarPos(name, self.window, pos)

    def values(self) -> Dict[str, Number]:
        return {n: self.get(n) for n in self._specs.keys()}

    # ---------- internals ----------
    def _to_int(self, name: str, value: Number) -> int:
        spec = self._specs[name]
        value = float(self._clamp(value, spec.min, spec.max))
        if spec.as_float:
            scale = max(1, int(round(1.0 / float(spec.step))))
            return int(round((value - spec.min) * scale))
        else:
            return int(round(value - spec.min))

    def _to_value(self, name: str, pos: int) -> Number:
        spec = self._specs[name]
        if spec.as_float:
            scale = max(1, int(round(1.0 / float(spec.step))))
            return spec.min + (pos / scale)
        else:
            return int(round(spec.min + pos))

    def _snap(self, name: str, value: Number) -> Number:
        spec = self._specs[name]
        if spec.as_float:
            steps = round((float(value) - float(spec.min)) / float(spec.step))
            snapped = float(spec.min) + steps * float(spec.step)
            return self._clamp(snapped, spec.min, spec.max)
        else:
            # integer step snapping
            steps = ((int(round(value)) - int(round(spec.min))) // int(round(spec.step)))
            snapped = int(round(spec.min)) + steps * int(round(spec.step))
            return int(self._clamp(snapped, spec.min, spec.max))

    @staticmethod
    def _clamp(v: Number, lo: Number, hi: Number) -> Number:
        return max(lo, min(hi, v))
