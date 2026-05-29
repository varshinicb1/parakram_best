# Parakram VM Host Test Harness
# Compiles the real firmware VM with mock ESP-IDF dependencies on x86 Linux.

CC      = gcc
CFLAGS  = -Wall -Wextra -g -O0 -DHOST_TEST \
          -I. -I../main/include -lm
LDFLAGS = -lm

SRCS    = vm_test.c mock_subsystems.c ../main/runtime/vm.c
TARGET  = vm_test

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(SRCS) esp_mock.h
	$(CC) $(CFLAGS) -o $@ $(SRCS) $(LDFLAGS)

test: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)
