__author__ = 'Владимир'

import abc


class IGroup(metaclass=abc.ABCMeta):
    """
    Абстрактный класс контейнера в объясняюшем графе.
    """

    def __init__(self):
        self._nodes = []
        self._edges = []
        self._clusters = []
        self._tooltip = ""
        self._id = ""


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


class Cluster(IGroup):
    """
    Подграф в объясняющем графе.
    """

    def __init__(self):
        IGroup.__init__(self)
        self._bgcolor = "white"
        self._style = ""
        self._label = ""


class Node:
    """
    Узел объясняющего графа.
    """
    pass


class Edge:
    """
    Ребро в объясняющем графе.
    """
    pass