__author__ = 'Владимир'

import abc


class IGroup(metaclass=abc.ABCMeta):
    """
    Абстрактный класс контейнера в объясняющем графе.
    """

    def __init__(self):
        self._parts = []
        self._tooltip = ""
        self._id = None
        self._gmain = None

    def add_part(self, part):
        part.id = self._gmain._idcounter
        self._gmain._idcounter += 1
        if isinstance(part, IGroup):
            part._gmain = self._gmain
        self._parts.append(part)

    @abc.abstractmethod
    def to_dot(self) -> str:
        """
        Получает dot-представление данного контейнера.
        """
        pass

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


class ExplainingGraph(IGroup):
    """
    Модель объясняющего графа.
    """

    def __init__(self):
        IGroup.__init__(self)
        self._id = "explaining_graph"
        self._name = "explaining graph"
        self._compound = "true"
        self._rankdir = "LR"
        self._gmain = self
        self._idcounter = 1

    def to_dot(self) -> str:
        result = "digraph \"" + self._name + "\" {\n" \
            + "\t" + "tooltip=\"" + self._tooltip + "\";\n" \
            + "\t" + "id=\"" + str(self._id) + "\";\n" \
            + "\t" + "compound=" + self._compound + ";\n" \
            + "\t" + "rankdir=" + self._rankdir + ";\n\n"

        result += "\t" + '"begin" [color=purple, shape=box, style=filled];\n'
        result += "\t" + '"end" [color=purple, shape=box, style=filled];\n'

        state = ["begin", "", 1]
        iterfunc = lambda part, s: part.to_dot(s)
        return result + ''.join([iterfunc(part, state) for part in self._parts]) + \
            '\t"{0}" -> "end" [label="{1}"];\n}}'.format(state[0], state[1])


class Cluster(IGroup, metaclass=abc.ABCMeta):
    """
    Подграф в объясняющем графе.
    """

    def __init__(self):
        IGroup.__init__(self)
        self._bgcolor = "white"
        self._color = "black"
        self._style = "solid"
        self._label = ""

    def to_dot(self, state=None) -> str:
        margin_before = '\t'*state[2] if state is not None else ''
        state[2] += 1
        margin_after = margin_before + '\t'
        result = margin_before + 'subgraph "cluster_{0}" {{\n'.format(self._id) \
            + margin_after + 'style={0};\n'.format(self._style) \
            + margin_after + 'color={0};\n'.format(self._color) \
            + margin_after + 'bgcolor={0};\n'.format(self._bgcolor) \
            + margin_after + 'label="{0}";\n'.format(self._label) \
            + margin_after + 'id="graphid_{0}";\n\n'.format(self._id)

        if len(self._parts) != 0:
            result += ''.join([part.to_dot(state) for part in self._parts])
        elif state is not None:
            point_id = -1
            if self._gmain is not None:
                self._gmain._idcounter += 1
                point_id = self._gmain._idcounter

            result += margin_after + '"nd_{0}" [shape=point];\n'.format(point_id)
            result = margin_before + '"{0}" -> "nd_{1}";\n'.format(state[0], point_id) + result

            state[0] = "nd_{0}".format(point_id)

        state[2] -= 1
        return result + margin_before + '}\n'


class Node(metaclass=abc.ABCMeta):
    """
    Узел объясняющего графа.
    """

    def __init__(self):
        self._shape = ""
        self._color = ""
        self._style = ""
        self._label = ""
        self._id = -1
        self._fillcolor = ""

    def to_dot(self, state=None) -> str:
        """
        Получает dot-представление данного узла. Если state задано, то узел присоединяется к указанному в state.
        """
        result = '"nd_{0}" [shape={1}, id="graphid_{0}", color={2}, \
style={3}, label="{4}", fillcolor={5}, tooltip="{4}"];\n' \
        .format(
            self._id,
            self._shape,
            self._color,
            self._style,
            self._label,
            self._fillcolor
        )
        if state is not None:
            result = ("\t"*state[2]) + result + ("\t"*state[2]) + '"{0}" -> "nd_{1}" [label="{2}"];\n'\
                .format(state[0], self._id, state[1])
            state[0] = 'nd_' + str(self._id)

        return result

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


class Edge(metaclass=abc.ABCMeta):
    """
    Ребро в объясняющем графе.
    """

    def __init__(self):
        self._label = ""
        self._id = -1
        self._color = ""
        self._tooltip = ""
        self._arrowhead = ""

    def to_dot(self, state=None) -> str:
        """
        Получает dot-представление данного ребра.
        """
        if state is not None:
            state[1] += ('\n' if state[1] != '' else '') + self._label
        return ''

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value


class Alternative(IGroup):
    """
    Альтернатива в регулярном выражении.
    """

    def __init__(self):
        IGroup.__init__(self)
        self._tooltip = "alternative"
        self._id = -1

    def to_dot(self, state=None) -> str:
        """
        Получает dot-представление данной альтернативы.
        """
        raise NotImplementedError


class Text(Node):
    """
    Простой текст в регулярном выражении.
    """

    def __init__(self, txt=""):
        self._label = txt

        self._shape = "ellipse"
        self._color = "black"
        self._style = "solid"
        self._id = -1
        self._fillcolor = "white"


class BorderAssert(Edge):
    """
    Представляет простое утверждение в регулярном выражении.
    """

    def __init__(self, inverse=False):
        self._label = "a word boundary"
        self._id = -1
        self._color = "black"
        self._tooltip = "a word boundary"
        self._arrowhead = "normal"
        self._inverse = inverse

class Subexpression(Cluster):
    """
    Представляет подвыражение в регулярном выражении.
    """

    def __init__(self, number=0):
        Cluster.__init__(self)
        self._number = number
        self._label = "subexpression #{0}".format(number)
