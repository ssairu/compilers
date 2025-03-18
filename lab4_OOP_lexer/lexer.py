from enum import Enum
import os


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

    def is_latin_char(self):
        s = self.get_char()
        return ('a' <= s <= 'z') or ('A' <= s <= 'Z')

    def is_whitespace(self):
        s = self.get_char()
        return s == ' ' or s == '\r' or s == '\n' or s == '\t'

    def is_star(self):
        s = self.get_char()
        return s == '*'

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


class DomainTag(Enum):
    IDENT = 0
    KEY_WORD = 1
    SYMBOL = 2
    END_OF_PROGRAM = 3


class IdentToken:
    tag = DomainTag.IDENT

    def __init__(self, code: int, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.code = code


class KeyWordToken:
    tag = DomainTag.KEY_WORD

    def __init__(self, word: str, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.word = word


class SymbolToken:
    tag = DomainTag.SYMBOL

    def __init__(self, symbol: str, starting: Position, following: Position):
        self.coords = Fragment(starting, following)
        self.symbol = symbol


class EndOfProgramToken:
    tag = DomainTag.END_OF_PROGRAM

    def __init__(self, starting: Position, following: Position):
        self.coords = Fragment(starting, following)


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


class Scanner:
    def __init__(self, program: str, compiler: Compiler):
        self._compiler = compiler
        self.program = program
        self._cur = Position(program)
        self._comments = []

    @property
    def comments(self):
        return [[c,
                 self.program[c.starting.index+1:c.following.index]]
                for c in self._comments]

    def next_token(self):
        while not self._cur.get_char() == '':
            while self._cur.is_whitespace():
                self._cur = self._cur.next()

            start_pos = self._cur
            current_char = self._cur.get_char()

            if current_char == '':
                return EndOfProgramToken(self._cur, self._cur)

            if self._cur.is_star() and (self._cur.col == 1):
                self._skip_comment(start_pos)
                continue

            if current_char == "'":
                return self._read_symbol_literal(start_pos)

            if self._cur.is_latin_char() or self._cur.is_star():
                return self._read_identifier_or_keyword(start_pos)

            self._compiler.add_message(True, start_pos, f"Unexpected character: {current_char}")
            self._cur = self._cur.next()

        return EndOfProgramToken(self._cur, self._cur)

    def _skip_comment(self, start_pos: Position):
        while not self._cur.is_newline() and self._cur.get_char() != '':
            self._cur = self._cur.next()
        end_pos = self._cur
        self._comments.append(Fragment(start_pos, end_pos))
        self._cur = self._cur.next()

    def _read_symbol_literal(self, start_pos: Position):
        self._cur = self._cur.next()
        if self._cur.get_char() == "'":
            self._cur = self._cur.next()
        else:
            self._compiler.add_message(True, start_pos,
                                       "expected 2 apostrophes -- '' --, "
                                       "get only one -- ' --")

        if self._cur.get_char() == "'" and self._cur.next().get_char() == "'":
            self._compiler.add_message(False, start_pos,
                                       "expected any symbol literal, "
                                       "but get nothing")
            self._cur = self._cur.next()
            symbol = ''
        else:
            symbol = self._cur.get_char()
            if self._cur.next().get_char() != "'":
                self._compiler.add_message(True,
                                           start_pos,
                                           "Unterminated symbol literal")
            else:
                self._cur = self._cur.next()
                if self._cur.next().get_char() != "'":
                    self._compiler.add_message(True,
                                               start_pos,
                                               "Unterminated symbol literal")
                else:
                    self._cur = self._cur.next()

        self._cur = self._cur.next()
        return SymbolToken(symbol, start_pos, self._cur)

    def _read_identifier_or_keyword(self, start_pos: Position):
        lexeme = ""
        if self._cur.is_star():
            while self._cur.is_star():
                lexeme += self._cur.get_char()
                self._cur = self._cur.next()
        elif self._cur.is_latin_char():
            lexeme += self._cur.get_char()
            prev_cur = self._cur
            self._cur = self._cur.next()
            while self._cur.is_latin_char() and prev_cur.is_latin_char():
                if prev_cur > self._cur:
                    lexeme += self._cur.get_char() + prev_cur.get_char()
                    self._cur = self._cur.next().next()
                    if lexeme == "wit" and self._cur.get_char() == 'h' and not self._cur.next().is_latin_char():
                        lexeme = "with"
                        self._cur = self._cur.next()
                        break
                else:
                    prev_cur = self._cur.next()
        end_pos = self._cur

        if lexeme in {"with", "end", "**"}:
            return KeyWordToken(lexeme, start_pos, end_pos)

        if lexeme.isalpha():
            code = self._compiler.add_name(lexeme)
            return IdentToken(code, start_pos, end_pos)
        else:
            code = self._compiler.add_name(lexeme)
            return IdentToken(code, start_pos, end_pos)


def main():
    input_file = "input.txt"
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
        tokens.append(token)
        if token.tag == DomainTag.END_OF_PROGRAM:
            break

    for token in tokens:
        if token.tag == DomainTag.IDENT:
            name = compiler.get_name(token.code)
            print(f"IDENT {token.coords}: {name}")
        elif token.tag == DomainTag.KEY_WORD:
            print(f"KEYWORD {token.coords}: {token.word}")
        elif token.tag == DomainTag.SYMBOL:
            print(f"SYMBOL {token.coords}: {token.symbol}")
        elif token.tag == DomainTag.END_OF_PROGRAM:
            print(f"END {token.coords}:")

    print("\nMessages:")
    compiler.output_messages()

    print("\nComments:")
    for pos, text in scanner.comments:
        print(f"{pos} --- '{text}'")


if __name__ == "__main__":
    main()
