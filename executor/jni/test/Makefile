OBJ = executor
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic

INC = -I../include

$(OBJ): $(OBJ).c ../utils.c ../optee.c ../opteenet.c ../opteelibteec.c
	$(CC) $(INC) -o $@ $^ -ldl

libteec.so: libteecfake.c
	$(CC) $(INC) -o $@ -shared $<

clean:
	$(RM) $(OBJ) *.so
