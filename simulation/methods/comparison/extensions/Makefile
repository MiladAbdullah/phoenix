PYTHON_EXTENSION_SUFFIX := $(shell python3-config --extension-suffix)
PYTHON_CFLAGS := $(shell python3-config --cflags|sed 's/[[:space:]]\+/\n/g'|sort -u|grep -E -v '^(-I|-mtune|-O)')
PYTHON_LDFLAGS := $(shell python3-config --ldflags)

PYTHON_INCLUDES := $(shell python3-config --includes)
NUMPY_INCLUDE := $(shell python3 -c 'import numpy; print(numpy.get_include())')

CC ?= gcc
CFLAGS = -O2 -ftree-vectorize -ffast-math -march=native -DNDEBUG -shared -fPIC $(PYTHON_INCLUDES) -I$(NUMPY_INCLUDE) -I../../include $(PYTHON_CFLAGS)
LDFLAGS = $(PYTHON_LDFLAGS)

SOURCE = fusedboot.c
MODULE = fusedboot.so
TARGET = $(MODULE)

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGET)

