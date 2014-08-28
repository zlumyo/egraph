__author__ = 'Владимир'

import abc


class IDotable(metaclass=abc.ABCMeta):
    """
    Абстрактный класс чего-то, что можно преобразовать в dot-код.
    Объединяет атрибуты общие для всех объектов в dot-коде.
    """

    def __init__(self, id=-1, label='', style=''):
        self.id = id
        self.label = label
        self.style = style

    @abc.abstractmethod
    def to_dot(self, level=0):
        pass


class IGroupable(IDotable, metaclass=abc.ABCMeta):
    """
    Абстрактный контейнер dot-сущностей.
    """

    def __init__(self, id=-1, label='', style='solid', bgcolor='white'):
        IDotable.__init__(self, id, label, style)
        self.items = []
        self.bgcolor = bgcolor
        self.node_attrs = {}
        self.edge_attrs = {}

    def to_dot(self, level=0):
        level += 1
        result = self._initial(level)

        result += ''.join([('\t'*level) + item.to_dot(level+1) + '\n' for item in self.items])

        level -= 1
        return result + ('\t'*level) + '}'

    @abc.abstractmethod
    def _initial(self, level):
        pass


class DotNode(IDotable):
    """
    Узел в dot-коде.
    """

    def __init__(self, id=-1, label='', style='solid', color='black', tooltip='', shape='ellipse', fillcolor='white'):
        IDotable.__init__(self, id, label, style)
        self.shape = shape
        self.fillcolor = fillcolor
        self.color = color
        self.tooltip = tooltip

    def to_dot(self, level=0):
        # label и tooltip эскейпить на html
        return '"nd_{0}" [shape={1}, id="graphid_{0}", color={2}, style={3}, label="{4}", fillcolor={5},' \
               ' tooltip="{6}"];'\
            .format(self.id, self.shape, self.color, self.style, self.label, self.fillcolor, self.tooltip)


class DotLink(IDotable):
    """
    Связь в dot-коде.
    """

    def __init__(self, source: DotNode, destination: DotNode, id=-1, label='', style='solid', color='black', tooltip='',
                 arrowhead='normal'):
        IDotable.__init__(self, id, label, style)
        self.source = source
        self.destination = destination
        self.arrowhead = arrowhead
        self.color = color
        self.tooltip = tooltip

    def to_dot(self, level=0):
        return '"nd_{0}" -> "nd_{1}" [id="graphid_{2}", label="{3}", color="{4}", tooltip="{5}", ' \
               'arrowhead="{6}", style="{7}"]'\
            .format(
                self.source.id,
                self.destination.id,
                self.id,
                self.label,
                self.color,
                self.tooltip,
                self.arrowhead,
                self.style
            )


class DotSubgraph(IGroupable):
    """
    Подграф в dot-коде.
    """

    def __init__(self, id=-1, label='', style='solid', bgcolor='white', color='black', tooltip=''):
        IGroupable.__init__(self, id, label, style, bgcolor)
        self.entry = None
        self.exit = None
        self.color = color
        self.tooltip = tooltip

    def _initial(self, level=0):
        result = ('\t'*level+'\n').join([
            'subgraph "cluster_{0}" {',
            'style={1};',
            'color={2};',
            'bgcolor={3};',
            'label="{4}";',
            'id="graphid_{0}";',
            'tooltip="{5}";',
            self._get_node_attrs(),
            self._get_edge_attrs()
        ])

        return '\t'*(level-1) + result.format(self.id, self.style, self.color, self.bgcolor, self.label, self.tooltip)

    def _get_node_attrs(self):
        result = 'node ['

        result += ', '.join(['{0}="{1}"'.format(k, v) for k, v in self.node_attrs])

        return result + ']'

    def _get_edge_attrs(self):
        result = 'edge ['

        result += ', '.join(['{0}="{1}"'.format(k, v) for k, v in self.edge_attrs])

        return result + ']'


class DotDigraph(IGroupable):
    """
    Главный граф в dot-коде.
    """

    def __init__(self, id="explaining_graph", label='', style='solid', bgcolor='white'):
        IDotable.__init__(self, id, label, style)
        self.items = []
        self.bgcolor = bgcolor
        self.compound = 'true'
        self.rankdir = 'LR'

    def _initial(self, level=1):
        level = 1

        result = ('\n'+'\t'*level).join([
            'digraph "explaining graph" {{',
            'bgcolor={0};',
            'id="{1}";',
            'compound={2}',
            'rankdir={3}'
        ])

        return '\t'*(level-1) + result.format(self.bgcolor, self.id, self.compound, self.rankdir) + '\n'