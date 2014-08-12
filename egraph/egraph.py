__author__ = 'Владимир'

import abc


class IGroup(metaclass=abc.ABCMeta):
    """
    Абстрактный класс контейнера в объясняюшем графе.
    """

    def __init__(self):
        self._parts = []
        self._tooltip = ""
        self._id = None

    def add_part(self, part):
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

    def to_dot(self) -> str:
        level = 1

        result = "digraph \"" + self._name + "\" {\n" \
        + ("\t"*level) + "tooltip=\"" + self._tooltip + "\";\n" \
        + ("\t"*level) + "id=\"" + self._id + "\";\n" \
        + ("\t"*level) + "compound=" + self._compound + ";\n" \
        + ("\t"*level) + "rankdir = " + self._compound + ";\n" + "\n"

        result += ("\t"*level) + '"begin" [color=purple, shape=box, style=filled];\n'
        result += ("\t"*level) + '"end" [color=purple, shape=box, style=filled];\n'

        return result + "}"


class Cluster(IGroup, metaclass=abc.ABCMeta):
    """
    Подграф в объясняющем графе.
    """

    def __init__(self):
        IGroup.__init__(self)
        self._bgcolor = ""
        self._style = ""
        self._label = ""


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

    def to_dot(self) -> str:
        """
        Получает dot-представление данного узла.
        """
        raise NotImplementedError

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

    def __init__(self, src=None, dst=None):
        self._source = src
        self._destination = dst
        self._label = ""
        self._id = -1
        self._color = ""
        self._tooltip = ""
        self._arrowhead = ""

    def to_dot(self) -> str:
        """
        Получает dot-представление данного ребра.
        """
        raise NotImplementedError

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