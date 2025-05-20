%{
#include "lexer.h"

typedef struct {
    int indent_level;
    FILE *output;
} Formatter;

void format_indent(Formatter *f) {
    for (int i = 0; i < f->indent_level; i++) {
        fprintf(f->output, "  ");
    }
}

void print_formatted(Formatter *f, const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    format_indent(f);
    vfprintf(f->output, fmt, args);
    va_end(args);
}
%}

%define api.pure
%locations
%lex-param {yyscan_t scanner}
%parse-param {yyscan_t scanner}
%parse-param {Formatter *formatter}

%union {
    char *string;
    int number;
}

%token TYPE FUN WHERE WEND ARROW PIPE COLON DOT COMMA
%token LEFT_PAREN RIGHT_PAREN LEFT_BRACKET RIGHT_BRACKET
%token <string> TYPE_NAME IDENTIFIER
%token <number> NUMBER

%type <string> type_declaration type_constructors type_constructor
%type <string> function_declaration pattern expression where_clause
%type <string> function_definition function_body

%{
int yylex(YYSTYPE *yylval_param, YYLTYPE *yylloc_param, yyscan_t scanner);
void yyerror(YYLTYPE *loc, yyscan_t scanner, Formatter *formatter, const char *message);
%}

%%

program:
    declaration_list
    ;

declaration_list:
    declaration
    | declaration_list declaration
    ;

declaration:
    type_declaration { fprintf(formatter->output, "%s\n\n", $1); free($1); }
    | function_declaration { fprintf(formatter->output, "%s\n\n", $1); free($1); }
    ;

type_declaration:
    TYPE TYPE_NAME COLON type_constructors DOT
    {
        $$ = malloc(256);
        snprintf($$, 256, "type %s: %s.", $2, $4);
        free($2); free($4);
    }
    ;

type_constructors:
    type_constructor
    {
        $$ = $1;
    }
    | type_constructors PIPE type_constructor
    {
        $$ = malloc(strlen($1) + strlen($3) + 4);
        sprintf($$, "%s | %s", $1, $3);
        free($1); free($3);
    }
    ;

type_constructor:
    TYPE_NAME
    {
        $$ = strdup($1);
    }
    | TYPE_NAME type_fields
    {
        $$ = malloc(strlen($1) + strlen($2) + 1);
        sprintf($$, "%s%s", $1, $2);
        free($1); free($2);
    }
    ;

type_fields:
    TYPE_NAME
    {
        $$ = malloc(strlen($1) + 2);
        sprintf($$, " %s", $1);
        free($1);
    }
    | type_fields TYPE_NAME
    {
        $$ = malloc(strlen($1) + strlen($2) + 2);
        sprintf($$, "%s %s", $1, $2);
        free($1); free($2);
    }
    ;

function_declaration:
    FUN LEFT_PAREN pattern RIGHT_PAREN ARROW TYPE_NAME function_body
    {
        $$ = malloc(256);
        snprintf($$, 256, "fun (%s) -> %s%s", $3, $6, $7);
        free($3); free($6); free($7);
    }
    ;

function_body:
    COLON function_definition
    {
        formatter->indent_level++;
        $$ = malloc(strlen($2) + 2);
        sprintf($$, ":\n%s", $2);
        formatter->indent_level--;
        free($2);
    }
    ;

function_definition:
    pattern ARROW expression where_clause
    {
        char *temp = malloc(256);
        snprintf(temp, 256, "  (%s) -> %s%s", $1, $3, $4);
        $$ = temp;
        free($1); free($3); free($4);
    }
    | function_definition PIPE function_definition
    {
        $$ = malloc(strlen($1) + strlen($3) + 2);
        sprintf($$, "%s\n%s", $1, $3);
        free($1); free($3);
    }
    ;

where_clause:
    /* empty */ { $$ = strdup(""); }
    | WHERE function_declaration_list WEND
    {
        formatter->indent_level++;
        $$ = malloc(strlen($2) + 8);
        sprintf($$, "\n  where%s\n  wend", $2);
        formatter->indent_level--;
        free($2);
    }
    ;

function_declaration_list:
    function_declaration
    {
        $$ = $1;
    }
    | function_declaration_list function_declaration
    {
        $$ = malloc(strlen($1) + strlen($2) + 2);
        sprintf($$, "%s\n%s", $1, $2);
        free($1); free($2);
    }
    ;

pattern:
    LEFT_BRACKET expression RIGHT_BRACKET
    {
        $$ = malloc(strlen($2) + 3);
        sprintf($$, "[%s]", $2);
        free($2);
    }
    | IDENTIFIER { $$ = strdup($1); }
    | NUMBER
    {
        $$ = malloc(16);
        sprintf($$, "%d", $1);
    }
    ;

expression:
    IDENTIFIER { $$ = strdup($1); }
    | NUMBER
    {
        $$ = malloc(16);
        sprintf($$, "%d", $1);
    }
    | LEFT_PAREN expression RIGHT_PAREN
    {
        $$ = malloc(strlen($2) + 3);
        sprintf($$, "(%s)", $2);
        free($2);
    }
    | IDENTIFIER LEFT_PAREN expression_list RIGHT_PAREN
    {
        $$ = malloc(strlen($1) + strlen($3) + 3);
        sprintf($$, "%s(%s)", $1, $3);
        free($1); free($3);
    }
    ;

expression_list:
    expression
    {
        $$ = $1;
    }
    | expression_list COMMA expression
    {
        $$ = malloc(strlen($1) + strlen($3) + 3);
        sprintf($$, "%s, %s", $1, $3);
        free($1); free($3);
    }
    ;

%%

void yyerror(YYLTYPE *loc, yyscan_t scanner, Formatter *formatter, const char *message) {
    fprintf(stderr, "Error at line %d, column %d: %s\n", 
            loc->first_line, loc->first_column, message);
}

int main(int argc, char *argv[]) {
    FILE *input = stdin;
    yyscan_t scanner;
    struct Extra extra;
    Formatter formatter = {0, stdout};

    if (argc > 1) {
        input = fopen(argv[1], "r");
        if (!input) {
            perror("Error opening input file");
            return 1;
        }
    }

    init_scanner(input, &scanner, &extra);
    yyparse(scanner, &formatter);
    destroy_scanner(scanner);

    if (input != stdin) {
        fclose(input);
    }

    return 0;
}