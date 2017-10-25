#include <stdio.h>
#include <string.h>

int main() {
    char buf[0x100];
    char result[0x80];
    char path;
    int choice;

    printf("Choose a command:\n");
    scanf("%d", &choice);
    switch(choice) {
        case 1:
            printf("Enter log file\n");
            read(0, buf, 0x100);
            path = malloc(100);
            sprintf(path, "/tmp/%s_%d", buf, strlen(buf));
            sprintf(result, "SUCCESS: %s\n", "Log file created.");
            break;
        default:
            sprintf(result, "Sorry, choice %d is not accepted\n", choice);
    }

    write(1, result, strlen(result));

    return 0;
}
