from enum import Enum, auto


class State(Enum):
    OFF = auto()
    ON = auto()
    Z = auto()


class Pin:
    def __init__(self, x=0, y=0, state=State.Z):
        self._x = x
        self._y = y


class PluginComponent:
    """maybe function that runs every tick? but effish"""
    """or just on updates but that fucks clocks"""
    pass


class Component:
    def __init__(self, n_inputs, n_outputs):
        self._id = id()
        self._n_inputs = n_inputs
        self._n_outputs = n_outputs
        self._inputs = [Pin() for k in range(n_inputs)]
        self._outputs = [Pin() for k in range(n_outputs)]
        self._subcomponents: dict[int: Component] = {}
        # {(component_id, input_id, value): time}
        self._schedule_: dict[tuple(int, int, int): int] = {}

    def _schedule(self, component_id, input_id, value, time):
        self._schedule_[(component_id, input_id, value)] = time

    def _set_input(self, iid, value):
        assert self._n_inputs > iid, f"Input ID {iid} is too large"
        self._inputs[iid] = value

    def _tick(self):
        for key in self._schedule_:
            if self._schedule_[key] == 0:
                cid, iid, value = key
                c: Component = self._subcomponents.get(cid)
                assert c, f"Found no subcomponent with id {cid}"
                c._set_input(iid, value)
            self._schedule_[key] -= 1
            # After trigger (t=0), time becomes negative
            # This enables potential tracking / last activation time
