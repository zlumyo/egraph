__author__ = 'Владимир'

import abc


class IDotable(metaclass=abc.ABCMeta):
    """
    Абстрактный класс чего-то, что можно преобразовать в dot-код.
    """

    def __init__(self, id=-1, label='', color='', tooltip='', style=''):
        self.id = id
        self.label = label
        self.color = color
        self.tooltip = tooltip
        self.style = style

    @abc.abstractmethod
    def to_dot(self):
        pass


class DotNode(IDotable):
    """
    Узел в dot-коде.
    """

    def __init__(self, id=-1, label='', color='black', tooltip='', style='solid', shape='ellipse', fillcolor='white'):
        IDotable.__init__(self, id, label, color, tooltip, style)
        self.shape = shape
        self.fillcolor = fillcolor
        # self.owner = owner

    def to_dot(self):
        # label и tooltip эскейпить на html
        return '"nd_{0}" [shape={1}, id="graphid_{0}", color={2}, style={3}, label="{4}", fillcolor={5},' \
               ' tooltip="{6}"];'\
            .format(self.id, self.shape, self.color, self.style, self.label, self.fillcolor, self.tooltip)