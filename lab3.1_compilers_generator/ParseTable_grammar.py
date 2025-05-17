# Auto-generated parse axiom
axiom = 'grammar'

# Auto-generated parse terms
terminals = ['tokens', 'start', 'is', ',', '.', 'id']

# Auto-generated parse table
parse_table = {
    ('grammar', '$'): [],
    ('grammar', 'tokens'): ['definition', 'grammar'],
    ('grammar', 'start'): ['definition', 'grammar'],
    ('grammar', 'id'): ['definition', 'grammar'],
    ('definition', 'start'): ['axiom'],
    ('definition', 'id'): ['rules'],
    ('definition', 'tokens'): ['tokens-decl'],
    ('tokens-decl', 'tokens'): ['tokens', 'id', 'TI', '.'],
    ('TI', '.'): [],
    ('TI', ','): [',', 'id', 'TI'],
    ('rules', 'id'): ['rule', '.'],
    ('rule', 'id'): ['id', 'is', 'SP', 'RP'],
    ('SP', ','): [],
    ('SP', '.'): [],
    ('SP', 'id'): ['id', 'SP'],
    ('RP', '.'): [],
    ('RP', ','): [',', 'rule'],
    ('axiom', 'start'): ['start', 'id', '.'],
}
