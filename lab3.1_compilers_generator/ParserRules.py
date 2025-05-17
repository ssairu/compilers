import os
from dataclasses import dataclass
from enum import Enum
from ParseTable_grammar import parse_table, terminals, axiom
from collections import defaultdict, deque
import sys

sys.setrecursionlimit(10000)


class Position:
    def __init__(self, text: str):
        self.col = 1
        self.line = 1
        self.index = 0
        self._text = text

    def __lt__(self, other):
        return self.index < other.index

    def __le__(self, other):
        return self.index <= other.index

    def __ge__(self, other):
        return self.index >= other.index

    def __gt__(self, other):
        return self.index > other.index

    def __ne__(self, other):
        return self.index != other.index

    def __eq__(self, other):
        return self.index == other.index

    def __str__(self):
        return f"({self.line}, {self.col})"

    def get_char(self):
        if self.index == len(self._text):
            return ''
        else:
            return self._text[self.index]

    def is_newline(self):
        if self.index == len(self._text):
            return True
        if (self._text[self.index] == '\r' and
                self.index + 1 < len(self._text)):
            return self._text[self.index + 1] == '\n'
        return self._text[self.index] == '\n'

    def is_digit(self):
        s = self.get_char()
        return '0' <= s <= '9'

    def is_whitespace(self):
        s = self.get_char()
        return s == ' ' or s == '\r' or s == '\n' or s == '\t'

    def is_latin_char(self):
        s = self.get_char()
        return 'a' <= s.lower() <= 'z'

    def is_letter_or_space(self):
        s = self.get_char()
        return self.is_latin_char() or s == ' '

    def next(self):
        pos = Position(self._text)
        pos.col = self.col
        pos.index = self.index
        pos.line = self.line
        if pos.index < len(pos._text):
            if pos.is_newline():
                if pos._text[pos.index] == '\r':
                    pos.index += 1
                pos.line += 1
                pos.col = 1
            else:
                pos.col += 1
            pos.index += 1
        return pos


class Fragment:
    def __init__(self, starting: Position, following: Position):
        self.starting = starting
        self.following = following

    def __str__(self):
        return f"{str(self.starting)}-{str(self.following)}"


class Message:
    def __init__(self, is_error: bool, text: str):
        self.is_error = is_error
        self.text = text


class Compiler:
    def __init__(self):
        self.__messages = []
        self.__nameCodes = {}
        self.__names = []

    def add_name(self, name: str):
        if name in self.__nameCodes:
            return self.__nameCodes[name]
        else:
            code = len(self.__names)
            self.__names.append(name)
            self.__nameCodes[name] = code
            return code

    def get_name(self, code: int):
        return self.__names[code]

    def add_message(self, isError: bool, pos: Position, text: str):
        self.__messages += [[pos, Message(isError, text)]]

    def output_messages(self):
        for position, message in self.__messages:
            if message.is_error:
                print(f"Error {position}: {message.text}")
            else:
                print(f"Warning {position}: {message.text}")

    def get_scanner(self, program: str):
        return Scanner(program, self)


class DomainTag(Enum):
    KEYWORD = 0
    COMMA = 1
    DOT = 2
    IDENTIFIER = 3
    END_OF_PROGRAM = 4


@dataclass
class Token:
    tag: DomainTag
    coords: Fragment


class KeywordToken(Token):
    def __init__(self, value: str, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.value = value
        self.tag = DomainTag.KEYWORD


class CommaToken(Token):
    value = ','

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.COMMA


class DotToken(Token):
    value = '.'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.DOT


class IdentifierToken(Token):
    value = 'id'

    def __init__(self, code: int, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.code = code
        self.tag = DomainTag.IDENTIFIER

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        return self.code == other.code

    def __int__(self):
        return self.code


class EndOfProgramToken(Token):
    value = '$'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.END_OF_PROGRAM


class Scanner:
    def __init__(self, program: str, compiler: Compiler):
        self.program = program
        self._compiler = compiler
        self._cur = Position(program)
        self._comments = []

    @property
    def comments(self):
        return [[c, self.program[c.starting.index:c.following.index]] for c in self._comments]

    def next_token(self):
        while self._cur.get_char():
            while self._cur.is_whitespace():
                self._cur = self._cur.next()

            start_pos = self._cur
            current_char = self._cur.get_char()

            if not current_char:
                return EndOfProgramToken(self._cur, self._cur)

            # Обработка комментария: начинается с (*
            if current_char == '(' and self._cur.next().get_char() == '*':
                self._skip_comment(start_pos)
                continue

            # Символы
            if current_char == ',':
                self._cur = self._cur.next()
                return CommaToken(start_pos, self._cur)
            if current_char == '.':
                self._cur = self._cur.next()
                return DotToken(start_pos, self._cur)

            # Идентификатор: начинается с (
            if current_char == '(':
                return self._read_identifier(start_pos)

            # Ключевые слова
            if self._cur.is_latin_char():
                return self._read_keyword(start_pos)

            self._compiler.add_message(True, start_pos, f"Unexpected character: {current_char}")
            self._cur = self._cur.next()

        return EndOfProgramToken(self._cur, self._cur)

    def _skip_comment(self, start_pos: Position):
        # Пропускаем (* и читаем до *)
        self._cur = self._cur.next().next()  # Пропускаем (*
        while self._cur.get_char():
            if self._cur.get_char() == '*' and self._cur.next().get_char() == ')':
                end_pos = self._cur
                self._cur = self._cur.next().next()  # Пропускаем *)
                self._comments.append(Fragment(start_pos.next().next(), end_pos))
                return
            self._cur = self._cur.next()
        self._compiler.add_message(True, start_pos, "Unterminated comment")

    def _read_identifier(self, start_pos: Position):
        self._cur = self._cur.next()  # Пропускаем (
        lexeme = ""
        while self._cur.get_char() != ')' and self._cur.get_char() != '':
            lexeme += self._cur.get_char()
            self._cur = self._cur.next()
        if self._cur.get_char() != ')':
            self._compiler.add_message(True, start_pos, "Expected closing parenthesis for identifier")
            return None
        self._cur = self._cur.next()  # Пропускаем )
        end_pos = self._cur
        lexeme = lexeme.strip()
        if not lexeme:
            self._compiler.add_message(True, start_pos, "Empty identifier")
            return None
        code = self._compiler.add_name(lexeme)
        return IdentifierToken(code, start_pos, end_pos)

    def _read_keyword(self, start_pos: Position):
        lexeme = ""
        while self._cur.get_char() and self._cur.is_latin_char():
            lexeme += self._cur.get_char()
            self._cur = self._cur.next()
        end_pos = self._cur
        if lexeme in {"tokens", "is", "start"}:
            return KeywordToken(lexeme, start_pos, end_pos)
        self._compiler.add_message(True, start_pos, f"Unknown keyword: {lexeme}")
        return None


class Node:
    def __init__(self, term: str, token=None, attr=None):
        self.term = term
        self.token = token
        self.attr = attr
        self.children = []

    def __str__(self):
        return self.term + "   " + str(self.token.coords if self.token else "none") + " : " + str(self.children) + "  ___  " + str(self.attr)


class ParserRules:
    def __init__(self, program, compiler: Compiler):
        self.scanner = compiler.get_scanner(program)
        self.compiler = compiler
        self._messages = []
        self.table = parse_table

    def add_message(self, is_error: bool, pos: Position, text: str):
        self._messages.append([pos, Message(is_error, text)])

    def output_messages(self):
        for position, message in self._messages:
            if message.is_error:
                print(f"Error {position}: {message.text}")
            else:
                print(f"Warning {position}: {message.text}")

    def parse(self):
        stack = ['$', axiom]
        root = Node(axiom)
        node_stack = [root]
        token = self.scanner.next_token()
        while node_stack:
            X = stack.pop()
            # print([str(i) for i in node_stack])
            current_node = node_stack.pop()
            # print(token.tag)
            # print(stack)
            a = self._get_token_symbol(token)

            if X in terminals + ['$']:
                if X == a:
                    current_node.token = token
                    token = self.scanner.next_token()
                else:
                    self.add_message(True, token.coords.starting,
                                     f"Expected {X}, got {a}")
                    return None
            else:
                key = (X, a)
                if key in self.table:
                    production = self.table[key]
                    for symbol in reversed(production):
                        stack.append(symbol)
                        child = Node(symbol)
                        current_node.children.append(child)
                        node_stack.append(child)
                    current_node.children.reverse()
                else:
                    self.add_message(True, token.coords.starting,
                                     f"No rule for {X} on {a}")
                    return None

        last_token = self.scanner.next_token()
        if not last_token.tag == DomainTag.END_OF_PROGRAM:
            self.add_message(True, last_token.coords.starting,
                             f"Unexpected token: {self._get_token_symbol(last_token)}")
            return None

        return root

    def _get_token_symbol(self, token):
        if token is None:
            return 'error'
        elif token.tag == DomainTag.END_OF_PROGRAM:
            return '$'
        return token.value

    def to_graphviz(self, root: Node) -> str:
        def _escape_label(label: str) -> str:
            return label.replace('"', '\\"').replace('\n', '\\n')

        def _traverse(node: Node, dot_lines: list, node_ids: dict, counter: list):
            node_id = f"node_{counter[0]}"
            node_ids[node] = node_id
            counter[0] += 1

            label = node.term
            if node.token is not None:
                if node.token.tag == DomainTag.IDENTIFIER:
                    label += f" = ({self.compiler.get_name(node.token.code)})"
                elif node.token.tag == DomainTag.KEYWORD:
                    label += f" = {node.token.value}"

            dot_lines.append(f'    {node_id} [label="{_escape_label(label)}"];')

            s = " { rank=same; "
            for child in node.children:
                _traverse(child, dot_lines, node_ids, counter)
                dot_lines.append(f'    {node_id} -> {node_ids[child]};')
                if child == node.children[0]:
                    s += f'{node_ids[child]} '
                else:
                    s += f'-> {node_ids[child]} '
            if len(node.children) >= 2:
                dot_lines.append(s + '[style=invis] }')

        if root is None:
            return "digraph G { }"

        dot_lines = ['digraph ParseTree {']
        node_ids = {}
        counter = [0]
        _traverse(root, dot_lines, node_ids, counter)
        dot_lines.append('}')

        return '\n'.join(dot_lines)


class TableGenerator:
    def __init__(self, k_param=1):
        self.grammar_str = ''
        self.NT_To_Rules = defaultdict(list)
        self.rules = []
        self.allNTs = set([])
        self.terminals = set([])
        self.startingNT = None
        self.k = k_param

        self.compiler = None
        self.parser = None

        self.first = defaultdict(set)
        self.follow = defaultdict(set)
        self.parseTable = defaultdict(list)

        self.PDAstates = []
        self.PDAstart = []
        self.PDAfinal = []
        self.PDAstack = deque()
        self.PDAtrans = []
        self.parsing_str = ''
        self.pos = 0
        self.nextk = ''
        self.allready_read = ''

    def get_rules(self, root: Node):
        self.NT_To_Rules = defaultdict(list)
        self.allNTs = set()
        self.terminals = set()
        self.startingNT = None

        right_symbols = set()

        def traverse(node: Node):
            for child in node.children:
                traverse(child)

            if node.term == 'id':
                node.attr = [node.token]
            # Non-terminal nodes
            elif node.term == 'rule':
                # rule ::= id is SP RP
                # print(node)
                # print(node.children[0])
                nt = node.children[0].attr[0]  # Non-terminal (id)
                symbols = node.children[2].attr  # SP symbols
                for x in symbols:
                    right_symbols.add(x)
                # print(self.compiler.get_name(node.children[0].attr[0]))
                # print([self.compiler.get_name(term) for term in symbols])
                self.allNTs.add(nt)
                self.NT_To_Rules[nt].append(symbols)

            elif node.term == 'SP':
                # SP ::= id SP | ε
                node.attr = node.children[0].attr + node.children[1].attr if node.children else []

            elif node.term == 'tokens-decl':
                # tokens-decl ::= tokens id TI .

                node.attr = node.children[1].attr + node.children[2].attr
                if node.children[1].attr[0] in self.terminals:
                    self.parser.compiler.add_message(True, node.children[1].attr[0].coords.starting,
                                                     f"Repeated terminal: ({self.parser.compiler.get_name(node.children[1].attr[0].code)})")
                self.terminals.update(node.attr)

            elif node.term == 'TI':
                # TI ::= , id TI | ε
                if node.children:
                    node.attr = node.children[1].attr + node.children[2].attr
                    if node.children[1].attr[0] in self.terminals:
                        self.parser.compiler.add_message(True, node.children[1].attr[0].coords.starting,
                                                         f"Repeated terminal: ({self.parser.compiler.get_name(node.children[1].attr[0].code)})")
                else:
                    node.attr = []

            elif node.term == 'axiom':
                # axiom ::= start id .
                if self.startingNT:
                    self.parser.compiler.add_message(True, node.children[1].attr[0].coords.starting,
                                                     f"Can't set axiom ({self.parser.compiler.get_name(node.children[1].attr[0].code)}), "
                                                     f"axiom is already ({self.parser.compiler.get_name(self.startingNT.code)})")

                self.startingNT = node.children[1].attr[0]
            else:
                node.attr = []

        traverse(root)

        if not self.startingNT:
            self.parser.compiler.add_message(True, self.parser.scanner.next_token().coords.starting,
                                             f"axiom is not set")

        for x in right_symbols:
            if x not in self.terminals.union(self.allNTs):
                self.parser.compiler.add_message(True, x.coords.starting,
                                                 f"Undefined token: ({self.parser.compiler.get_name(x.code)})")

    def readGrammar(self, grammar):
        self.first = defaultdict(set)
        self.follow = defaultdict(set)
        self.parseTable = defaultdict(list)

        self.compiler = Compiler()
        self.parser = ParserRules(grammar, self.compiler)
        parse_tree = self.parser.parse()
        # print(self.parser.to_graphviz(parse_tree))
        self.get_rules(parse_tree)
        self.rules = []
        for NT, rightRules in self.NT_To_Rules.items():
            for rightRule in rightRules:
                self.rules.append((NT, rightRule))

    def getFirstK(self, str):
        return str[:self.k]

    def FirstK_concatStringSets(self, sets):
        if len(sets) == 1:
            return {tuple(s) for s in sets[0]}

        if sets[0] == {}:
            return {}
        else:
            result = sets[0]

        if sets[1] == {}:
            return {}

        new_result = set()
        for x in result:
            for y in sets[1]:
                concat = list(x) + list(y)
                new_result.add(tuple(self.getFirstK(concat)))
        result = new_result

        return self.FirstK_concatStringSets([result] + sets[2:])

    def createFirst(self):
        new_first = defaultdict(set)
        for NT in self.allNTs:
            new_first[NT] = set()

        for T in self.terminals:
            new_first[T] = {tuple([T])}

        while not (self.first == new_first):
            for key, value in new_first.items():
                self.first[key] = value

            for NT, rule in self.rules:
                if not rule:
                    new_first[NT].add(tuple([]))
                else:
                    first_k = self.FirstK_concatStringSets([new_first[symbol] for symbol in rule])
                    new_first[NT] = new_first[NT].union(first_k)

    def createFollow(self):
        new_follow = defaultdict(set)
        new_follow[self.startingNT] = {tuple([])}

        for NT in self.allNTs:
            if NT != self.startingNT:
                new_follow[NT] = set()

        while not (self.follow == new_follow):
            for key, value in new_follow.items():
                self.follow[key] = value

            for NT, rule in self.rules:
                for i, symbol in enumerate(rule):
                    if symbol in self.allNTs:
                        follow_set = self.FirstK_concatStringSets(
                            [self.first[s] for s in rule[i + 1:]] + [new_follow[NT]]
                        )
                        new_follow[symbol] = new_follow[symbol].union(follow_set)

    def createParseTable(self, grammar, name):
        self.readGrammar(grammar)
        if not self.startingNT:
            return
        self.createFirst()
        self.createFollow()

        parseTable = defaultdict(set)
        for NT, rule in self.rules:
            for x in self.FirstK_concatStringSets([self.first[s] for s in rule] + [self.follow[NT]]):
                parseTable[(NT, x)] = parseTable[(NT, x)].union({tuple(rule)})
                if len(parseTable[(NT, x)]) > 1:
                    self.compiler.add_message(True, NT.coords.starting,
                                              f"({self.compiler.get_name(NT.code)}) NOT LL(1)!!!")

        for key, value in parseTable.items():
            self.parseTable[key] = list(value)

        with open(name, 'w', encoding='utf-8') as f:
            f.write("# Auto-generated parse axiom\n")
            f.write(f"axiom = '{self.compiler.get_name(self.startingNT.code)}'\n\n")

            f.write("# Auto-generated parse terms\n")
            f.write(f"terminals = {[self.compiler.get_name(x.code) for x in self.terminals]}\n\n")

            f.write("# Auto-generated parse table\n")
            f.write("parse_table = {\n")
            for key, rules in self.parseTable.items():
                nt = self.compiler.get_name(key[0].code)
                if key[1]:
                    lookahead = self.compiler.get_name(key[1][0].code)
                else:
                    lookahead = "$"
                if len(rules) > 1:
                    rules_str = "[" + ", ".join([str(list(
                        [self.compiler.get_name(term.code) for term in rule]
                    )) for rule in rules]) + "]"
                else:
                    rules_str = str(list([self.compiler.get_name(term.code) for term in rules[0]]))
                f.write(f"    ('{nt}', '{lookahead}'): {rules_str},\n")
            f.write("}\n")

    def check_ll_k(self):
        ll_mark = True
        for rules in self.parseTable.values():
            if len(rules) > 1:
                ll_mark = False
        return ll_mark


def read_file(path):
    input_file = path
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        program = f.read()
    return program


def main():
    PDA = TableGenerator(1)
    program = read_file("compiler_grammar.txt")
    PDA.createParseTable(program, 'ParseTable_grammar.py')
    PDA.compiler.output_messages()

    program = read_file("input.txt")
    PDA.createParseTable(program, 'ParseTable_calc.py')
    PDA.compiler.output_messages()


if __name__ == "__main__":
    main()

#
# def main():
#     input_file = "compiler_grammar.txt"
#     if not os.path.exists(input_file):
#         print(f"Error: File {input_file} not found")
#         return
#
#     with open(input_file, "r", encoding="utf-8") as f:
#         program = f.read()
#
#     print("\nPROGRAM\n--------------------------------------")
#     print(program)
#     print("--------------------------------------\n")
#
#     print("LEXEMS:")
#     compiler = Compiler()
#     scanner = compiler.get_scanner(program)
#     tokens = []
#     while True:
#         token = scanner.next_token()
#         if token is None:
#             break
#         tokens.append(token)
#         if token.tag == DomainTag.END_OF_PROGRAM:
#             break
#
#     for token in tokens:
#         if token.tag == DomainTag.IDENTIFIER:
#             name = compiler.get_name(token.code)
#             print(f"IDENT {token.coords}: {name}")
#         elif token.tag == DomainTag.KEYWORD:
#             print(f"KEYWORD {token.coords}: {token.value}")
#         elif token.tag == DomainTag.COMMA:
#             print(f"COMMA {token.coords}: {token.value}")
#         elif token.tag == DomainTag.DOT:
#             print(f"DOT {token.coords}: {token.value}")
#         elif token.tag == DomainTag.END_OF_PROGRAM:
#             print(f"END {token.coords}:")
#
#     print("\nComments:")
#     for pos, text in scanner.comments:
#         print(f"{pos} --- '{text}'")
#
#     print("\nPARSING\n--------------------------------------")
#     parser = ParserRules(program, compiler)
#     parse_tree = parser.parse()
#     if parse_tree:
#         print("\nParse Tree (Graphviz):\n")
#         print(parser.to_graphviz(parse_tree))
#     else:
#         print("\nParsing failed.")
#
#     print("\nSyntax Analysis Messages:")
#     compiler.output_messages()
#     parser.output_messages()
#
#
# if __name__ == "__main__":
#     main()
