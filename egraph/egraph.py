__author__ = 'Владимир'

from egraph.dot import *


class Part(metaclass=abc.ABCMeta):
    """
    Абстрактная часть регулярного выражения.
    """

    def __init__(self, id=None):
        self._id = id

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

    def __init__(self, id=None):
        Part.__init__(self, id)
        self._parts = []

    def add_part(self, part):
        self._parts.append(part)

    @abc.abstractmethod
    def to_graph(self, current=None, id_counter=1, label=''):
        pass


class ExplainingGraph(PartContainer):
    """
    Модель объясняющего графа.
    """

    def __init__(self):
        PartContainer.__init__(self, "explaining_graph")
        self._id_counter = 1

    def to_graph(self):
        graph = DotDigraph(self._id)

        begin = DotNode(self._id_counter, "begin", 'filled', "purple", "begin", "rect", "purple")
        self._id_counter += 1
        graph.items.append(begin)
        end = DotNode(self._id_counter, "end", 'filled', "purple", "end", "rect", "purple")
        self._id_counter += 1
        graph.items.append(end)

        current = begin
        label = ''
        for item in self._parts:
            parts, new_current, new_id, label = item.to_graph(current=current, label=label, id_counter=self._id_counter)
            graph.items += parts
            self._id_counter = new_id
            current = new_current

        graph.items.append(DotLink(current, end, self._id_counter))
        self._id_counter += 1

        return graph


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

    def __init__(self, txt="", id=None):
        Part.__init__(self)
        self.text = txt

    def to_graph(self, current=None, id_counter=1, label=''):
        if self._id is None:
            self._id = id_counter
            id_counter += 1
        node = DotNode(self._id, self.text)
        result = [node]
        if current is not None:
            # noinspection PyTypeChecker
            result.append(DotLink(current, node, id_counter, label))
            id_counter += 1
        current = node
        return result, current, id_counter, ""


class BorderAssert(Part):
    """
    Представляет простое утверждение в регулярном выражении.
    """

    def __init__(self, inverse=False):
        Part.__init__(self)
        self.inverse = inverse

    def to_graph(self, current=None, id_counter=1, label=''):
        text = "a word boundary" if not self.inverse else "not a word boundary"
        new_label = text if label == '' else label + '\\n' + text
        return [], current, id_counter, new_label


class Subexpression(PartContainer):
    """
    Представляет подвыражение в регулярном выражении.
    """

    def __init__(self, number=0):
        PartContainer.__init__(self)
        self.number = number

    def to_graph(self):
        pass
