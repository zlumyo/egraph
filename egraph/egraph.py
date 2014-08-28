__author__ = 'Владимир'

from egraph.dot import *


class Part(metaclass=abc.ABCMeta):
    """
    Абстрактная часть регулярного выражения.
    """

    def __init__(self):
        self._id = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @abc.abstractmethod
    def to_graph(self):
        pass


class PartContainer(Part, metaclass=abc.ABCMeta):
    """
    Абстрактный класс контейнера частей в объясняющем графе.
    (по сути конкатенация)
    """

    def __init__(self):
        self._parts = []
        self._gmain = None

    def add_part(self, part):
        if part.id is None:
            part.id = self._gmain._idcounter
        self._gmain._idcounter += 1
        if isinstance(part, PartContainer):
            part._gmain = self._gmain
        self._parts.append(part)

    @abc.abstractmethod
    def to_graph(self):
        pass


class ExplainingGraph(PartContainer):
    """
    Модель объясняющего графа.
    """

    def __init__(self):
        PartContainer.__init__(self)
        self._id = "explaining_graph"
        self._gmain = self
        self._idcounter = 1

    def to_graph(self):
        graph = DotDigraph()

        begin = DotNode(self._idcounter, "begin", 'filled', "purple", "begin", "rect", "purple")
        self._idcounter += 1
        graph.nodes.append(begin)
        end = DotNode(self._idcounter, "end", 'filled', "purple", "end", "rect", "purple")
        self._idcounter += 1
        graph.nodes.append(end)

        current = begin
        for item in self._parts:
            parts, current = item.to_graph(current)
            graph.items += parts


class Alternative(Part):
    """
    Альтернатива в регулярном выражении.
    """

    def __init__(self):
        Part.__init__(self)
        self.branches = set()

    def to_graph(self):
        pass
        

class Text(Part):
    """
    Простой текст в регулярном выражении.
    """

    def __init__(self, txt=""):
        Part.__init__(self)
        self.text = txt

    def to_graph(self):
        pass


class BorderAssert(Part):
    """
    Представляет простое утверждение в регулярном выражении.
    """

    def __init__(self, inverse=False):
        Part.__init__(self)
        self.inverse = inverse

    def to_graph(self):
        pass


class Subexpression(PartContainer):
    """
    Представляет подвыражение в регулярном выражении.
    """

    def __init__(self, number=0):
        PartContainer.__init__(self)
        self.number = number

    def to_graph(self):
        pass
