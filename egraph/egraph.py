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
    def to_graph(self, current=None, id_counter=1):
        """
        Возвращает часть регулярного выражения в Dot-представлении.

        :param DotNode current: Предыдущий узел.
        :param id_counter: Счётчик id.
        """
        pass

    def _set_id_if_not_exist(self, id_counter):
        """
        Устанавливает id, если тот не установлен. В случае установки возвращает id+1.

        :param int id_counter: Значение устанавливаемое id.
        :rtype : int
        """
        if self._id is None:
            self._id = id_counter
            id_counter += 1
        return id_counter

    @staticmethod
    def _link_with_previous_if_exist(current, id_counter, node, result):
        """
        Связывает 2 DotNode с помощью DotLink, если первый не None,
        и добавляет созданную связь в список.

        :param DotNode|None current: Первый узел.
        :param int id_counter: Счётчик id.
        :param DotNode|None node: Второй узел.
        :param list[IDotable] result: Список частей dot-графа.
        :rtype : int
        """
        if current is not None:
            result.append(DotLink(current, node, id_counter))
            id_counter += 1
        return id_counter


class PartContainer(Part, metaclass=abc.ABCMeta):
    """
    Абстрактный класс контейнера частей в объясняющем графе.
    (по сути альтернатива конкатенаций)
    """

    def __init__(self, id=None):
        Part.__init__(self, id)
        self._branches = []
        """:type : list[list[Part]]"""

    def add_branch(self, branch):
        """
        :param list[Part] branch: Новая ветка для альтернативы.
        """
        self._branches.append(branch)

    def __getitem__(self, item):
        return self._branches[item]

    def __iter__(self):
        for branch in self._branches:
            yield branch

    @abc.abstractmethod
    def to_graph(self, current=None, id_counter=1):
        pass


class ExplainingGraph(PartContainer):
    """
    Модель объясняющего графа.
    """

    def __init__(self):
        PartContainer.__init__(self, "explaining_graph")
        self._id_counter = 1

    def to_graph(self, current=None, id_counter=1):
        """
        :rtype : DotDigraph
        """
        graph = DotDigraph(self._id)

        begin = DotNode(self._id_counter, "begin", 'filled', "purple", "begin", "rect", "purple")
        self._id_counter += 1
        graph.items.append(begin)
        end = DotNode(self._id_counter, "end", 'filled', "purple", "end", "rect", "purple")
        self._id_counter += 1
        graph.items.append(end)

        current = begin
        if len(self._branches) == 1:
            branch = self._branches[0]
            for item in branch:
                parts, new_current, new_id = item.to_graph(current=current, id_counter=self._id_counter)
                graph.items += parts
                self._id_counter = new_id
                current = new_current
        else:
            start = DotNode(self._id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white")
            self._id_counter += 1
            finish = DotNode(self._id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white")
            self._id_counter += 1

            graph.items += [start, finish]
            self._id_counter = self._link_with_previous_if_exist(current, self._id_counter, start, graph.items)

            for branch in self._branches:
                current = start
                for item in branch:
                    parts, new_current, new_id = item.to_graph(current=current, id_counter=self._id_counter)
                    graph.items += parts
                    self._id_counter = new_id
                    current = new_current

                graph.items.append(DotLink(current, finish, self._id_counter))
                self._id_counter += 1

            current = finish

        graph.items.append(DotLink(current, end, self._id_counter))
        self._id_counter += 1

        ExplainingGraph._optimize(graph)

        return graph

    @staticmethod
    def _optimize(graph: DotDigraph):
        pass


class Text(Part):
    """
    Простой текст в регулярном выражении.
    """

    def __init__(self, txt="", id=None):
        Part.__init__(self, id=id)
        self._txt = txt

    @property
    def text(self) -> str:
        return self._txt

    @text.setter
    def text(self, value: str) -> None:
        self._txt = value

    def to_graph(self, current=None, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(self._id, self.text)
        result = [node]
        id_counter = self._link_with_previous_if_exist(current, id_counter, node, result)
        current = node
        return result, current, id_counter


class BorderAssert(Part):
    """
    Представляет простое утверждение в регулярном выражении.
    """

    def __init__(self, id=None, inverse=False):
        Part.__init__(self, id=id)
        self.inverse = inverse

    def to_graph(self, current=None, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        text = "a word boundary" if not self.inverse else "not a word boundary"
        node = DotNode(self._id, text)
        result = [node]
        id_counter = self._link_with_previous_if_exist(current, id_counter, node, result)
        current = node
        return result, current, id_counter


class Subexpression(PartContainer):
    """
    Представляет подвыражение в регулярном выражении.
    """

    def __init__(self, id=None, number=0):
        PartContainer.__init__(self, id=id)
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int) -> None:
        self._number = value

    def to_graph(self, current=None, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        subgraph = DotSubgraph(id=self._id, label="subexpression #{0}".format(self.number), tooltip="subexpression")
        result = [subgraph]
        """:type : list[IDotable|DotLink]"""
        id_counter = self._link_with_previous_if_exist(current, id_counter, None, result)

        if len(self._branches) == 1:
            branch = self._branches[0]
            for item in branch:
                parts, new_current, new_id = item.to_graph(current=current, id_counter=id_counter)
                subgraph.items += parts
                id_counter = new_id
                current = new_current
        else:
            start = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white")
            id_counter += 1
            finish = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white")
            id_counter += 1

            subgraph.items += [start, finish]
            id_counter = self._link_with_previous_if_exist(current, id_counter, start, subgraph.items)

            for branch in self._branches:
                current = start
                for item in branch:
                    parts, new_current, new_id = item.to_graph(current=current, id_counter=id_counter)
                    subgraph.items += parts
                    id_counter = new_id
                    current = new_current

                subgraph.items.append(DotLink(current, finish, id_counter))
                id_counter += 1

            current = finish

        result[1].destination = subgraph.items[0]

        return result, current, id_counter
