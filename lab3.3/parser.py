import parser_edsl as pe
import abc
import enum
import sys
import typing
from dataclasses import dataclass
from pprint import pprint


# Определение типов
class Type(enum.Enum):
    Int = 'int'
    Char = 'char'
    Double = 'double'
    Struct = 'struct'
    Union = 'union'
    Enum = 'enum'


# Класс для семантических ошибок
class SemanticError(pe.Error):
    def __init__(self, pos, message):
        self.pos = pos
        self.__message = message

    @property
    def message(self):
        return self.__message


# Абстрактные классы
class TypeSpecifier(abc.ABC):
    @abc.abstractmethod
    def check(self, tags, pos):
        pass

    @abc.abstractmethod
    def size(self, tags, consts):
        pass


class EnumTerm(abc.ABC):
    @abc.abstractmethod
    def check(self, tags, consts):
        pass

    @abc.abstractmethod
    def evaluate(self, tags, consts):
        pass


class Declaration(abc.ABC):
    @abc.abstractmethod
    def check(self, tags, consts):
        pass


class MemberDecl(abc.ABC):
    @abc.abstractmethod
    def check(self, tags, consts):
        pass

    @abc.abstractmethod
    def size(self, tags, consts):
        pass


class DirectDeclarator(abc.ABC):
    @abc.abstractmethod
    def check(self, tags, consts):
        pass


# Типы данных
@dataclass
class SympleType(TypeSpecifier):
    type: Type

    def check(self, tags, pos):
        pass

    def size(self, tags, consts):
        if self.type == Type.Int:
            return 4
        elif self.type == Type.Char:
            return 4  # Можно изменить на 1, если требуется
        elif self.type == Type.Double:
            return 8
        return 0


@dataclass
class IdentifierTerm(EnumTerm):
    name: str
    name_coord: pe.Position

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, = attrs
        cname, = coords
        return IdentifierTerm(name, cname.start)

    def check(self, tags, consts):
        if self.name not in consts:
            raise SemanticError(self.name_coord, f"Необъявленная константа {self.name}")

    def evaluate(self, tags, consts):
        if self.name not in consts:
            raise SemanticError(self.name_coord, f"Необъявленная константа {self.name}")
        return consts[self.name]


@dataclass
class NamedType(TypeSpecifier):
    type: Type
    identifier: IdentifierTerm

    @pe.ExAction
    def create_struct(attrs, coords, res_coord):
        id, = attrs
        _, cid = coords
        return NamedType(Type.Struct, IdentifierTerm(id, cid.start))

    @pe.ExAction
    def create_union(attrs, coords, res_coord):
        id, = attrs
        _, cid = coords
        return NamedType(Type.Union, IdentifierTerm(id, cid.start))

    @pe.ExAction
    def create_enum(attrs, coords, res_coord):
        id, = attrs
        _, cid = coords
        return NamedType(Type.Enum, IdentifierTerm(id, cid.start))

    def check(self, tags, pos):
        if self.identifier.name not in tags:
            raise SemanticError(self.identifier.name_coord, f"Необъявленный тег {self.identifier.name}")
        decl = tags[self.identifier.name]
        decl_type = {
            StructDecl: Type.Struct,
            UnionDecl: Type.Union,
            EnumDecl: Type.Enum
        }.get(type(decl))
        if decl_type is None:
            raise SemanticError(self.identifier.name_coord, f"Тег {self.identifier.name} имеет неподдерживаемый тип")
        if decl_type != self.type:
            raise SemanticError(self.identifier.name_coord, f"Тег {self.identifier.name} не соответствует типу {self.type.value}")

    def size(self, tags, consts):
        if self.identifier.name not in tags:
            raise SemanticError(self.identifier.name_coord, f"Необъявленный тег {self.identifier.name}")
        return tags[self.identifier.name].size(tags, consts)


@dataclass
class IntegerConstantTerm(EnumTerm):
    value: int

    def check(self, tags, consts):
        pass

    def evaluate(self, tags, consts):
        return self.value


@dataclass
class SizeofTerm(EnumTerm):
    type_specifier: TypeSpecifier
    sizeof_coord: pe.Position

    @pe.ExAction
    def create(attrs, coords, res_coord):
        type_specifier, = attrs
        csizeof, copen, ctype, cclose = coords
        return SizeofTerm(type_specifier, csizeof.start)

    def check(self, tags, consts):
        self.type_specifier.check(tags, self.sizeof_coord)

    def evaluate(self, tags, consts):
        return self.type_specifier.size(tags, consts)


@dataclass
class EnumExpr(EnumTerm):
    terms: list[EnumTerm]
    operators: list[str]
    first_term_coord: pe.Position

    @pe.ExAction
    def create(attrs, coords, res_coord):
        term, = attrs
        cterm, = coords
        return EnumExpr([term], [], cterm.start)

    @pe.ExAction
    def create_binop(attrs, coords, res_coord):
        term, op, expr = attrs
        cterm, cop, cexpr = coords
        return EnumExpr([term] + expr.terms, [op] + expr.operators, cterm.start)

    def check(self, tags, consts):
        for term in self.terms:
            term.check(tags, consts)

    def evaluate(self, tags, consts):
        result = self.terms[0].evaluate(tags, consts)
        for op, term in zip(self.operators, self.terms[1:]):
            val = term.evaluate(tags, consts)
            if op == '+':
                result += val
            elif op == '-':
                result -= val
            elif op == '*':
                result *= val
            elif op == '/':
                if val == 0:
                    raise SemanticError(self.first_term_coord, f"Деление на ноль в выражении перечисления")
                result //= val
        return result


@dataclass
class EnumConstant:
    name: str
    name_coord: pe.Position
    value: typing.Optional[EnumExpr]

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, = attrs
        cname, = coords
        return EnumConstant(name, cname.start, None)

    @pe.ExAction
    def create_with_value(attrs, coords, res_coord):
        name, expr = attrs
        cname, ceq, cexpr = coords
        return EnumConstant(name, cname.start, expr)

    def check(self, tags, consts):
        if self.name in consts:
            raise SemanticError(self.name_coord, f"Повторная константа {self.name}")
        if self.value:
            self.value.check(tags, consts)


@dataclass
class EnumBody:
    constants: list[EnumConstant]

    def check(self, tags, consts):
        for constant in self.constants:
            constant.check(tags, consts)


@dataclass
class IdentifierDeclarator(DirectDeclarator):
    name: str
    name_coord: pe.Position

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, = attrs
        cname, = coords
        return IdentifierDeclarator(name, cname.start)

    def check(self, tags, consts):
        pass


@dataclass
class ArrayDeclarator(DirectDeclarator):
    name: str
    name_coord: pe.Position
    dimensions: list[EnumExpr]

    @pe.ExAction
    def create(attrs, coords, res_coord):
        name, dimensions = attrs
        cname, cdims = coords
        return ArrayDeclarator(name, cname.start, dimensions)

    def check(self, tags, consts):
        for dim in self.dimensions:
            dim.check(tags, consts)


@dataclass
class Declarator:
    pointer_count: int
    direct_declarator: DirectDeclarator
    star_coord: typing.Optional[pe.Position]

    @pe.ExAction
    def create(attrs, coords, res_coord):
        pointer, direct = attrs
        cpointer, cdirect = coords
        star_coord = cpointer[0].start if isinstance(cpointer, list) else None
        return Declarator(pointer, direct, star_coord)

    def check(self, tags, consts):
        self.direct_declarator.check(tags, consts)


@dataclass
class TypeMemberDecl(MemberDecl):
    type_specifier: TypeSpecifier
    declarators: list[Declarator]
    type_coord: pe.Position

    @pe.ExAction
    def create(attrs, coords, res_coord):
        type_spec, declarator, comma_decls = attrs
        ctype, cdecl, ccomma, csemi = coords
        return TypeMemberDecl(type_spec, [declarator] + comma_decls, ctype.start)

    def check(self, tags, consts):
        self.type_specifier.check(tags, self.type_coord)
        member_names = set()
        for decl in self.declarators:
            decl.check(tags, consts)
            name = decl.direct_declarator.name
            if name in member_names:
                raise SemanticError(decl.direct_declarator.name_coord, f"Повторное поле {name}")
            member_names.add(name)

    def size(self, tags, consts):
        total_size = 0
        for decl in self.declarators:
            base_size = 4 if decl.pointer_count > 0 else self.type_specifier.size(tags, consts)
            if isinstance(decl.direct_declarator, ArrayDeclarator):
                for dim in decl.direct_declarator.dimensions:
                    base_size *= dim.evaluate(tags, consts)
            total_size += base_size
        return total_size


@dataclass
class NestedDecl(MemberDecl):
    nested_decl: Declaration

    def check(self, tags, consts):
        self.nested_decl.check(tags, consts)

    def size(self, tags, consts):
        return self.nested_decl.size(tags, consts)


@dataclass
class StructUnionBody:
    members: list[MemberDecl]

    def check(self, tags, consts):
        for member in self.members:
            member.check(tags, consts)

    def size(self, tags, consts, is_union=False):
        if is_union:
            return max((member.size(tags, consts) for member in self.members), default=0)
        return sum(member.size(tags, consts) for member in self.members)


@dataclass
class StructDecl(Declaration):
    identifier: typing.Optional[IdentifierTerm]
    body: typing.Optional[StructUnionBody]
    declarators: list[Declarator]

    @pe.ExAction
    def create_with_id_and_body(attrs, coords, res_coord):
        id, body, decls = attrs
        _, cid, _, _, _, cdecls, _ = coords
        return StructDecl(IdentifierTerm(id, cid.start), body, decls)

    @pe.ExAction
    def create_with_id(attrs, coords, res_coord):
        id, decls = attrs
        _, cid, cdecls, _ = coords
        return StructDecl(IdentifierTerm(id, cid.start), None, decls)

    @pe.ExAction
    def create_with_body(attrs, coords, res_coord):
        body, decls = attrs
        _, _, _, _, cdecls, _ = coords
        return StructDecl(None, body, decls)

    @pe.ExAction
    def create_empty(attrs, coords, res_coord):
        decls, = attrs
        _, cdecls, _ = coords
        return StructDecl(None, None, decls)

    def check(self, tags, consts):
        if self.identifier:
            if self.identifier.name in tags:
                raise SemanticError(self.identifier.name_coord, f"Повторный тег структуры {self.identifier.name}")
            tags[self.identifier.name] = self
        if self.body:
            self.body.check(tags, consts)
        for decl in self.declarators:
            decl.check(tags, consts)

    def size(self, tags, consts):
        if self.body:
            return self.body.size(tags, consts)
        return 0


@dataclass
class UnionDecl(Declaration):
    identifier: typing.Optional[IdentifierTerm]
    body: typing.Optional[StructUnionBody]
    declarators: list[Declarator]

    @pe.ExAction
    def create_with_id_and_body(attrs, coords, res_coord):
        id, body, decls = attrs
        _, cid, _, _, _, cdecls, _ = coords
        return UnionDecl(IdentifierTerm(id, cid.start), body, decls)

    @pe.ExAction
    def create_with_id(attrs, coords, res_coord):
        id, decls = attrs
        _, cid, cdecls, _ = coords
        return UnionDecl(IdentifierTerm(id, cid.start), None, decls)

    @pe.ExAction
    def create_with_body(attrs, coords, res_coord):
        body, decls = attrs
        _, _, _, _, cdecls, _ = coords
        return UnionDecl(None, body, decls)

    @pe.ExAction
    def create_empty(attrs, coords, res_coord):
        decls, = attrs
        _, cdecls, _ = coords
        return UnionDecl(None, None, decls)

    def check(self, tags, consts):
        if self.identifier:
            if self.identifier.name in tags:
                raise SemanticError(self.identifier.name_coord, f"Повторный тег объединения {self.identifier.name}")
            tags[self.identifier.name] = self
        if self.body:
            self.body.check(tags, consts)
        for decl in self.declarators:
            decl.check(tags, consts)

    def size(self, tags, consts):
        if self.body:
            return self.body.size(tags, consts, is_union=True)
        return 0


@dataclass
class EnumDecl(Declaration):
    identifier: typing.Optional[IdentifierTerm]
    body: typing.Optional[EnumBody]
    declarators: list[Declarator]

    @pe.ExAction
    def create_with_id_and_body(attrs, coords, res_coord):
        id, body, decls = attrs
        _, cid, _, _, _, cdecls, _ = coords
        return EnumDecl(IdentifierTerm(id, cid.start), body, decls)

    @pe.ExAction
    def create_with_id(attrs, coords, res_coord):
        id, decls = attrs
        _, cid, cdecls, _ = coords
        return EnumDecl(IdentifierTerm(id, cid.start), None, decls)

    @pe.ExAction
    def create_with_body(attrs, coords, res_coord):
        body, decls = attrs
        _, _, _, _, cdecls, _ = coords
        return EnumDecl(None, body, decls)

    @pe.ExAction
    def create_empty(attrs, coords, res_coord):
        decls, = attrs
        _, cdecls, _ = coords
        return EnumDecl(None, None, decls)

    def check(self, tags, consts):
        if self.identifier:
            if self.identifier.name in tags:
                raise SemanticError(self.identifier.name_coord, f"Повторный тег перечисления {self.identifier.name}")
            tags[self.identifier.name] = self
        if self.body:
            enum_counter = 0  # Локальный счётчик для значений констант
            for constant in self.body.constants:
                constant.check(tags, consts)
                consts[constant.name] = constant.value.evaluate(tags, consts) if constant.value else enum_counter
                enum_counter += 1
        for decl in self.declarators:
            decl.check(tags, consts)

    def size(self, tags, consts):
        return 4  # Фиксированный размер перечисления


@dataclass
class Program:
    declarations: list[Declaration]

    def check(self):
        tags = {}
        consts = {}
        for decl in self.declarations:
            decl.check(tags, consts)

        print("Константы перечислений:")
        for name, value in consts.items():
            print(f"{name} = {value}")

        print("\nРазмеры типов:\n")

        for decl in self.declarations:
            if isinstance(decl, (StructDecl, UnionDecl, EnumDecl)) and decl.identifier:
                size = decl.size(tags, consts)
                print(f"Размер типа {decl.identifier.name}: {size} байт")

        print("Семантических ошибок не найдено")



# Терминалы и нетерминалы
PLUS = pe.Terminal('+', '[+]', str)
MINUS = pe.Terminal('-', '[-]', str)
DIV = pe.Terminal('/', '[/]', str)
MUL = pe.Terminal('*', '[*]', str)
INTEGER = pe.Terminal('INTEGER', '[0-9]+', int, priority=7)
IDENTIFIER = pe.Terminal('IDENTIFIER', '[a-zA-Z][a-zA-Z0-9_]*', str)


def make_keyword(image):
    return pe.Terminal(image, image, lambda name: None, priority=10)


KW_STRUCT, KW_UNION, KW_ENUM, KW_INT, KW_CHAR, KW_DOUBLE, KW_SIZEOF = \
    map(make_keyword, 'struct union enum int char double sizeof'.split())

NProgram, NDeclaration, NStructDecl, NUnionDecl, NEnumDecl = \
    map(pe.NonTerminal, 'Program Declaration StructDecl UnionDecl EnumDecl'.split())

NOptDeclarators = pe.NonTerminal('OptDeclarators')
NStructUnionBody, NEnumBody, NTypeMemberDecl, NNestedDecl, NTypeSpecifier = \
    map(pe.NonTerminal, 'StructUnionBody EnumBody TypeMemberDecl NestedDecl TypeSpecifier'.split())

NCommaDeclarator, NDeclarator, NDirectDeclarator, NArrayIdentifier = \
    map(pe.NonTerminal, 'CommaDeclarator Declarator DirectDeclarator ArrayIdentifier'.split())

NPointer, NEnumConstant, NEnumExpr, NEnumTerm, NArrayBrackets = \
    map(pe.NonTerminal, 'Pointer EnumConstant EnumExpr EnumTerm ArrayBrackets'.split())

NMemberDecl = pe.NonTerminal('MemberDecl')

# Грамматика
NProgram |= lambda: Program([])
NProgram |= NDeclaration, lambda d: Program([d])
NProgram |= NProgram, NDeclaration, lambda p, d: Program(p.declarations + [d])

NDeclaration |= NStructDecl
NDeclaration |= NUnionDecl
NDeclaration |= NEnumDecl

NStructDecl |= (
    KW_STRUCT, IDENTIFIER, '{', NStructUnionBody, '}', NOptDeclarators, ';',
    StructDecl.create_with_id_and_body
)
NStructDecl |= (
    KW_STRUCT, IDENTIFIER, NOptDeclarators, ';',
    StructDecl.create_with_id
)
NStructDecl |= (
    KW_STRUCT, '{', NStructUnionBody, '}', NOptDeclarators, ';',
    StructDecl.create_with_body
)
NStructDecl |= (
    KW_STRUCT, NOptDeclarators, ';',
    StructDecl.create_empty
)

NUnionDecl |= (
    KW_UNION, IDENTIFIER, '{', NStructUnionBody, '}', NOptDeclarators, ';',
    UnionDecl.create_with_id_and_body
)
NUnionDecl |= (
    KW_UNION, IDENTIFIER, NOptDeclarators, ';',
    UnionDecl.create_with_id
)
NUnionDecl |= (
    KW_UNION, '{', NStructUnionBody, '}', NOptDeclarators, ';',
    UnionDecl.create_with_body
)
NUnionDecl |= (
    KW_UNION, NOptDeclarators, ';',
    UnionDecl.create_empty
)

NEnumDecl |= (
    KW_ENUM, IDENTIFIER, '{', NEnumBody, '}', NOptDeclarators, ';',
    EnumDecl.create_with_id_and_body
)
NEnumDecl |= (
    KW_ENUM, IDENTIFIER, NOptDeclarators, ';',
    EnumDecl.create_with_id
)
NEnumDecl |= (
    KW_ENUM, '{', NEnumBody, '}', NOptDeclarators, ';',
    EnumDecl.create_with_body
)
NEnumDecl |= (
    KW_ENUM, NOptDeclarators, ';',
    EnumDecl.create_empty
)

NOptDeclarators |= lambda: []
NOptDeclarators |= NDeclarator, lambda d: [d]
NOptDeclarators |= NDeclarator, ',', NOptDeclarators, lambda d, ds: [d] + ds

NStructUnionBody |= lambda: StructUnionBody([])
NStructUnionBody |= NMemberDecl, NStructUnionBody, lambda m, b: StructUnionBody([m] + b.members)

NEnumBody |= lambda: EnumBody([])
NEnumBody |= NEnumConstant, lambda c: EnumBody([c])
NEnumBody |= NEnumConstant, ',', NEnumBody, lambda c, b: EnumBody([c] + b.constants)

NMemberDecl |= NTypeMemberDecl
NMemberDecl |= NNestedDecl

NTypeMemberDecl |= NTypeSpecifier, NDeclarator, NCommaDeclarator, ';', TypeMemberDecl.create

NNestedDecl |= NStructDecl, lambda d: NestedDecl(d)
NNestedDecl |= NUnionDecl, lambda d: NestedDecl(d)
NNestedDecl |= NEnumDecl, lambda d: NestedDecl(d)

NCommaDeclarator |= lambda: []
NCommaDeclarator |= ',', NDeclarator, NCommaDeclarator, lambda d, ds: [d] + ds

NTypeSpecifier |= KW_INT, lambda: SympleType(Type.Int)
NTypeSpecifier |= KW_CHAR, lambda: SympleType(Type.Char)
NTypeSpecifier |= KW_DOUBLE, lambda: SympleType(Type.Double)
NTypeSpecifier |= KW_STRUCT, IDENTIFIER, NamedType.create_struct
NTypeSpecifier |= KW_UNION, IDENTIFIER, NamedType.create_union
NTypeSpecifier |= KW_ENUM, IDENTIFIER, NamedType.create_enum

NArrayIdentifier |= IDENTIFIER, NArrayBrackets, ArrayDeclarator.create

NArrayBrackets |= lambda: []
NArrayBrackets |= '[', NEnumExpr, ']', NArrayBrackets, lambda n, dims: [n] + dims

NDeclarator |= NPointer, NDirectDeclarator, Declarator.create

NDirectDeclarator |= IDENTIFIER, IdentifierDeclarator.create
NDirectDeclarator |= NArrayIdentifier

NPointer |= lambda: 0
NPointer |= '*', NPointer, lambda p: p + 1

NEnumConstant |= IDENTIFIER, EnumConstant.create
NEnumConstant |= IDENTIFIER, '=', NEnumExpr, EnumConstant.create_with_value

NEnumExpr |= NEnumTerm, EnumExpr.create
NEnumExpr |= NEnumTerm, PLUS, NEnumExpr, EnumExpr.create_binop
NEnumExpr |= NEnumTerm, MINUS, NEnumExpr, EnumExpr.create_binop
NEnumExpr |= NEnumTerm, MUL, NEnumExpr, EnumExpr.create_binop
NEnumExpr |= NEnumTerm, DIV, NEnumExpr, EnumExpr.create_binop

NEnumTerm |= INTEGER, IntegerConstantTerm
NEnumTerm |= IDENTIFIER, IdentifierTerm.create
NEnumTerm |= KW_SIZEOF, '(', NTypeSpecifier, ')', SizeofTerm.create
NEnumTerm |= '(', NEnumExpr, ')', lambda expr: expr

# Парсер
p = pe.Parser(NProgram)
p.add_skipped_domain('\\s')

# Обработка входных файлов
for filename in sys.argv[1:]:
    try:
        with open(filename) as f:
            tree = p.parse(f.read())
            consts = tree.check()
    except pe.Error as e:
        print(f"Ошибка {e.pos}: {e.message}")