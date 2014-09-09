__author__ = 'Владимир'

from egraph.dot import *
from enum import Enum


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

        :param DotNode|None current: Предыдущий узел.
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

        ExplainingGraph._optimize(graph, graph)

        return graph

    @staticmethod
    def _optimize(graph: IGroupable, main: DotDigraph):
        ExplainingGraph._optimize_simple_characters(graph, main)
        ExplainingGraph._optimize_asserts(graph, main)

        for item in graph.items:
            if isinstance(item, IGroupable):
                ExplainingGraph._optimize(item, main)

    @staticmethod
    def _optimize_simple_characters(graph: IGroupable, main: DotDigraph):
        while True:
            for item in filter(lambda i: isinstance(i, DotNode), graph.items):
                if item.comment != Text.__name__:
                    continue

                neighbor = main.find_neighbor_right(item)
                owner = main.find_node_owner(neighbor)
                # If neighbor is simple node with text too and it's a child of the same subgraph,
                # then we need to join this two nodes.
                if neighbor is not None and neighbor.comment == Text.__name__ and owner == graph:
                    if type(item) is str and type(neighbor) is str:
                        ids_this = item.id.split('_')
                        ids_neighbor = neighbor.id.split('_')
                        ids_new = ids_this[0] + '_' + ids_this[1] + '_' + ids_neighbor[2]
                    else:
                        ids_new = item.id

                    item.label += neighbor.label
                    item.tooltip += neighbor.label
                    item.id = ids_new

                    # Destroy old node.
                    owner.items.remove(neighbor)

                    # Find a link between current node and neighbor, then change destination to node after neighbor.
                    link, _ = main.find_link(item, neighbor)
                    after, _ = main.find_neighbor_right(neighbor)
                    link.destination = after

                    # Destroy old link.
                    link, owner = main.find_link(neighbor, after)
                    if owner is not None:
                        owner.items.remove(link)

                    break
            else:
                break

    @staticmethod
    def _compute_label(label1, label2):
        empty = ''
        if label1 == empty and label2 == empty:
            return empty
        elif label1 == empty:
            return label2
        elif label2 == empty:
            return label1
        else:
            return label1 + '\n' + label2

    @staticmethod
    def _optimize_asserts(graph: IGroupable, main: DotDigraph):
        while True:
            # Lets find an assert.
            for _assert in filter(lambda i: isinstance(i, DotNode) and i.comment == Assert.__name__, graph.items):
                need_to_break = False
                # Find its neighbors (left and right).
                right_neighbor = main.find_neighbor_right(_assert)
                right_owner = main.find_node_owner(right_neighbor)
                left_neighbor = main.find_neighbor_left(_assert)
                left_owner = main.find_node_owner(left_neighbor)

                # First case - both neighbors are in same subgraph.
                if right_neighbor is not None and left_owner is right_owner and right_owner is graph:
                    # Find links between neighbors and assert.
                    left_link, _ = main.find_link(left_neighbor, _assert)
                    right_link, owner = main.find_link(_assert, right_neighbor)

                    left_link.destination = right_link.destination
                    left_link.label = ExplainingGraph._compute_label(left_link.label, _assert.label)
                    left_link.tooltip = left_link.label

                    owner.items.remove(right_link)
                    graph.items.remove(_assert)
                    need_to_break = True
                # Second case - neighbors are not in the same subgraphs, but right neighbor is in same as assert.
                elif right_neighbor is not None and right_owner is not left_owner \
                        and left_owner is not graph and right_owner is graph:
                    right_link, _ = main.find_link(_assert, right_neighbor)
                    right_link.label = ExplainingGraph._compute_label(_assert.label, right_link.label)
                    right_link.tooltip = right_link.label
                    _assert.shape = 'point'
                    _assert.label = ''
                # Third case - neighbors are not in the same subgraphs, but left neighbor is in same as assert.
                elif right_neighbor is not None and right_owner is not left_owner \
                        and left_owner is graph and right_owner is not graph:
                    left_link, _ = main.find_link(left_neighbor, _assert)
                    left_link.label = ExplainingGraph._compute_label(left_link.label, _assert.label)
                    left_link.tooltip = left_link.label
                    _assert.shape = 'point'
                    _assert.label = ''
                else:  # Fourth case - neighbors are not in the same subgraphs and no one in current subgraph.
                    # If right neighbor is existing...
                    if right_neighbor is not None:
                        # Find links between neighbors and assert.
                        left_link, _ = main.find_link(left_neighbor, _assert)
                        right_link, owner = main.find_link(_assert, right_neighbor)

                        left_link.destination = right_link.destination
                        left_link.label = _assert.label
                        left_link.tooltip = left_link.label

                        owner.items.remove(right_link)
                        graph.items.remove(_assert)
                    else:  # Right neighbor is not existing, so we just replace it with point-node.
                        point = DotNode(shape="point", comment="Point")
                        new_link = DotLink(_assert, point, _assert.label, tooltip=_assert.label)
                        _assert.shape = 'point'
                        _assert.label = ''

                        graph.items.extend([point, new_link])

                    need_to_break = True

                if need_to_break:
                    break
            else:
                break


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
        node = DotNode(self._id, self.text, tooltip=self.text, comment=Text.__name__)
        result = [node]
        id_counter = self._link_with_previous_if_exist(current, id_counter, node, result)
        current = node
        return result, current, id_counter


class AssertType(Enum):
    slash_b = 1
    slash_B = 2
    circumflex = 3
    dollar = 4


class Assert(Part):
    """
    Представляет простое утверждение в регулярном выражении.
    """

    def __init__(self, type: AssertType, id=None):
        Part.__init__(self, id=id)
        self._type = type

    @property
    def type(self) -> str:
        return self._type

    @type.setter
    def type(self, value: str) -> None:
        self._type = value

    _assert_strings = {
        AssertType.slash_b: "a word boundary",
        AssertType.slash_B: "not a word boundary",
        AssertType.circumflex: "start of the string",
        AssertType.dollar: "end of the string"
    }

    def to_graph(self, current=None, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        text = self._assert_strings[self.type]
        node = DotNode(self._id, text, comment=Assert.__name__)
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
                parts, new_current, new_id = item.to_graph(current=None, id_counter=id_counter)
                subgraph.items += parts
                id_counter = new_id
                current = new_current
        else:
            start = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                            comment="Point")
            id_counter += 1
            finish = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                             comment="Point")
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
