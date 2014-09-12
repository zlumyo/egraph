__author__ = 'Владимир'

import abc


class IDotable(metaclass=abc.ABCMeta):
    """
    Абстрактный класс чего-то, что можно преобразовать в dot-код.
    Объединяет атрибуты общие для всех объектов в dot-коде.
    """

    def __init__(self, id=-1, label='', style=''):
        self._id = id
        self._label = label
        self.style = style

    @property
    def id(self):
        return '"graphid_{0}"'.format(self._id)

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def label(self):
        return '"{0}"'.format(self._label)

    @label.setter
    def label(self, value):
        self._label = value

    @abc.abstractmethod
    def to_dot(self, level=0):
        pass


class IGroupable(IDotable, metaclass=abc.ABCMeta):
    """
    Абстрактный контейнер dot-сущностей.
    """

    def __init__(self, id=-1, label='', style='', bgcolor=''):
        IDotable.__init__(self, id, label, style)
        self.items = []
        self.bgcolor = bgcolor

    def to_dot(self, level=0):
        level += 1
        result = self._initial(level)

        result += ''.join([
            ('\t' * level) + (item.to_dot(level) if isinstance(item, DotSubgraph) else item.to_dot(level + 1)) + '\n'
            for item in self.items
        ])

        level -= 1
        return result + ('\t' * level) + '}'

    @abc.abstractmethod
    def _initial(self, level):
        pass

    def find_neighbor_right(self, item):
        for link in filter(lambda i: isinstance(i, DotLink), self.items):
            if link.source is item:
                return link.destination

        for subgraph in filter(lambda i: isinstance(i, DotSubgraph), self.items):
            result = subgraph.find_neighbor_right(item)
            if result is not None:
                return result
        else:
            return None

    def find_neighbor_left(self, item):
        for link in filter(lambda i: isinstance(i, DotLink), self.items):
            if link.destination is item:
                return link.source

        for subgraph in filter(lambda i: isinstance(i, DotSubgraph), self.items):
            result = subgraph.find_neighbor_right(item)
            if result is not None:
                return result
        else:
            return None

    def find_link(self, source, destination):
        for link in filter(lambda i: isinstance(i, DotLink), self.items):
            if link.destination is destination and link.source is source:
                return link, self

        for subgraph in filter(lambda i: isinstance(i, DotSubgraph), self.items):
            result, owner = subgraph.find_link(source, destination)
            if result is not None:
                return result, owner
        else:
            return None, None

    def find_node_owner(self, node):
        for item in filter(lambda i: isinstance(i, DotNode), self.items):
            if node is item:
                return self

        for subgraph in filter(lambda i: isinstance(i, DotSubgraph), self.items):
            result = subgraph.find_node_owner(node)
            if result is not None:
                return result
        else:
            return None


class DotNode(IDotable):
    """
    Узел в dot-коде.
    """

    def __init__(self, id=-1, label='', style='', color='', tooltip='', shape='', fillcolor='',
                 comment=''):
        IDotable.__init__(self, id, label, style)
        self.shape = shape
        self.fillcolor = fillcolor
        self.color = color
        self._tooltip = tooltip
        self._comment = comment

    @property
    def comment(self):
        return '"{0}"'.format(self._comment)

    @comment.setter
    def comment(self, value):
        self._comment = value

    @property
    def tooltip(self):
        return '"{0}"'.format(self._tooltip)

    @tooltip.setter
    def tooltip(self, value):
        self._tooltip = value

    def to_dot(self, level=0):
        #TODO label и tooltip эскейпить на html
        attrs = filter(lambda i: i[1] != '', {
            'id': self.id,
            'label': self.label,
            'style': self.style,
            'shape': self.shape,
            'fillcolor': self.fillcolor,
            'color': self.color,
            'tooltip': self.tooltip,
            'comment': self.comment
        }.items())

        return '"nd_{0}" ['.format(self._id) + \
               ', '.join([k + '=' + v for k, v in attrs]) + ']'


class DotLink(IDotable):
    """
    Связь в dot-коде.
    """

    def __init__(self, source: DotNode, destination: DotNode, id=-1, label='', style='', color='', tooltip='',
                 arrowhead='', comment=''):
        IDotable.__init__(self, id, label, style)
        self.source = source
        self.destination = destination
        self.arrowhead = arrowhead
        self.color = color
        self._tooltip = tooltip
        self._comment = comment

    @property
    def comment(self):
        return '"{0}"'.format(self._comment)

    @comment.setter
    def comment(self, value):
        self._comment = value

    @property
    def tooltip(self):
        return '"{0}"'.format(self._tooltip)

    @tooltip.setter
    def tooltip(self, value):
        self._tooltip = value

    def to_dot(self, level=0):
        #TODO label и tooltip эскейпить на html
        attrs = filter(lambda i: i[1] != '', {
            'id': self.id,
            'label': self.label,
            'style': self.style,
            'color': self.color,
            'tooltip': self.tooltip,
            'comment': self.comment,
            'arrowhead': self.arrowhead
        }.items())

        return '"nd_{0}" -> "nd_{1}" ['.format(self.source._id, self.destination._id) + \
               ', '.join([k + '=' + v for k, v in attrs]) + ']'


class DotSubgraph(IGroupable):
    """
    Подграф в dot-коде.
    """

    def __init__(self, id=-1, label='', style='', bgcolor='', color='', tooltip=''):
        IGroupable.__init__(self, id, label, style, bgcolor)
        self.color = color
        self._tooltip = tooltip
        self.edge_attrs = {}

    @property
    def tooltip(self):
        return '"{0}"'.format(self._tooltip)

    @tooltip.setter
    def tooltip(self, value):
        self._tooltip = value

    def _initial(self, level=0):
        attrs = filter(lambda i: i[1] != '', {
            'id': self.id,
            'label': self.label,
            'style': self.style,
            'color': self.color,
            'tooltip': self.tooltip,
            'bgcolor': self.bgcolor
        }.items())

        result = ('\n' + '\t' * level).join(
            ['subgraph "cluster_{0}" {{'.format(self._id)] +
            [k+'='+v for k, v in attrs] +
            [self._get_edge_attrs()]
        )

        return '\t' * (level - 2) + result + '\n'

    def _get_edge_attrs(self):
        if len(self.edge_attrs) != 0:
            result = 'edge ['

            result += ', '.join(['{0}="{1}"'.format(k, v) for k, v in self.edge_attrs.items()])

            return result + '];'
        else:
            return ''


class DotDigraph(IGroupable):
    """
    Главный граф в dot-коде.
    """

    def __init__(self, id=-1, label='', style='', bgcolor=''):
        # noinspection PyTypeChecker
        IGroupable.__init__(self, 'explaining_graph', label, style, bgcolor)
        self.items = []
        self.compound = 'true'
        self.rankdir = 'LR'

    def _initial(self, level=1):
        level = 1

        attrs = filter(lambda i: i[1] != '', {
            'bgcolor': self.bgcolor,
            'compound': self.compound,
            'rankdir': self.rankdir
        }.items())

        result = ('\n' + '\t' * level).join(
            ['digraph "{0}" {{'.format(self._id)] + [k+'='+v for k, v in attrs]
        )

        return '\t' * (level - 1) + result + '\n'