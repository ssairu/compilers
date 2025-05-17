%option noyywrap bison-bridge bison-locations

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAG_IDENT 1
#define TAG_STRING 2
#define TAG_END 0

char *tag_names[] = {
    "END_OF_PROGRAM", "IDENT", "STRING"
};

struct Position {
    int line, pos, index;
};

void print_pos(struct Position *p) {
    printf("(%d,%d)", p->line, p->pos);
}

struct Fragment {
    struct Position starting, following;
};

typedef struct Fragment YYLTYPE;

void print_frag(struct Fragment *f) {
    print_pos(&(f->starting));
    printf("-");
    print_pos(&(f->following));
}

union Token {
    int ident_id;
    char *string;
};

typedef union Token YYSTYPE;

struct IdentNode {
    char *name;
    int id;
    struct IdentNode *next;
};
struct IdentNode *ident_list = NULL;
int ident_count = 0;

int add_ident(char *name) {
    struct IdentNode *node = ident_list;
    while (node) {
        if (strcmp(node->name, name) == 0) {
            return node->id;
        }
        node = node->next;
    }
    node = (struct IdentNode *)malloc(sizeof(struct IdentNode));
    node->name = strdup(name);
    node->id = ident_count++;
    node->next = ident_list;
    ident_list = node;
    return node->id;
}

const char* get_ident_name(int id) {
    struct IdentNode *node = ident_list;
    while (node != NULL) {
        if (node->id == id) {
            return node->name;
        }
        node = node->next;
    }
    return "(unknown)";
}

struct Error {
    struct Position pos;
    char *message;
    struct Error *next;
};
struct Error *error_list = NULL;
struct Error *error_list_tail = NULL;

void add_error(struct Position *pos, char *msg) {
    struct Error *err = (struct Error *)malloc(sizeof(struct Error));
    err->pos = *pos;
    err->message = strdup(msg);
    err->next = NULL;

    if (error_list == NULL) {
        error_list = err;
        error_list_tail = err;
    } else {
        error_list_tail->next = err;
        error_list_tail = err;
    }
}

void print_errors() {
    struct Error *err = error_list;
    while (err) {
        printf("Error at (%d,%d): %s\n", err->pos.line, err->pos.pos, err->message);
        err = err->next;
    }
}

int continued;
struct Position cur;

#define YY_USER_ACTION { \
    int i; \
    if (!continued) \
        yylloc->starting = cur; \
    continued = 0; \
    for (i = 0; i < yyleng; i++) { \
        if (yytext[i] == '\n') { \
            cur.line++; \
            cur.pos = 1; \
        } else { \
            cur.pos++; \
        } \
        cur.index++; \
    } \
    yylloc->following = cur; \
}

void init_scanner(FILE *input) {
    continued = 0;
    cur.line = 1;
    cur.pos = 1;
    cur.index = 0;
    yyin = input;
}

%}


LETTER [a-zA-Z]
DIGIT [0-9]
IDENT {LETTER}({LETTER}|{DIGIT})*

%x STRING STRING_NUM SUPER_STRING

%%

<INITIAL>[ \t\n]+

{IDENT}           {
    yylval->ident_id = add_ident(yytext);
    return TAG_IDENT;
}

<INITIAL>"'"               {
    BEGIN(STRING); continued = 1;
    yylval->string = strdup("");
}

<SUPER_STRING>"'"       {
	BEGIN(STRING); continued = 1;
}

<INITIAL>"#"                {
    BEGIN(STRING_NUM); continued = 1;
    yylval->string = strdup("");
}

<SUPER_STRING>[#]       {
	BEGIN(STRING_NUM); continued = 1;
}

<STRING>"'#"       {
    BEGIN(STRING_NUM); continued = 1;
}

<STRING>"''"      {
    char *new_str = (char *)malloc(strlen(yylval->string) + 2);
    strcpy(new_str, yylval->string);
    strcat(new_str, "'");
    free(yylval->string);
    yylval->string = new_str;
    continued = 1;
}

<STRING>"'"/[^#]       {
    BEGIN(0);
    return TAG_STRING;
}

<STRING>[^'\n#]*  {
    char *new_str = (char *)malloc(strlen(yylval->string) + strlen(yytext) + 1);
    strcpy(new_str, yylval->string);
    strcat(new_str, yytext);
    free(yylval->string);
    yylval->string = new_str;
    continued = 1;
}

<STRING>\n        {
    add_error(&cur, "newline in string literal");
    continued = 1;
}

<STRING>.         {
    add_error(&cur, "unexpected character in string");
    continued = 1;
}

<STRING_NUM>{DIGIT}{1,3}/['#] {
    char *endptr;
    int code = strtol(yytext, &endptr, 10);
    if (*endptr != '\0' || code < 0 || code > 255) {
        add_error(&cur, "invalid character code");
    } else {
        char *new_str = (char *)malloc(strlen(yylval->string) + 2);
        strcpy(new_str, yylval->string);
        new_str[strlen(new_str)] = (char)code;
        new_str[strlen(new_str) + 1] = '\0';
        free(yylval->string);
        yylval->string = new_str;
    }
    BEGIN(SUPER_STRING);
    continued = 1;
}

<STRING_NUM>{DIGIT}{1,3}/[^#'] {
    char *endptr;
    int code = strtol(yytext, &endptr, 10);
    if (*endptr != '\0' || code < 0 || code > 255) {
        add_error(&cur, "invalid character code");
    } else {
        char *new_str = (char *)malloc(strlen(yylval->string) + 2);
        strcpy(new_str, yylval->string);
        new_str[strlen(new_str)] = (char)code;
        new_str[strlen(new_str) + 1] = '\0';
        free(yylval->string);
        yylval->string = new_str;
    }
    BEGIN(0);
    return TAG_STRING;
}

<STRING_NUM>[^0-9] {
    add_error(&cur, "expected number after '#'");
    BEGIN(STRING);
    continued = 1;
}
<STRING_NUM>\\n    {
    add_error(&cur, "newline in string literal");
    free(yylval->string);
    yylval->string = strdup("");
    BEGIN(0);
    return TAG_STRING;
}

.                 { add_error(&cur, "unexpected character"); }

%%

int main(int argc, char *argv[]) {
    FILE *input = stdin;
    if (argc > 1) {
        input = fopen(argv[1], "r");
        if (!input) {
            perror("Cannot open input file");
            return 1;
        }
    }

    int tag;
    YYSTYPE value;
    YYLTYPE coords;
    init_scanner(input);

    do {
        tag = yylex(&value, &coords);
        if (tag != 0) {
            printf("%s ", tag_names[tag]);
            print_frag(&coords);
            if (tag == TAG_IDENT) {
                printf(": %s", get_ident_name(value.ident_id));
            } else if (tag == TAG_STRING) {
                printf(": %s", value.string);
                free(value.string);
            } else {
                printf(":");
            }
            printf("\n");
        }
    } while (tag != 0);

    if (input != stdin) {
        fclose(input);
    }

    print_errors();

    while (ident_list) {
        struct IdentNode *temp = ident_list;
        ident_list = ident_list->next;
        free(temp->name);
        free(temp);
    }
    while (error_list) {
        struct Error *temp = error_list;
        error_list = error_list->next;
        free(temp->message);
        free(temp);
    }

    return 0;
}
