#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define RES_FILE "reservations.txt"
#define USR_FILE "users.txt"
#define HASH_SIZE 101

typedef struct User {
    char name[100];
    char phone[50];
    char email[100];
    char pass[100];
    struct User *next;
} User;

typedef struct Reservation {
    char user[100];
    int id;
    char tables[100];
    char guests[10];
    char date[20];
    char slot[50];
    int status;
    struct Reservation *next;
} Reservation;

User *user_head = NULL;
Reservation *res_head = NULL;

// Hash tables
User *user_hash[HASH_SIZE];
Reservation *res_hash[HASH_SIZE];

unsigned int hash_str(char *str) {
    unsigned int hash = 0;
    while (*str)
        hash = (hash * 31) + *str++;
    return hash % HASH_SIZE;
}

unsigned int hash_int(int id) {
    return id % HASH_SIZE;
}

void insert_user_hash(User *u) {
    int h = hash_str(u->email);
    u->next = user_hash[h];
    user_hash[h] = u;
}

void insert_res_hash(Reservation *r) {
    int h = hash_int(r->id);
    r->next = res_hash[h];
    res_hash[h] = r;
}

void load_users() {
    FILE *fp = fopen(USR_FILE, "r");
    if (!fp) return;

    char line[256];

    while (fgets(line, sizeof(line), fp)) {
        User *u = malloc(sizeof(User));

        sscanf(line, "%[^,],%[^,],%[^,],%s",
               u->name, u->phone, u->email, u->pass);

        u->next = user_head;
        user_head = u;
        insert_user_hash(u);
    }
    fclose(fp);
}

void load_reservations() {
    FILE *fp = fopen(RES_FILE, "r");
    if (!fp) return;

    char line[512];

    while (fgets(line, sizeof(line), fp)) {
        Reservation *r = malloc(sizeof(Reservation));

        sscanf(line, "%[^,],%d,%[^,],%[^,],%[^,],%[^,],%d",
               r->user, &r->id, r->tables,
               r->guests, r->date, r->slot, &r->status);

        r->next = res_head;
        res_head = r;
        insert_res_hash(r);
    }
    fclose(fp);
}

void save_users() {
    FILE *fp = fopen(USR_FILE, "w");

    User *curr = user_head;
    while (curr) {
        fprintf(fp, "%s,%s,%s,%s\n",
                curr->name, curr->phone,
                curr->email, curr->pass);
        curr = curr->next;
    }

    fclose(fp);
}

void save_reservations() {
    FILE *fp = fopen(RES_FILE, "w");

    Reservation *curr = res_head;
    while (curr) {
        fprintf(fp, "%s,%d,%s,%s,%s,%s,%d\n",
                curr->user, curr->id, curr->tables,
                curr->guests, curr->date,
                curr->slot, curr->status);
        curr = curr->next;
    }

    fclose(fp);
}

void auth_login(char email[], char pass[]) {
    int h = hash_str(email);
    User *curr = user_hash[h];

    while (curr) {
        if (strcmp(curr->email, email) == 0 &&
            strcmp(curr->pass, pass) == 0) {
            printf("%s\n", curr->name);
            return;
        }
        curr = curr->next;
    }

    printf("FAILURE\n");
}

void auth_signup(char name[], char phone[], char email[], char pass[]) {
    int h = hash_str(email);
    User *curr = user_hash[h];

    while (curr) {
        if (strcmp(curr->email, email) == 0) {
            printf("EXISTS\n");
            return;
        }
        curr = curr->next;
    }

    User *u = malloc(sizeof(User));
    strcpy(u->name, name);
    strcpy(u->phone, phone);
    strcpy(u->email, email);
    strcpy(u->pass, pass);

    u->next = user_head;
    user_head = u;
    insert_user_hash(u);

    save_users();
    printf("SUCCESS\n");
}

int is_table_booked(int tid, char date[], char slot[]) {
    Reservation *curr = res_head;

    while (curr) {
        if (curr->status == 0 &&
            strcmp(curr->date, date) == 0 &&
            strcmp(curr->slot, slot) == 0) {

            char temp[100];
            strcpy(temp, curr->tables);

            char *token = strtok(temp, "|");
            while (token) {
                if (atoi(token) == tid)
                    return 1;
                token = strtok(NULL, "|");
            }
        }
        curr = curr->next;
    }

    return 0;
}

void find_tables(int guests, char date[], char slot[]) {

    if (guests <= 10) {
        for (int i = 1; i <= 10; i++) {
            if (!is_table_booked(i, date, slot)) {
                printf("%d\n", i);
                return;
            }
        }
    }

    printf("NONE\n");
}

void reserve(char user[], char tables[], char guests[],
             char date[], char slot[]) {

    Reservation *r = malloc(sizeof(Reservation));

    strcpy(r->user, user);
    r->id = rand() % 9000 + 1000;
    strcpy(r->tables, tables);
    strcpy(r->guests, guests);
    strcpy(r->date, date);
    strcpy(r->slot, slot);
    r->status = 0;

    r->next = res_head;
    res_head = r;
    insert_res_hash(r);

    save_reservations();

    printf("%d\n", r->id);
}


void cancel(int id) {
    int h = hash_int(id);
    Reservation *curr = res_hash[h];

    while (curr) {
        if (curr->id == id) {
            curr->status = 1;
            save_reservations();
            printf("SUCCESS\n");
            return;
        }
        curr = curr->next;
    }
}

void mark_paid(int id) {
    int h = hash_int(id);
    Reservation *curr = res_hash[h];

    while (curr) {
        if (curr->id == id) {
            curr->status = 2;
            save_reservations();
            printf("SUCCESS\n");
            return;
        }
        curr = curr->next;
    }
}

int main(int argc, char *argv[]) {
    srand(time(0));

    load_users();
    load_reservations();

    if (argc < 2) return 1;

    if (strcmp(argv[1], "login") == 0)
        auth_login(argv[2], argv[3]);

    else if (strcmp(argv[1], "signup") == 0)
        auth_signup(argv[2], argv[3], argv[4], argv[5]);

    else if (strcmp(argv[1], "find") == 0)
        find_tables(atoi(argv[2]), argv[3], argv[4]);

    else if (strcmp(argv[1], "reserve") == 0)
        reserve(argv[2], argv[3], argv[4], argv[5], argv[6]);

    else if (strcmp(argv[1], "cancel") == 0)
        cancel(atoi(argv[2]));

    else if (strcmp(argv[1], "pay") == 0)
        mark_paid(atoi(argv[2]));

    return 0;
}