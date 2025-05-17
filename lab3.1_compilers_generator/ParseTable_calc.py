# Auto-generated parse axiom
axiom = 'E'

# Auto-generated parse terms
terminals = ['plus sign', 'star', 'n', 'left paren', 'right paren']

# Auto-generated parse table
parse_table = {
    ('E', 'n'): ['T', 'E 1'],
    ('E', 'left paren'): ['T', 'E 1'],
    ('E 1', '$'): [],
    ('E 1', 'right paren'): [],
    ('E 1', 'plus sign'): ['plus sign', 'T', 'E 1'],
    ('T', 'n'): ['F', 'T 1'],
    ('T', 'left paren'): ['F', 'T 1'],
    ('T 1', 'plus sign'): [],
    ('T 1', '$'): [],
    ('T 1', 'right paren'): [],
    ('T 1', 'star'): ['star', 'F', 'T 1'],
    ('F', 'left paren'): ['left paren', 'E', 'right paren'],
    ('F', 'n'): ['n'],
}
