

#ifndef _STRING_H_
#define _STRING_H_

#include <stdlib.h>

void *memcpy(void *, const void *, size_t);
void *memmove(void *, const void *, size_t);
int memcmp(const void *, const void *, size_t);
void *memchr(const void *, int, size_t);
void *memset(void *, int, size_t);

char *strcpy(char *, const char *);
char *strncpy(char *, const char *, size_t);
char *strcat(char *, const char *);
char *strncat(char *, const char *, size_t);


int strcmp(const char *, const char *);
int strcoll(char *, char *);
int strncmp(const char *, const char *, size_t);

size_t strxfrm(char *, const char *, size_t);

char  *strchr(const char *, int);
size_t strcspn(const char *, const char *);
char *strpbrk(const char *, const char *);
char *strrchr(const char *, int);
size_t strspn(const char *, const char *);
char *strstr(const char *, const char *);
char *strtok(char *, const char *);
size_t strlen(const char *);

#endif