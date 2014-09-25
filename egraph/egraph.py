__author__ = 'Владимир'

from egraph.dot import *
from enum import Enum
from copy import deepcopy


class Part(metaclass=abc.ABCMeta):
    """
    Абстрактная часть регулярного выражения.
    """

    def __init__(self, id=None):
        self._id = id
        self._enter = self
        """:type : Part|None"""
        self._exit = self
        """:type : Part|None"""

    @property
    def enter(self):
        return self._enter

    @property
    def exit(self):
        return self._exit

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @abc.abstractmethod
    def to_graph(self, id_counter=1):
        """
        Возвращает часть регулярного выражения в Dot-представлении.

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


class OptionCaseSensitivity(Part):
    """
    Представляет опцию чувствительности к регистру.
    """

    def __init__(self, is_positive=True, id=None):
        Part.__init__(self, id=id)
        self._is_positive = is_positive

    @property
    def is_positive(self) -> bool:
        return self._is_positive

    @is_positive.setter
    def is_positive(self, value: bool):
        self._is_positive = value

    def __eq__(self, other):
        return self.is_positive == other.is_positive

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(self._id, 'i-option', comment=OptionCaseSensitivity.__name__)
        return node, id_counter, node, node


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
    def to_graph(self, id_counter=1):
        pass

    def _perform_case_option(self, initial=OptionCaseSensitivity(False)):
        for branch in self._branches:
            option = initial
            for item in branch:
                if isinstance(item, OptionCaseSensitivity):
                    option = item
                elif isinstance(item, ICaseSensitive):
                    item.is_sensitive = not option.is_positive
                elif isinstance(item, PartContainer) or isinstance(item, ConditionalSubexpression):
                    item._perform_case_option(option)


class ICaseSensitive(metaclass=abc.ABCMeta):
    """
    Интерфейс чувствительного к регсистру объекта.
    """

    def __init__(self):
        self._is_sensitive = True

    @property
    def is_sensitive(self) -> bool:
        return self._is_sensitive

    @is_sensitive.setter
    def is_sensitive(self, value: bool):
        self._is_sensitive = value


class ExplainingGraph(PartContainer, ICaseSensitive):
    """
    Модель объясняющего графа.
    """

    def __init__(self, is_exact=False, is_case_sensitive=True):
        PartContainer.__init__(self, "explaining_graph")
        ICaseSensitive.__init__(self)
        self.is_sensitive = is_case_sensitive
        self._id_counter = 1
        self.is_exact = is_exact

    def to_graph(self, id_counter=1):
        """
        :rtype : DotDigraph
        """
        rabbit = deepcopy(self)             # сохраним копию, чтобы потом восстановить
        """:type : ExplainingGraph"""
        # реализуем опцию чувствительности к регистру
        rabbit._perform_case_option(OptionCaseSensitivity(not self.is_sensitive))
        graph = rabbit._to_real_graph()
        ExplainingGraph._del_case_options(graph, graph)
        return graph

    def _to_real_graph(self):
        graph = DotDigraph(self._id)        # собственно результирующий граф

        # добавим в него начало и конец
        begin = DotNode(self._id_counter, "begin", 'filled', "purple", "begin", "rect", "purple")
        self._id_counter += 1
        graph.items.append(begin)
        end = DotNode(self._id_counter, "end", 'filled', "purple", "end", "rect", "purple")
        self._id_counter += 1
        graph.items.append(end)

        if len(self._branches) == 0:  # если ветвей нет, то добавим пустую
            self._branches.append([])

        # если уставновлен флаг точного совпадения, то проводим соотвествующие преобразования
        if self.is_exact:
            sol = Assert(AssertType.circumflex, self._id_counter)
            self._id_counter += 1
            eol = Assert(AssertType.dollar, self._id_counter)
            self._id_counter += 1

            graph.bgcolor = 'grey'

            container = Subexpression(is_wrapper=True)
            for branch in self._branches:
                container.add_branch(branch)

            self._branches = [[sol, container, eol]]

        current = begin
        if len(self._branches) == 1:
            branch = self._branches[0]
            """:type : list"""
            for item in branch:
                part, new_id, enter, exit = item.to_graph(self._id_counter)
                self._id_counter = new_id
                graph.items.append(part)
                # не забываем соединить две части
                graph.items.append(DotLink(current, enter, self._id_counter))
                self._id_counter += 1
                current = exit  # теперь конец нового элемента является зацепкой для следующего
        else:
            start = DotNode(self._id_counter, tooltip="alternative", shape="point", fillcolor="white")
            self._id_counter += 1
            finish = DotNode(self._id_counter, tooltip="alternative", shape="point", fillcolor="white")
            self._id_counter += 1

            graph.items += [start, finish, DotLink(begin, start, self._id_counter)]
            self._id_counter += 1

            for branch in self._branches:
                current = start
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=self._id_counter)
                    self._id_counter = new_id
                    graph.items.append(part)
                    # не забываем соединить две части
                    graph.items.append(DotLink(current, enter, self._id_counter))
                    self._id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего

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
                if item._comment != Text.__name__:
                    continue

                neighbor = main.find_neighbor_right(item)
                owner = main.find_node_owner(neighbor)
                # If neighbor is simple node with text too and it's a child of the same subgraph,
                # then we need to join this two nodes.
                if neighbor is not None and neighbor._comment == Text.__name__ and owner == graph:
                    if type(item._id) is str and type(neighbor._id) is str:
                        ids_this = item._id.split('_')
                        ids_neighbor = neighbor._id.split('_')
                        ids_new = ids_this[0] + '_' + ids_this[1] + '_' + ids_neighbor[2]
                    else:
                        ids_new = item._id

                    item._label += neighbor._label
                    item._tooltip += neighbor._label
                    item.id = ids_new

                    # Find a link between current node and neighbor, then change destination to node after neighbor.
                    link, _ = main.find_link(item, neighbor)
                    after = main.find_neighbor_right(neighbor)
                    link.destination = after

                    # Destroy old link.
                    link, owner = main.find_link(neighbor, after)
                    if owner is not None:
                        owner.items.remove(link)

                    # Destroy old node.
                    owner.items.remove(neighbor)

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
            for _assert in filter(
                    lambda i: isinstance(i, DotNode) and i._comment == Assert.__name__,
                    graph.items
            ):
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
                    left_link._label = ExplainingGraph._compute_label(left_link._label, _assert._label)
                    left_link.tooltip = left_link._label

                    owner.items.remove(right_link)
                    graph.items.remove(_assert)
                    need_to_break = True
                # Second case - neighbors are not in the same subgraphs, but right neighbor is in same as assert.
                elif right_neighbor is not None and right_owner is not left_owner \
                        and left_owner is not graph and right_owner is graph:
                    right_link, _ = main.find_link(_assert, right_neighbor)
                    right_link._label = ExplainingGraph._compute_label(_assert._label, right_link._label)
                    right_link.tooltip = right_link._label
                    _assert.shape = 'point'
                    _assert._label = ''
                # Third case - neighbors are not in the same subgraphs, but left neighbor is in same as assert.
                elif right_neighbor is not None and right_owner is not left_owner \
                        and left_owner is graph and right_owner is not graph:
                    left_link, _ = main.find_link(left_neighbor, _assert)
                    left_link._label = ExplainingGraph._compute_label(left_link._label, _assert._label)
                    left_link.tooltip = left_link._label
                    _assert.shape = 'point'
                    _assert._label = ''
                else:  # Fourth case - neighbors are not in the same subgraphs and no one in current subgraph.
                    # If right neighbor is existing...
                    if right_neighbor is not None:
                        # Find links between neighbors and assert.
                        left_link, _ = main.find_link(left_neighbor, _assert)
                        right_link, owner = main.find_link(_assert, right_neighbor)

                        left_link.destination = right_link.destination
                        left_link._label = _assert._label
                        left_link.tooltip = left_link._label

                        owner.items.remove(right_link)
                        graph.items.remove(_assert)
                    else:  # Right neighbor is not existing, so we just replace it with point-node.
                        point = DotNode(shape="point", comment="Point")
                        new_link = DotLink(_assert, point, _assert._label, tooltip=_assert._label)
                        _assert.shape = 'point'
                        _assert._label = ''

                        graph.items.extend([point, new_link])

                    need_to_break = True

                if need_to_break:
                    break
            else:
                break

    @staticmethod
    def _del_case_options(graph: IGroupable, main: DotDigraph):
        while True:
            for item in filter(lambda i: isinstance(i, DotNode) and i._comment == OptionCaseSensitivity.__name__,
                               graph.items):

                neighbor_r = main.find_neighbor_right(item)
                neighbor_l = main.find_neighbor_left(item)
                link, _ = main.find_link(neighbor_l, item)
                link.destination = neighbor_r

                link, owner = main.find_link(item, neighbor_r)
                owner.items.remove(link)

                graph.items.remove(item)

                break
            else:
                break

        for subgraph in filter(lambda i: isinstance(i, IGroupable), graph.items):
            ExplainingGraph._del_case_options(subgraph, main)


class Text(Part, ICaseSensitive):
    """
    Простой текст в регулярном выражении.
    """

    def __init__(self, txt="", id=None):
        Part.__init__(self, id=id)
        ICaseSensitive.__init__(self)
        self._txt = txt

    @property
    def text(self) -> str:
        return self._txt

    @text.setter
    def text(self, value: str) -> None:
        self._txt = value

    def __str__(self):
        return self.text

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            self.text,
            tooltip=self.text,
            comment=Text.__name__,
            fillcolor=('' if self.is_sensitive else 'lightgrey'),
            style=('' if self.is_sensitive else 'filled')
        )
        return node, id_counter, node, node


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
    def type(self) -> AssertType:
        return self._type

    @type.setter
    def type(self, value: str):
        self._type = value

    _assert_strings = {
        AssertType.slash_b: "a word boundary",
        AssertType.slash_B: "not a word boundary",
        AssertType.circumflex: "start of the string",
        AssertType.dollar: "end of the string"
    }

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        text = self._assert_strings[self.type]
        node = DotNode(self._id, text, comment=Assert.__name__)
        return node, id_counter, node, node


class Subexpression(PartContainer):
    """
    Представляет подвыражение в регулярном выражении.
    """

    def __init__(self, number=None, id=None, is_wrapper=False):
        PartContainer.__init__(self, id=id)
        self._number = number
        self._is_wrapper = is_wrapper

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int):
        self._number = value

    @property
    def is_wrapper(self) -> bool:
        return self._is_wrapper

    @is_wrapper.setter
    def is_wrapper(self, value: bool):
        self._is_wrapper = value

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)  # устанавливаем id, если он не задан

        if self.number is not None:  # если это не группировка, то надпись нужна
            text = "subexpression #{0}".format(self.number)
            tooltip = "subexpression"
        else:  # иначе надпись не нужна
            text = ""
            tooltip = "grouping"

        # подграф представляющий подвыражение (группировку)
        subgraph = DotSubgraph(
            id=self._id,
            label=text,
            tooltip=tooltip,
            bgcolor='white',
            color=('white' if self.is_wrapper else 'black')
        )

        if len(self._branches) == 0:  # если ветвей нет, то добавим пустую
            self._branches.append([])

        global_enter = global_exit = None
        if len(self._branches) == 1:  # если всего 1 ветвь, то это неальтернатива
            branch = self._branches[0]

            # если совсем пустое подвыражение, то внутри надобно сделать точку
            if len(branch) == 0:
                point = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                                comment="Point")
                id_counter += 1

                subgraph.items.append(point)
                global_enter = global_exit = point
            # иначе проходимся по содержимому ветки и генерирем части графа соотвествующие ему (содержимому)
            else:
                current = None  # первый элемент ни с чем соединять не будем
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    if global_enter is None:
                        global_enter = enter
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    if current is not None:
                        subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего
                global_exit = current  # конец последнего элемента является глобальным концом подграфа
        else:  # иначе это альтернатива
            # вход альтернативы
            start = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                            comment="Point")
            id_counter += 1
            # выход альтернативы
            finish = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                             comment="Point")
            id_counter += 1

            subgraph.items += [start, finish]  # добавляем точки к частям подграфа
            global_enter = start  # первая точка это глобальный вход подграфа
            global_exit = finish  # вторая точка это глобальный выход подграфа

            # проходимся по веткам и создаём из них части подграфа
            for branch in self._branches:
                current = start  # грядущий первый элемент соединим с начальной точкой
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего

                # не забываем соединить конец ветки с выходом альтернативы
                subgraph.items.append(DotLink(current, finish, id_counter))
                id_counter += 1

        return (subgraph, id_counter, global_enter, global_exit)


class CharflagType(Enum):
    dot = 1
    slashd = 2
    slashh = 3
    slashs = 4
    slashv = 5
    slashw = 6
    slashd_neg = 7
    slashh_neg = 8
    slashs_neg = 9
    slashv_neg = 10
    slashw_neg = 11

    # юникод-флаги

    Cc = 12
    Cf = 13
    Cn = 14
    Co = 15
    Cs = 16
    C = 17
    Ll = 18
    Lm = 19
    Lo = 20
    Lt = 21
    Lu = 22
    L = 23
    Mc = 24
    Me = 25
    Mn = 26
    M = 27
    Nd = 28
    Nl = 29
    No = 30
    N = 31
    Pc = 32
    Pd = 33
    Pe = 34
    Pf = 35
    Pi = 36
    Po = 37
    Ps = 38
    P = 39
    Sc = 40
    Sk = 41
    Sm = 42
    So = 43
    S = 44
    Zl = 45
    Zp = 46
    Zs = 47
    Z = 48
    Xan = 49
    Xps = 51
    Xsp = 52
    Xwd = 53
    Arabic = 54
    Armenian = 55
    Avestan = 56
    Balinese = 57
    Bamum = 58
    Bengali = 59
    Bopomofo = 60
    Braille = 61
    Buginese = 62
    Buhid = 63
    Canadian_Aboriginal = 64
    Carian = 65
    Cham = 66
    Cherokee = 67
    Common = 68
    Coptic = 69
    Cuneiform = 70
    Cypriot = 71
    Cyrillic = 72
    Deseret = 73
    Devanagari = 74
    Egyptian_Hieroglyphs = 75
    Ethiopic = 76
    Georgian = 77
    Glagolitic = 78
    Gothic = 79
    Greek = 80
    Gujarati = 81
    Gurmukhi = 82
    Han = 83
    Hangul = 84
    Hanunoo = 85
    Hebrew = 86
    Hiragana = 87
    Imperial_Aramaic = 88
    Inherited = 89
    Inscriptional_Pahlavi = 90
    Inscriptional_Parthian = 91
    Javanese = 92
    Kaithi = 93
    Kannada = 94
    Katakana = 95
    Kayah_Li = 96
    Kharoshthi = 97
    Khmer = 98
    Lao = 99
    Latin = 100
    Lepcha = 101
    Limbu = 102
    Linear_B = 103
    Lisu = 104
    Lycian = 105
    Lydian = 106
    Malayalam = 107
    Meetei_Mayek = 108
    Mongolian = 109
    Myanmar = 110
    New_Tai_Lue = 111
    Nko = 112
    Ogham = 113
    Old_Italic = 114
    Old_Persian = 115
    Old_South_Arabian = 116
    Old_Turkic = 117
    Ol_Chiki = 118
    Oriya = 119
    Osmanya = 120
    Phags_Pa = 121
    Phoenician = 122
    Rejang = 123
    Runic = 124
    Samaritan = 125
    Saurashtra = 126
    Shavian = 127
    Sinhala = 128
    Sundanese = 129
    Syloti_Nagri = 130
    Syriac = 131
    Tagalog = 132
    Tagbanwa = 133
    Tai_Le = 134
    Tai_Tham = 135
    Tai_Viet = 136
    Tamil = 137
    Telugu = 138
    Thaana = 139
    Thai = 140
    Tibetan = 141
    Tifinagh = 142
    Ugaritic = 143
    Vai = 144
    Yi = 145

    Cc_neg = 112
    Cf_neg = 113
    Cn_neg = 114
    Co_neg = 115
    Cs_neg = 116
    C_neg = 117
    Ll_neg = 118
    Lm_neg = 119
    Lo_neg = 120
    Lt_neg = 121
    Lu_neg = 122
    L_neg = 123
    Mc_neg = 124
    Me_neg = 125
    Mn_neg = 126
    M_neg = 127
    Nd_neg = 128
    Nl_neg = 129
    No_neg = 130
    N_neg = 131
    Pc_neg = 132
    Pd_neg = 133
    Pe_neg = 134
    Pf_neg = 135
    Pi_neg = 136
    Po_neg = 137
    Ps_neg = 138
    P_neg = 139
    Sc_neg = 140
    Sk_neg = 141
    Sm_neg = 142
    So_neg = 143
    S_neg = 144
    Zl_neg = 145
    Zp_neg = 146
    Zs_neg = 147
    Z_neg = 148
    Xan_neg = 149
    Xps_neg = 151
    Xsp_neg = 152
    Xwd_neg = 153
    Arabic_neg = 154
    Armenian_neg = 155
    Avestan_neg = 156
    Balinese_neg = 157
    Bamum_neg = 158
    Bengali_neg = 159
    Bopomofo_neg = 160
    Braille_neg = 161
    Buginese_neg = 162
    Buhid_neg = 163
    Canadian_Aboriginal_neg = 164
    Carian_neg = 165
    Cham_neg = 166
    Cherokee_neg = 167
    Common_neg = 168
    Coptic_neg = 169
    Cuneiform_neg = 170
    Cypriot_neg = 171
    Cyrillic_neg = 172
    Deseret_neg = 173
    Devanagari_neg = 174
    Egyptian_Hieroglyphs_neg = 175
    Ethiopic_neg = 176
    Georgian_neg = 177
    Glagolitic_neg = 178
    Gothic_neg = 179
    Greek_neg = 180
    Gujarati_neg = 181
    Gurmukhi_neg = 182
    Han_neg = 183
    Hangul_neg = 184
    Hanunoo_neg = 185
    Hebrew_neg = 186
    Hiragana_neg = 187
    Imperial_Aramaic_neg = 188
    Inherited_neg = 189
    Inscriptional_Pahlavi_neg = 190
    Inscriptional_Parthian_neg = 191
    Javanese_neg = 192
    Kaithi_neg = 193
    Kannada_neg = 194
    Katakana_neg = 195
    Kayah_Li_neg = 196
    Kharoshthi_neg = 197
    Khmer_neg = 198
    Lao_neg = 199
    Latin_neg = 200
    Lepcha_neg = 201
    Limbu_neg = 202
    Linear_B_neg = 203
    Lisu_neg = 204
    Lycian_neg = 205
    Lydian_neg = 206
    Malayalam_neg = 207
    Meetei_Mayek_neg = 208
    Mongolian_neg = 209
    Myanmar_neg = 210
    New_Tai_Lue_neg = 211
    Nko_neg = 212
    Ogham_neg = 213
    Old_Italic_neg = 214
    Old_Persian_neg = 215
    Old_South_Arabian_neg = 216
    Old_Turkic_neg = 217
    Ol_Chiki_neg = 218
    Oriya_neg = 219
    Osmanya_neg = 220
    Phags_Pa_neg = 221
    Phoenician_neg = 222
    Rejang_neg = 223
    Runic_neg = 224
    Samaritan_neg = 225
    Saurashtra_neg = 226
    Shavian_neg = 227
    Sinhala_neg = 228
    Sundanese_neg = 229
    Syloti_Nagri_neg = 230
    Syriac_neg = 231
    Tagalog_neg = 232
    Tagbanwa_neg = 233
    Tai_Le_neg = 234
    Tai_Tham_neg = 235
    Tai_Viet_neg = 236
    Tamil_neg = 237
    Telugu_neg = 238
    Thaana_neg = 239
    Thai_neg = 240
    Tibetan_neg = 241
    Tifinagh_neg = 242
    Ugaritic_neg = 243
    Vai_neg = 244
    Yi_neg = 245

    # POSIX классы

    alnum = 251
    alpha = 252
    ascii = 253
    blank = 254
    cntrl = 255
    digit = 256
    graph = 257
    lower = 258
    print = 259
    punct = 260
    space = 261
    upper = 262
    word = 263
    xdigit = 264
    alnum_neg = 265
    alpha_neg = 266
    ascii_neg = 267
    blank_neg = 268
    cntrl_neg = 269
    digit_neg = 270
    graph_neg = 271
    lower_neg = 272
    print_neg = 273
    punct_neg = 274
    space_neg = 275
    upper_neg = 276
    word_neg = 277
    xdigit_neg = 278


class Charflag(Part, ICaseSensitive):
    """
    Представляет символьный флаг в регулярном выражении.
    """

    def __init__(self, type: CharflagType, id=None):
        Part.__init__(self, id=id)
        ICaseSensitive.__init__(self)
        self._type = type

    @property
    def type(self) -> CharflagType:
        return self._type

    @type.setter
    def type(self, value: CharflagType):
        self._type = value

    _charflag_strings = {
        CharflagType.dot: "any character",
        CharflagType.slashd: "a decimal digit",
        CharflagType.slashh: "a horizontal white space character",
        CharflagType.slashs: "a white space",
        CharflagType.slashv: "a vertical white space character",
        CharflagType.slashw: "a word character",
        CharflagType.slashd_neg: "not a decimal digit",
        CharflagType.slashh_neg: "not a horizontal white space character",
        CharflagType.slashs_neg: "not a white space",
        CharflagType.slashv_neg: "not a vertical white space character",
        CharflagType.slashw_neg: "not a word character",

        CharflagType.alnum: "a letter or digit",
        CharflagType.alpha: "a letter",
        CharflagType.ascii: "a character with codes 0-127",
        CharflagType.blank: "a space or tab only",
        CharflagType.cntrl: "a control character",
        CharflagType.digit: "a decimal digit",
        CharflagType.graph: "a printing character (excluding space)",
        CharflagType.lower: "a lower case letter",
        CharflagType.print: "a printing character (including space)",
        CharflagType.punct: "a printing character (excluding letters and digits and space)",
        CharflagType.space: "a white space",
        CharflagType.upper: "an upper case letter",
        CharflagType.word: "a word character",
        CharflagType.xdigit: "a hexadecimal digit",
        CharflagType.alnum_neg: "not a letter and not digit",
        CharflagType.alpha_neg: "not a letter",
        CharflagType.ascii_neg: "not a character with codes 0-127",
        CharflagType.blank_neg: "not a space and not tab",
        CharflagType.cntrl_neg: "not a control character",
        CharflagType.digit_neg: "not a decimal digit",
        CharflagType.graph_neg: "not a printing character (excluding space)",
        CharflagType.lower_neg: "not a lower case letter",
        CharflagType.print_neg: "not a printing character (including space)",
        CharflagType.punct_neg: "not a printing character (excluding letters and digits and space)",
        CharflagType.space_neg: "not a white space",
        CharflagType.upper_neg: "not an upper case letter",
        CharflagType.word_neg: "not a word character",
        CharflagType.xdigit_neg: "not a hexadecimal digit",

        CharflagType.Cc: "control",
        CharflagType.Cf: "format",
        CharflagType.Cn: "unassigned",
        CharflagType.Co: "private use",
        CharflagType.Cs: "surrogate",
        CharflagType.C: "other Unicode property",
        CharflagType.Ll: "lower case letter",
        CharflagType.Lm: "modifier letter",
        CharflagType.Lo: "other letter",
        CharflagType.Lt: "title case letter",
        CharflagType.Lu: "upper case letter",
        CharflagType.L: "letter",
        CharflagType.Mc: "spacing mark",
        CharflagType.Me: "enclosing mark",
        CharflagType.Mn: "non-spacing mark",
        CharflagType.M: "mark",
        CharflagType.Nd: "decimal number",
        CharflagType.Nl: "letter number",
        CharflagType.No: "other number",
        CharflagType.N: "number",
        CharflagType.Pc: "connector punctuation",
        CharflagType.Pd: "dash punctuation",
        CharflagType.Pe: "close punctuation",
        CharflagType.Pf: "final punctuation",
        CharflagType.Pi: "initial punctuation",
        CharflagType.Po: "other punctuation",
        CharflagType.Ps: "open punctuation",
        CharflagType.P: "punctuation",
        CharflagType.Sc: "currency symbol",
        CharflagType.Sk: "modifier symbol",
        CharflagType.Sm: "mathematical symbol",
        CharflagType.So: "other symbol",
        CharflagType.S: "symbol",
        CharflagType.Zl: "line separator",
        CharflagType.Zp: "paragraph separator",
        CharflagType.Zs: "space separator",
        CharflagType.Z: "separator",
        CharflagType.Xan: "any alphanumeric character",
        CharflagType.Xps: "any POSIX space character",
        CharflagType.Xsp: "any Perl space character",
        CharflagType.Xwd: "any Perl \"word\" character",
        CharflagType.Arabic: "Arabic character",
        CharflagType.Armenian: "Armenian character",
        CharflagType.Avestan: "Avestan character",
        CharflagType.Balinese: "Balinese character",
        CharflagType.Bamum: "Bamum character",
        CharflagType.Bengali: "Bengali character",
        CharflagType.Bopomofo: "Bopomofo character",
        CharflagType.Braille: "Braille character",
        CharflagType.Buginese: "Buginese character",
        CharflagType.Buhid: "Buhid character",
        CharflagType.Canadian_Aboriginal: "Canadian Aboriginal character",
        CharflagType.Carian: "Carian character",
        CharflagType.Cham: "Cham character",
        CharflagType.Cherokee: "Cherokee character",
        CharflagType.Common: "Common character",
        CharflagType.Coptic: "Coptic character",
        CharflagType.Cuneiform: "Cuneiform character",
        CharflagType.Cypriot: "Cypriot character",
        CharflagType.Cyrillic: "Cyrillic character",
        CharflagType.Deseret: "Deseret character",
        CharflagType.Devanagari: "Devanagari character",
        CharflagType.Egyptian_Hieroglyphs: "Egyptian Hieroglyphs character",
        CharflagType.Ethiopic: "Ethiopic character",
        CharflagType.Georgian: "Georgian character",
        CharflagType.Glagolitic: "Glagolitic character",
        CharflagType.Gothic: "Gothic character",
        CharflagType.Greek: "Greek character",
        CharflagType.Gujarati: "Gujarati character",
        CharflagType.Gurmukhi: "Gurmukhi character",
        CharflagType.Han: "Han character",
        CharflagType.Hangul: "Hangul character",
        CharflagType.Hanunoo: "Hanunoo character",
        CharflagType.Hebrew: "Hebrew character",
        CharflagType.Hiragana: "Hiragana character",
        CharflagType.Imperial_Aramaic: "Imperial Aramaic character",
        CharflagType.Inherited: "Inherited character",
        CharflagType.Inscriptional_Pahlavi: "Inscriptional Pahlavi character",
        CharflagType.Inscriptional_Parthian: "Inscriptional Parthian character",
        CharflagType.Javanese: "Javanese character",
        CharflagType.Kaithi: "Kaithi character",
        CharflagType.Kannada: "Kannada character",
        CharflagType.Katakana: "Katakana character",
        CharflagType.Kayah_Li: "Kayah Li character",
        CharflagType.Kharoshthi: "Kharoshthi character",
        CharflagType.Khmer: "Khmer character",
        CharflagType.Lao: "Lao character",
        CharflagType.Latin: "Latin character",
        CharflagType.Lepcha: "Lepcha character",
        CharflagType.Limbu: "Limbu character",
        CharflagType.Linear_B: "Linear B character",
        CharflagType.Lisu: "Lisu character",
        CharflagType.Lycian: "Lycian character",
        CharflagType.Lydian: "Lydian character",
        CharflagType.Malayalam: "Malayalam character",
        CharflagType.Meetei_Mayek: "Meetei Mayek character",
        CharflagType.Mongolian: "Mongolian character",
        CharflagType.Myanmar: "Myanmar character",
        CharflagType.New_Tai_Lue: "New Tai Lue character",
        CharflagType.Nko: "Nko character",
        CharflagType.Ogham: "Ogham character",
        CharflagType.Old_Italic: "Old Italic character",
        CharflagType.Old_Persian: "Old Persian character",
        CharflagType.Old_South_Arabian: "Old South_Arabian character",
        CharflagType.Old_Turkic: "Old_Turkic character",
        CharflagType.Ol_Chiki: "Ol_Chiki character",
        CharflagType.Oriya: "Oriya character",
        CharflagType.Osmanya: "Osmanya character",
        CharflagType.Phags_Pa: "Phags_Pa character",
        CharflagType.Phoenician: "Phoenician character",
        CharflagType.Rejang: "Rejang character",
        CharflagType.Runic: "Runic character",
        CharflagType.Samaritan: "Samaritan character",
        CharflagType.Saurashtra: "Saurashtra character",
        CharflagType.Shavian: "Shavian character",
        CharflagType.Sinhala: "Sinhala character",
        CharflagType.Sundanese: "Sundanese character",
        CharflagType.Syloti_Nagri: "Syloti_Nagri character",
        CharflagType.Syriac: "Syriac character",
        CharflagType.Tagalog: "Tagalog character",
        CharflagType.Tagbanwa: "Tagbanwa character",
        CharflagType.Tai_Le: "Tai_Le character",
        CharflagType.Tai_Tham: "Tai_Tham character",
        CharflagType.Tai_Viet: "Tai_Viet character",
        CharflagType.Tamil: "Tamil character",
        CharflagType.Telugu: "Telugu character",
        CharflagType.Thaana: "Thaana character",
        CharflagType.Thai: "Thai character",
        CharflagType.Tibetan: "Tibetan character",
        CharflagType.Tifinagh: "Tifinagh character",
        CharflagType.Ugaritic: "Ugaritic character",
        CharflagType.Vai: "Vai character",
        CharflagType.Yi: "Yi character",

        CharflagType.Cc_neg: "not control",
        CharflagType.Cf_neg: "not format",
        CharflagType.Cn_neg: "not unassigned",
        CharflagType.Co_neg: "not private use",
        CharflagType.Cs_neg: "not surrogate",
        CharflagType.C_neg: "not other Unicode property",
        CharflagType.Ll_neg: "not lower case letter",
        CharflagType.Lm_neg: "not modifier letter",
        CharflagType.Lo_neg: "not other letter",
        CharflagType.Lt_neg: "not title case letter",
        CharflagType.Lu_neg: "not upper case letter",
        CharflagType.L_neg: "not letter",
        CharflagType.Mc_neg: "not spacing mark",
        CharflagType.Me_neg: "not enclosing mark",
        CharflagType.Mn_neg: "not non-spacing mark",
        CharflagType.M_neg: "not mark",
        CharflagType.Nd_neg: "not decimal number",
        CharflagType.Nl_neg: "not letter number",
        CharflagType.No_neg: "not other number",
        CharflagType.N_neg: "not number",
        CharflagType.Pc_neg: "not connector punctuation",
        CharflagType.Pd_neg: "not dash punctuation",
        CharflagType.Pe_neg: "not close punctuation",
        CharflagType.Pf_neg: "not final punctuation",
        CharflagType.Pi_neg: "not initial punctuation",
        CharflagType.Po_neg: "not other punctuation",
        CharflagType.Ps_neg: "not open punctuation",
        CharflagType.P_neg: "not punctuation",
        CharflagType.Sc_neg: "not currency symbol",
        CharflagType.Sk_neg: "not modifier symbol",
        CharflagType.Sm_neg: "not mathematical symbol",
        CharflagType.So_neg: "not other symbol",
        CharflagType.S_neg: "not symbol",
        CharflagType.Zl_neg: "not line separator",
        CharflagType.Zp_neg: "not paragraph separator",
        CharflagType.Zs_neg: "not space separator",
        CharflagType.Z_neg: "not separator",
        CharflagType.Xan_neg: "not any alphanumeric character",
        CharflagType.Xps_neg: "not any POSIX space character",
        CharflagType.Xsp_neg: "not any Perl space character",
        CharflagType.Xwd_neg: "not any Perl \"word\" character",
        CharflagType.Arabic_neg: "not Arabic character",
        CharflagType.Armenian_neg: "not Armenian character",
        CharflagType.Avestan_neg: "not Avestan character",
        CharflagType.Balinese_neg: "not Balinese character",
        CharflagType.Bamum_neg: "not Bamum character",
        CharflagType.Bengali_neg: "not Bengali character",
        CharflagType.Bopomofo_neg: "not Bopomofo character",
        CharflagType.Braille_neg: "not Braille character",
        CharflagType.Buginese_neg: "not Buginese character",
        CharflagType.Buhid_neg: "not Buhid character",
        CharflagType.Canadian_Aboriginal_neg: "not Canadian Aboriginal character",
        CharflagType.Carian_neg: "not Carian character",
        CharflagType.Cham_neg: "not Cham character",
        CharflagType.Cherokee_neg: "not Cherokee character",
        CharflagType.Common_neg: "not Common character",
        CharflagType.Coptic_neg: "not Coptic character",
        CharflagType.Cuneiform_neg: "not Cuneiform character",
        CharflagType.Cypriot_neg: "not Cypriot character",
        CharflagType.Cyrillic_neg: "not Cyrillic character",
        CharflagType.Deseret_neg: "not Deseret character",
        CharflagType.Devanagari_neg: "not Devanagari character",
        CharflagType.Egyptian_Hieroglyphs_neg: "not Egyptian Hieroglyphs character",
        CharflagType.Ethiopic_neg: "not Ethiopic character",
        CharflagType.Georgian_neg: "not Georgian character",
        CharflagType.Glagolitic_neg: "not Glagolitic character",
        CharflagType.Gothic_neg: "not Gothic character",
        CharflagType.Greek_neg: "not Greek character",
        CharflagType.Gujarati_neg: "not Gujarati character",
        CharflagType.Gurmukhi_neg: "not Gurmukhi character",
        CharflagType.Han_neg: "not Han character",
        CharflagType.Hangul_neg: "not Hangul character",
        CharflagType.Hanunoo_neg: "not Hanunoo character",
        CharflagType.Hebrew_neg: "not Hebrew character",
        CharflagType.Hiragana_neg: "not Hiragana character",
        CharflagType.Imperial_Aramaic_neg: "not Imperial Aramaic character",
        CharflagType.Inherited_neg: "not Inherited character",
        CharflagType.Inscriptional_Pahlavi_neg: "not Inscriptional Pahlavi character",
        CharflagType.Inscriptional_Parthian_neg: "not Inscriptional Parthian character",
        CharflagType.Javanese_neg: "not Javanese character",
        CharflagType.Kaithi_neg: "not Kaithi character",
        CharflagType.Kannada_neg: "not Kannada character",
        CharflagType.Katakana_neg: "not Katakana character",
        CharflagType.Kayah_Li_neg: "not Kayah Li character",
        CharflagType.Kharoshthi_neg: "not Kharoshthi character",
        CharflagType.Khmer_neg: "not Khmer character",
        CharflagType.Lao_neg: "not Lao character",
        CharflagType.Latin_neg: "not Latin character",
        CharflagType.Lepcha_neg: "not Lepcha character",
        CharflagType.Limbu_neg: "not Limbu character",
        CharflagType.Linear_B_neg: "not Linear B character",
        CharflagType.Lisu_neg: "not Lisu character",
        CharflagType.Lycian_neg: "not Lycian character",
        CharflagType.Lydian_neg: "not Lydian character",
        CharflagType.Malayalam_neg: "not Malayalam character",
        CharflagType.Meetei_Mayek_neg: "not Meetei Mayek character",
        CharflagType.Mongolian_neg: "not Mongolian character",
        CharflagType.Myanmar_neg: "not Myanmar character",
        CharflagType.New_Tai_Lue_neg: "not New Tai Lue character",
        CharflagType.Nko_neg: "not Nko character",
        CharflagType.Ogham_neg: "not Ogham character",
        CharflagType.Old_Italic_neg: "not Old Italic character",
        CharflagType.Old_Persian_neg: "not Old Persian character",
        CharflagType.Old_South_Arabian_neg: "not Old South_Arabian character",
        CharflagType.Old_Turkic_neg: "not Old_Turkic character",
        CharflagType.Ol_Chiki_neg: "not Ol_Chiki character",
        CharflagType.Oriya_neg: "not Oriya character",
        CharflagType.Osmanya_neg: "not Osmanya character",
        CharflagType.Phags_Pa_neg: "not Phags_Pa character",
        CharflagType.Phoenician_neg: "not Phoenician character",
        CharflagType.Rejang_neg: "not Rejang character",
        CharflagType.Runic_neg: "not Runic character",
        CharflagType.Samaritan_neg: "not Samaritan character",
        CharflagType.Saurashtra_neg: "not Saurashtra character",
        CharflagType.Shavian_neg: "not Shavian character",
        CharflagType.Sinhala_neg: "not Sinhala character",
        CharflagType.Sundanese_neg: "not Sundanese character",
        CharflagType.Syloti_Nagri_neg: "not Syloti_Nagri character",
        CharflagType.Syriac_neg: "not Syriac character",
        CharflagType.Tagalog_neg: "not Tagalog character",
        CharflagType.Tagbanwa_neg: "not Tagbanwa character",
        CharflagType.Tai_Le_neg: "not Tai_Le character",
        CharflagType.Tai_Tham_neg: "not Tai_Tham character",
        CharflagType.Tai_Viet_neg: "not Tai_Viet character",
        CharflagType.Tamil_neg: "not Tamil character",
        CharflagType.Telugu_neg: "not Telugu character",
        CharflagType.Thaana_neg: "not Thaana character",
        CharflagType.Thai_neg: "not Thai character",
        CharflagType.Tibetan_neg: "not Tibetan character",
        CharflagType.Tifinagh_neg: "not Tifinagh character",
        CharflagType.Ugaritic_neg: "not Ugaritic character",
        CharflagType.Vai_neg: "not Vai character",
        CharflagType.Yi_neg: "not Yi character"
    }

    def __str__(self):
        return self._charflag_strings[self.type]

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        text = self._charflag_strings[self.type]
        node = DotNode(
            self._id,
            text,
            comment=Charflag.__name__, color='hotpink',
            fillcolor=('' if self.is_sensitive else 'lightgrey'),
            style=('' if self.is_sensitive else 'filled')
        )
        return node, id_counter, node, node


class Backreference(Part, ICaseSensitive):
    """
    Представляет обратную ссылку в регулярном выражении.
    """

    def __init__(self, number, id=None):
        Part.__init__(self, id=id)
        ICaseSensitive.__init__(self)
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    @number.setter
    def number(self, value: int):
        self._number = value

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            "backreference #" + str(self.number),
            tooltip="backreference",
            comment=Backreference.__name__,
            color="blue",
            fillcolor=('' if self.is_sensitive else 'lightgrey'),
            style=('' if self.is_sensitive else 'filled')
        )
        return node, id_counter, node, node


class SubexpressionCall(Part, ICaseSensitive):
    """
    Представляет вызов подмаски в регулярном выражении.
    """

    def __init__(self, subexpr_ref=None, is_recursive=False, id=None):
        Part.__init__(self, id=id)
        ICaseSensitive.__init__(self)
        self._subexpr_ref = subexpr_ref
        self._is_recursive = is_recursive

    @property
    def is_recursive(self) -> bool:
        return self._is_recursive

    @is_recursive.setter
    def is_recursive(self, value: bool):
        self._is_recursive = value

    @property
    def subexpr_ref(self):
        return self._subexpr_ref

    @subexpr_ref.setter
    def subexpr_ref(self, value):
        self._subexpr_ref = value

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)

        if self.subexpr_ref is not None:
            text = "call of the subpattern " + ("#{0}" if type(self.subexpr_ref) is int else '"{0}"')
            text = text.format(str(self.subexpr_ref))
        else:
            text = "call of the whole regular expression"

        if self.is_recursive:
            text = "recursive " + text

        node = DotNode(
            self._id,
            text,
            tooltip="subexpression call",
            comment=SubexpressionCall.__name__,
            color="blue",
            fillcolor=('' if self.is_sensitive else 'lightgrey'),
            style=('' if self.is_sensitive else 'filled')
        )
        return node, id_counter, node, node


class Quantifier(PartContainer):
    """
    Представляет квантификатор в регулярном выражении.
    """

    def __init__(self, min, max=None, is_greedy=True, id=None):
        PartContainer.__init__(self, id=id)

        if min < 0 or (max is not None and max < 0):
            raise ValueError("Границы не могут быть отрицательными.")

        if max is not None and max < min:
            raise ValueError("Верхняя граница не может быть меньше нижней.")

        self._min = min
        self._max = max
        self._is_greedy = is_greedy

    @property
    def min(self) -> int:
        return self._min

    @min.setter
    def min(self, value: int):
        self._min = value

    @property
    def max(self) -> int:
        return self._max

    @max.setter
    def max(self, value: int):
        self._max = value

    @property
    def is_greedy(self) -> bool:
        return self._is_greedy

    @is_greedy.setter
    def is_greedy(self, value: bool):
        self._is_greedy = value

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        text = "from {0} to {1}".format(self.min, 'infinity' if self.max is None else self.max)
        tooltip = "quantifier"
        subgraph = DotSubgraph(id=self._id, label=text, tooltip=tooltip, style='dotted')

        if len(self._branches) == 0:
            self._branches.append([])

        global_enter = global_exit = None
        if len(self._branches) == 1:  # если всего 1 ветвь, то это неальтернатива
            branch = self._branches[0]

            # если совсем пустое подвыражение, то внутри надобно сделать точку
            if len(branch) == 0:
                point = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                                comment="Point")
                id_counter += 1

                subgraph.items.append(point)
                global_enter = global_exit = point
            # иначе проходимся по содержимому ветки и генерирем части графа соотвествующие ему (содержимому)
            else:
                current = None  # первый элемент ни с чем соединять не будем
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    if global_enter is None:
                        global_enter = enter
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    if current is not None:
                        subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего
                global_exit = current  # конец последнего элемента является глобальным концом подграфа
        else:  # иначе это альтернатива
            # вход альтернативы
            start = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                            comment="Point")
            id_counter += 1
            # выход альтернативы
            finish = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                             comment="Point")
            id_counter += 1

            subgraph.items += [start, finish]  # добавляем точки к частям подграфа
            global_enter = start  # первая точка это глобальный вход подграфа
            global_exit = finish  # вторая точка это глобальный выход подграфа

            # проходимся по веткам и создаём из них части подграфа
            for branch in self._branches:
                current = start  # грядущий первый элемент соединим с начальной точкой
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего

                # не забываем соединить конец ветки с выходом альтернативы
                subgraph.items.append(DotLink(current, finish, id_counter))
                id_counter += 1

        return (subgraph, id_counter, global_enter, global_exit)


class AssertComplexType(Enum):
    pla = 1
    plb = 2
    nla = 3
    nlb = 4


class AssertComplex(PartContainer):
    """
    Представляет сложный ассерт в регулярном выражении.
    """

    def __init__(self, type: AssertComplexType, id=None):
        PartContainer.__init__(self, id=id)
        self._type = type

    @property
    def type(self) -> AssertComplexType:
        return self._type

    @type.setter
    def type(self, value: AssertComplexType):
        self._type = value

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        tooltip = "assert"
        subgraph = DotSubgraph(id=self._id, tooltip=tooltip, color='grey')
        color = 'green' if self.type == AssertComplexType.pla or self.type == AssertComplexType.plb else 'red'
        subgraph.edge_attrs = {'style': 'dashed'}
        subgraph.node_attrs = {'style': 'dotted'}
        enter = DotNode(id_counter, color="black", tooltip="assert", shape="point", fillcolor="white", comment="Point")
        id_counter += 1
        # noinspection PyTypeChecker
        link = DotLink(enter, None, id_counter, color=color)
        id_counter += 1

        # result = [enter, link, subgraph]
        # """:type : list[IDotable|DotLink]"""

        if len(self._branches) == 0:
            self._branches.append([])

        global_enter = global_exit = enter
        if len(self._branches) == 1:  # если всего 1 ветвь, то это неальтернатива
            branch = self._branches[0]

            # если совсем пустое подвыражение, то внутри надобно сделать точку
            if len(branch) == 0:
                point = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                                comment="Point")
                id_counter += 1

                subgraph.items.append(point)
                global_enter = global_exit = point
            # иначе проходимся по содержимому ветки и генерирем части графа соотвествующие ему (содержимому)
            else:
                current = None  # первый элемент ни с чем соединять не будем
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    if current is None:
                        link.destination = enter
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    if current is not None:
                        subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего
        else:  # иначе это альтернатива
            # вход альтернативы
            start = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                            comment="Point")
            id_counter += 1
            # выход альтернативы
            finish = DotNode(id_counter, color="black", tooltip="alternative", shape="point", fillcolor="white",
                             comment="Point")
            id_counter += 1

            subgraph.items += [start, finish]  # добавляем точки к частям подграфа

            # проходимся по веткам и создаём из них части подграфа
            for branch in self._branches:
                current = start  # грядущий первый элемент соединим с начальной точкой
                for item in branch:
                    part, new_id, enter, exit = item.to_graph(id_counter=id_counter)
                    id_counter = new_id
                    subgraph.items.append(part)
                    # не забываем соединить две части
                    subgraph.items.append(DotLink(current, enter, id_counter))
                    id_counter += 1
                    current = exit  # теперь конец нового элемента является зацепкой для следующего

                # не забываем соединить конец ветки с выходом альтернативы
                subgraph.items.append(DotLink(current, finish, id_counter))
                id_counter += 1

            link.destination = start

        wrapper = DotSubgraph(id_counter, color='white')
        wrapper.items += [global_enter, link, subgraph]

        return wrapper, id_counter, global_enter, global_exit


class Range:
    """
    Представляет диапазон в символьном классе.
    """

    def __init__(self, start: str, end: str):
        self._check_range(start, end)
        self._start = start[0]
        self._end = end[0]

    @property
    def start(self) -> str:
        return self._start

    @start.setter
    def start(self, value: str):
        self._check_range(value, self.end)
        self._start = value[0]

    @property
    def end(self) -> str:
        return self._end

    @end.setter
    def end(self, value: str):
        self._check_range(self.start, value)
        self._end = value[0]

    def __str__(self):
        return "from {0} to {1}".format(self.start, self.end)

    def __cmp__(self, other):
        return self.start == other.start and self.end == other.end

    @staticmethod
    def _check_range(start: str, end: str):
        if ord(start[0]) > ord(end[0]):
            raise ValueError("Начало интервала больше конца.")


class CharacterClass(Part, ICaseSensitive):
    """
    Символьный класс в регулярном выражении.
    """

    def __init__(self, is_inverted=False, id=None):
        Part.__init__(self, id=id)
        ICaseSensitive.__init__(self)
        self._is_inverted = is_inverted
        self._parts = [Text('')]

    @property
    def is_inverted(self) -> bool:
        return self._is_inverted

    @is_inverted.setter
    def is_inverted(self, value: bool):
        self._is_inverted = value

    def add_part(self, value):
        allowed_types = [Text, Charflag, Range]
        if allowed_types.count(type(value)) == 0:
            raise ValueError('Недопустимый тип части символьного класса.')
        if isinstance(value, Text):
            self._parts[0] += value
        elif self._parts.count(value) == 0:
            self._parts.append(value)

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        node = DotNode(
            self._id,
            self.generate_html(),
            tooltip='character class',
            comment=CharacterClass.__name__,
            shape='record',
            fillcolor=('' if self.is_sensitive else 'lightgrey'),
            style=('' if self.is_sensitive else 'filled')
        )
        return node, id_counter, node, node

    def generate_html(self):
        header = 'Any character from' if self.is_inverted else 'Any character except'
        filtered = list(filter(lambda i: str(i) != '', self._parts))
        result = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4"><TR><TD COLSPAN="{0}">' \
                 '<font face="Arial">{1}</font></TD></TR><TR>'.format(len(filtered), header)

        result += ''.join(['<TD>' + str(elem) + '</TD>' for elem in filtered])

        return result + '</TR></TABLE>>'


class ConditionalSubexpression(Part):
    """
    Представляет условное подвыражеине в регулярном выражении.
    """

    def __init__(self, condition, id=None):
        Part.__init__(self, id)
        if ConditionalSubexpression._allowed_types.count(type(condition)) == 0:
            raise ValueError('Недопустимый тип условия.')
        self._condition = condition
        """:type : SubexpressionCall|AssertComplex"""
        self._branch_true = []
        self._branch_false = []

    _allowed_types = [SubexpressionCall, AssertComplex]

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, value):
        if ConditionalSubexpression._allowed_types.count(type(value)) == 0:
            raise ValueError('Недопустимый тип условия.')
        self._condition = value

    @property
    def branch_true(self):
        return self._branch_true

    @branch_true.setter
    def branch_true(self, value):
        self._branch_true = value if isinstance(value, list) else []

    @property
    def branch_false(self):
        return self._branch_false

    @branch_false.setter
    def branch_false(self, value):
        self._branch_false = value if isinstance(value, list) else []

    def _build_condition(self, id_counter):
        condition = DotSubgraph(color='purple', tooltip='condition')
        part, id_counter, enter, exit = self.condition.to_graph(id_counter)
        condition.items.append(part)
        return condition, id_counter, enter, exit

    def _buld_branch(self, branch, id_counter):
        block = DotSubgraph(id_counter, style='dashed', color='purple')
        id_counter += 1

        global_enter = current = None
        for item in branch:
            part, id_counter, enter, exit = item.to_graph(id_counter)
            if global_enter is None:
                global_enter = enter
            block.items.append(part)
            if current is not None:
                block.items.append(DotLink(current, enter, id_counter))
            current = exit

        return block, id_counter, global_enter, current

    def to_graph(self, id_counter=1):
        id_counter = self._set_id_if_not_exist(id_counter)
        subgraph = DotSubgraph(id=self._id, tooltip='conditional subexpression')

        # формируем условие
        condition, id_counter, global_enter, current = self._build_condition(id_counter)
        subgraph.items.append(condition)

        # формируем начальную и конечную точки
        start_point = DotNode(id_counter, shape="point", fillcolor="white")
        id_counter += 1
        link = DotLink(current, start_point, id_counter)
        id_counter += 1
        global_end = end_point = DotNode(id_counter, shape="point", fillcolor="white")
        id_counter += 1
        subgraph.items += [start_point, link]

        # формируем истинную ветку
        current = start_point
        if len(self._branch_true) != 0:
            part, new_id, enter, exit = self._buld_branch(self._branch_true, id_counter)
            subgraph.items += [part, DotLink(current, enter, id_counter, 'true')]
            id_counter += 1
            current = exit
            label = ''
        else:
            label = 'true'

        # соединяем с выходной точкой условного подвыражения
        subgraph.items.append(DotLink(current, end_point, id_counter, label))
        id_counter += 1

        # формируем ложную ветку
        current = start_point
        if len(self._branch_false) != 0:
            part, new_id, enter, exit = self._buld_branch(self._branch_false, id_counter)
            subgraph.items += [part, DotLink(current, enter, id_counter, 'false')]
            id_counter += 1
            current = exit
            label = ''
        else:
            label = 'false'

        # соединяем с выходной точкой условного подвыражения
        subgraph.items.append(DotLink(current, end_point, id_counter, label))
        id_counter += 1
        subgraph.items.append(end_point)

        return subgraph, id_counter, global_enter, global_end

    @staticmethod
    def _perform_case_for_branch(branch, option=OptionCaseSensitivity(False)):
        for item in branch:
            if isinstance(item, OptionCaseSensitivity):
                option = item
            elif isinstance(item, ICaseSensitive):
                item.is_sensitive = not option.is_positive
            elif isinstance(item, PartContainer) or isinstance(item, ConditionalSubexpression):
                item._perform_case_option(option)

    def _perform_case_option(self, initial=OptionCaseSensitivity(False)):
        self._perform_case_for_branch(self.branch_true, initial)
        self._perform_case_for_branch(self.branch_false, initial)
        self._perform_case_for_branch(self.condition, initial)