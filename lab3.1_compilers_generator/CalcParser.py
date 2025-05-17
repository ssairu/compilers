import os
from dataclasses import dataclass
from enum import Enum
from ParseTable_calc import parse_table, terminals, axiom


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
    NUMBER = 0
    PLUS = 1
    STAR = 2
    LEFTPAREN = 3
    RIGHTPAREN = 4
    END_OF_PROGRAM = 5


@dataclass
class Token:
    tag: DomainTag
    coords: Fragment


class PlusToken(Token):
    value = 'plus sign'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.PLUS


class StarToken(Token):
    value = 'star'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.STAR


class LeftParenToken(Token):
    value = 'left paren'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.LEFTPAREN


class RightParenToken(Token):
    value = 'right paren'

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.tag = DomainTag.RIGHTPAREN


class NumberToken(Token):
    value = 'n'

    def __init__(self, code: int, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.code = code
        self.tag = DomainTag.NUMBER

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

            # Символы
            if current_char == '+':
                self._cur = self._cur.next()
                return PlusToken(start_pos, self._cur)
            if current_char == '*':
                self._cur = self._cur.next()
                return StarToken(start_pos, self._cur)
            if current_char == '(':
                self._cur = self._cur.next()
                return LeftParenToken(start_pos, self._cur)
            if current_char == ')':
                self._cur = self._cur.next()
                return RightParenToken(start_pos, self._cur)

            if self._cur.is_digit():
                return self._read_number(start_pos)

            self._compiler.add_message(True, start_pos, f"Unexpected character: {current_char}")
            self._cur = self._cur.next()

        return EndOfProgramToken(self._cur, self._cur)

    def _read_number(self, start_pos: Position):
        number_str = ""
        while self._cur.is_digit():
            number_str += self._cur.get_char()
            self._cur = self._cur.next()

        try:
            code = int(number_str)
            return NumberToken(code, start_pos, self._cur)
        except ValueError:
            self._compiler.add_message(True, start_pos, f"Invalid number: {number_str}")
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

    def get_solution(self, root: Node):
        solution = 0

        def traverse(node: Node):
            for child in node.children:
                traverse(child)

            if node.term == 'n':
                node.attr = node.token.code
            # Non-terminal nodes
            elif node.term == 'F':
                if len(node.children) > 1:
                    node.attr = node.children[1].attr
                else:
                    node.attr = node.children[0].attr

            elif node.term == 'T 1':
                node.attr = node.children[1].attr * node.children[2].attr if node.children else 1

            elif node.term == 'T':
                node.attr = node.children[0].attr * node.children[1].attr

            elif node.term == 'E 1':
                node.attr = node.children[1].attr + node.children[2].attr if node.children else 0

            elif node.term == 'E':
                node.attr = node.children[0].attr + node.children[1].attr

        traverse(root)
        return root.attr


    def to_graphviz(self, root: Node) -> str:
        def _escape_label(label: str) -> str:
            return label.replace('"', '\\"').replace('\n', '\\n')

        def _traverse(node: Node, dot_lines: list, node_ids: dict, counter: list):
            node_id = f"node_{counter[0]}"
            node_ids[node] = node_id
            counter[0] += 1

            label = node.term
            if node.token is not None:
                if node.token.tag == DomainTag.NUMBER:
                    label += f" = {node.token.code}"

            if node.attr is not None:
                label += f" ({node.attr})"

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


def main():
    input_file = "calc_problem.txt"
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        program = f.read()

    print("\nPROGRAM\n--------------------------------------")
    print(program)
    print("--------------------------------------\n")

    print("LEXEMS:")
    compiler = Compiler()
    scanner = compiler.get_scanner(program)
    tokens = []
    while True:
        token = scanner.next_token()
        if token is None:
            break
        tokens.append(token)
        if token.tag == DomainTag.END_OF_PROGRAM:
            break

    print("\nComments lexer:")
    for pos, text in scanner.comments:
        print(f"{pos} --- '{text}'")

    print("\nPARSING\n--------------------------------------")
    parser = ParserRules(program, compiler)
    parse_tree = parser.parse()
    result = parser.get_solution(parse_tree)
    if parse_tree:
        print("\nParse Tree (Graphviz):\n")
        print(parser.to_graphviz(parse_tree))
    else:
        print("\nParsing failed.")

    print(f"\n\n{program} = {result}")

    print("\nSyntax Analysis Messages:")
    compiler.output_messages()
    parser.output_messages()


if __name__ == "__main__":
    main()
