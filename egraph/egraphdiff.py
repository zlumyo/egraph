__author__ = 'Владимир'

from egraph.egraph import *


def diffegraphs(egr1, egr2):
    result = DiffExplainingGraph()

    comprasions = find_comprasions(egr1, egr2)

    return result


def find_comprasions(cont1: PartContainer, cont2: PartContainer):
    result = []
    for branch1 in cont1:
        for branch2 in cont2:
            result.append((compare_branches(branch1, branch2), branch1, branch2))

    result.sort(lambda k: k[0])
    return result


def compare_branches(branch1: list, branch2: list):
    diff_index = 0

    i1 = i2 = 0
    for item1 in branch1:
        while i2 < len(branch2):
            if compare_items(item1, branch2[i2]):
                break
            i2 += 1
        else:
            diff_index += 1
        i1 += 1

    diff_index += abs(len(branch2)-len(branch1))
    return diff_index


def compare_items(item1: Part, item2: Part):
    if item1.__class__ != item2.__class__:
        return False
    else:
        return item1 == item2


class DiffExplainingGraph(IGraph):

    def __init__(self):
        IGraph.__init__(self, "diffegraph")


class DiffAlt(Part):
    """
    Разница в виде альтернативы.
    """

    def __init__(self, id=None):
        Part.__init__(self, id)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "diff",
            tooltip="diff",
            comment=DiffAlt.__name__,
            color="red"
        )
        return node, id_counter, node, node


class DiffSubexpresion(PartContainer):
    """
    Разница в виде подвыражения.
    """

    def __init__(self, id=None):
        PartContainer.__init__(self, id)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "diff",
            tooltip="diff",
            comment=DiffAlt.__name__,
            color="red"
        )
        return node, id_counter, node, node


class DiffConditionalSubexpression(Part):
    """
    Разница в виде условного подвыражения.
    """

    def __init__(self, id=None):
        Part.__init__(self, id)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "diff",
            tooltip="diff",
            comment=DiffAlt.__name__,
            color="red"
        )
        return node, id_counter, node, node


class DiffAssert(Part):
    """
    Разница в виде простого ассерта.
    """

    def __init__(self, id=None):
        Part.__init__(self, id)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "diff",
            tooltip="diff",
            comment=DiffAlt.__name__,
            color="red"
        )
        return node, id_counter, node, node


class DiffAssertComplex(PartContainer):
    """
    Разница в виде сложного ассерта.
    """

    def __init__(self, id=None):
        PartContainer.__init__(self, id)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "diff",
            tooltip="diff",
            comment=DiffAlt.__name__,
            color="red"
        )
        return node, id_counter, node, node