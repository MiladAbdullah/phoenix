#include "common.h"
#include "splitmix64.h"
#include "xoshiro256pv.h"

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define NPY_NO_DEPRECATED_API NPY_1_19_API_VERSION
#include <numpy/arrayobject.h>

#include <stdint.h>
#include <stdlib.h>


// Auxiliary RNG state.

static splitmix64_t splitmix64;

// Main RNG state.

static xoshiro256pv_t xoshiro256pv;

// Macros to simplify switching between different main RNGs.

#define random_init_using(next, next_arg) xoshiro256pv_init_using(&xoshiro256pv, (void *) (next), (next_arg))
#define random_next_bulk(values) __xoshiro256pv_next_bulk(&xoshiro256pv, XOSHIRO256PV_WIDTH, (values))
#define RANDOM_WIDTH XOSHIRO256PV_WIDTH

//

static void xoshiro256pv_init_using(
    xoshiro256pv_t * const restrict state, uint64_t (*next)(void * const restrict), void * const restrict next_arg
) {
    uint64_t xoshiro256pv_seed[4][XOSHIRO256PV_WIDTH];
    for (unsigned si = 0; si < 4; si++) {
        for (unsigned ui = 0; ui < XOSHIRO256PV_WIDTH; ui++) {
            xoshiro256pv_seed[si][ui] = next(next_arg);
        }
    }

    __xoshiro256pv_init(&xoshiro256pv, xoshiro256pv_seed);
}


static void init_random(const uint64_t seed) {
    // Seed the splitmix64 RNG and use it to seed the main RNG.
    __splitmix64_init(&splitmix64, seed);
    random_init_using(__splitmix64_next, &splitmix64);
}


static PyObject* python_init_random(PyObject* self, PyObject* args) {
    long int random_seed;

    if (!PyArg_ParseTuple(args, "l", &random_seed)) {
        return NULL;
    }

    init_random(random_seed);
    Py_RETURN_NONE;
}

//

/**
 * Computes the bootstrap mean of a given array of double values
 * using a given number of samples.
 */
static double bootstrap_mean_1d_float64_simple(
    const npy_intp count, const npy_intp length, double const values[length]
) {
    const unsigned count_tail = count % RANDOM_WIDTH;
    const unsigned count_head = count - count_tail;

    double sum = 0.0;
    uint64_t randoms[RANDOM_WIDTH];

    // Handle head elements (if any).
    for (unsigned si = 0; si < count_head; si += RANDOM_WIDTH) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < RANDOM_WIDTH; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    // Handle tail elements (if any).
    if (count_tail != 0) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < count_tail; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    return sum / count;
}

//

/**
 * Computes the bootstrap mean of a given array of signed integer
 * values using a given number of samples.
 */
static double bootstrap_mean_1d_int64_simple(
    const npy_intp count, const npy_intp length, int64_t const values[length]
) {
    const unsigned count_tail = count % RANDOM_WIDTH;
    const unsigned count_head = count - count_tail;

    int_fast64_t sum = 0;
    uint64_t randoms[RANDOM_WIDTH];

    // Handle head elements (if any).
    for (unsigned si = 0; si < count_head; si += RANDOM_WIDTH) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < RANDOM_WIDTH; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    // Handle tail elements (if any).
    if (count_tail != 0) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < count_tail; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    return sum / (double) count;
}

//

/**
 * Computes the bootstrap mean of a given array of unsigned integer
 * values using a given number of samples.
 */
static double bootstrap_mean_1d_uint64_simple(
    const npy_intp count, const npy_intp length, uint64_t const values[length]
) {
    const unsigned count_tail = count % RANDOM_WIDTH;
    const unsigned count_head = count - count_tail;

    uint_fast64_t sum = 0;
    uint64_t randoms[RANDOM_WIDTH];

    // Handle head elements (if any).
    for (unsigned si = 0; si < count_head; si += RANDOM_WIDTH) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < RANDOM_WIDTH; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    // Handle tail elements (if any).
    if (count_tail != 0) {
        random_next_bulk(randoms);

        for (unsigned ri = 0; ri < count_tail; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], count);
            sum += values[index];
        }
    }

    return sum / (double) count;
}

//

typedef double (* bootstrap_mean_1d_fn_t)(const npy_intp count, const npy_intp length, void * arg);

/**
 * Computes the bootstrap mean of the given arrays using a given number of samples.
 * Uses a type-specific function to compute the bootstrap mean of the 1-D arrays.
 */
static double bootstrap_mean_2d(
    const unsigned mean_count, const unsigned array_count,
    PyArrayObject * const restrict arrays[array_count],
    const npy_intp sample_counts[array_count],
    bootstrap_mean_1d_fn_t bootstrap_mean_1d_fn
) {
    double sum = 0.0;

    for (unsigned mi = 0; mi < mean_count; mi += RANDOM_WIDTH) {
        uint64_t randoms[RANDOM_WIDTH];
        random_next_bulk(randoms);

        // Handle tail here, this should not be performance critical.
        for (unsigned ri = 0; ri < RANDOM_WIDTH && (mi + ri) < mean_count; ri++) {
            const unsigned index = __random_uint64_mod_float64(randoms[ri], array_count);
            sum += bootstrap_mean_1d_fn(
                sample_counts[index], PyArray_SIZE(arrays[index]), PyArray_DATA(arrays[index])
            );
        }
    }

    return sum / mean_count;
}

//

static PyObject* python_hierarchical_bootstrap_mean_2d(PyObject * const self, PyObject * const args) {
    PyObject * arrays;
    long run_count;
    long sample_count;
    long replica_count;

    if (!PyArg_ParseTuple(args, "Olll", &arrays, &run_count, &sample_count, &replica_count)) {
        return NULL;
    }

    if (!PyList_Check(arrays)) {
        PyErr_SetString(PyExc_TypeError, "`arrays` parameter must be of type `list`");
        return NULL;
    }

    PyArrayObject * result = NULL;

    //
    // We use two auxiliary arrays. One to hold the references to array objects
    // and one to hold the number of samples to take from each array (which does
    // not have to be equal to the number of array elements).
    //

    const Py_ssize_t arrays_count = PyList_Size(arrays);

    PyArrayObject ** const array_objects = calloc(arrays_count, sizeof(PyArrayObject *));
    npy_intp * const sample_counts = malloc(arrays_count * sizeof(npy_intp));

    if (array_objects == NULL || sample_counts == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory for auxiliary data");
        goto exit_free_arrays;
    }

    //
    // Check array type and collect array object references. For arrays of the right type
    // that are C contiguous, we just increment a reference count on the borrowed reference
    // (so that we can decrement it later). For other arrays, we create a new array with a
    // new reference that will be released later.
    //
    // For each array, we also determine the sample count, which defaults to array length.
    //

    int target_type = NPY_NOTYPE;
    bootstrap_mean_1d_fn_t bootstrap_mean_1d_fn = NULL;

    for (Py_ssize_t ai = 0; ai < arrays_count; ai++) {
        // PyList_GetItem returns a borrowed reference (no need to release it).
        PyObject * const object = PyList_GetItem(arrays, ai);
        if (!PyArray_Check(object)) {
            PyErr_Format(PyExc_TypeError, "Item %zd of the input list is not a `numpy.ndarray`", ai);
            goto exit_free_refs;
        }

        // Check the number of dimensions.
        const int ndim = PyArray_NDIM((PyArrayObject *) object);
        if (ndim != 1) {
            PyErr_Format(PyExc_ValueError, "Array %zd of the input list has %d dimensions (expecting 1)", ai, ndim);
            goto exit_free_refs;
        }

        // Check/upgrade array type and determine type-specific bootstrap function.
        int array_type = PyArray_TYPE((PyArrayObject *) object);
        if (PyTypeNum_ISFLOAT(array_type)) {
            bootstrap_mean_1d_fn = (bootstrap_mean_1d_fn_t) bootstrap_mean_1d_float64_simple;
            array_type = NPY_FLOAT64;
        } else if (PyTypeNum_ISSIGNED(array_type)) {
            bootstrap_mean_1d_fn = (bootstrap_mean_1d_fn_t) bootstrap_mean_1d_int64_simple;
            array_type = NPY_INT64;
        } else if (PyTypeNum_ISUNSIGNED(array_type)) {
            bootstrap_mean_1d_fn = (bootstrap_mean_1d_fn_t) bootstrap_mean_1d_uint64_simple;
            array_type = NPY_UINT64;
        } else {
            PyErr_Format(PyExc_TypeError, "Array %zd of the input list has invalid element type (expecting signed/unsigned integer, or float)", ai);
            goto exit_free_refs;
        }

        // Check for mismatching array types (or set the target type).
        // We expect all arrays to be of the same general type, i.e.,
        // floats, unsigned ints, or signed ints.
        if (array_type != target_type) {
            if (target_type != NPY_NOTYPE) {
                PyErr_Format(PyExc_TypeError, "Array %zd of the input list has a mismatching type (expecting similar types)", ai);
                goto exit_free_refs;
            } else {
                target_type = array_type;
            }
        }

        // Get a reference to a well-behaved (contiguous and aligned) array.
        // This may convert the input arrays to arrays using a wider type.
        // PyArray_FROM_OTF return a new reference that MUST be released.
        PyArrayObject * array_object = (PyArrayObject *) PyArray_FROM_OTF(object, target_type, NPY_ARRAY_IN_ARRAY);
        if (array_object == NULL) {
            PyErr_Format(PyExc_ValueError, "Failed getting a well-behaved `numpy.ndarray` for item %zd of the input list", ai);
            goto exit_free_refs;
        }

        array_objects[ai] = array_object;

        // Use array size if the `sample_count` is not well defined.
        sample_counts[ai] = (sample_count > 0) ? (npy_intp) sample_count : PyArray_SIZE(array_object);
    }


    //
    // Allocate the result object.
    //
    const npy_intp dims[] = { replica_count };
    result = (PyArrayObject *) PyArray_SimpleNew(1, dims, NPY_DOUBLE);
    if (result == NULL) {
        PyErr_Format(PyExc_MemoryError, "Failed to allocate memory for the output array of %ld replicas", replica_count);
        goto exit_free_refs;
    }

    //
    // Compute the hierarchical bootstrap mean replicas.
    // Use the bootstrap function corresponding to the target type.
    //
    double * const replicas = PyArray_DATA(result);
    for (long ri = 0; ri < replica_count; ri++) {
        replicas[ri] = bootstrap_mean_2d(
            run_count, arrays_count, array_objects, sample_counts,
            bootstrap_mean_1d_fn
        );
    }

exit_free_refs:
    for (Py_ssize_t i = 0; i < arrays_count; i++) {
        // Some of the references may be NULL.
        Py_XDECREF(array_objects[i]);
    }

exit_free_arrays:
    // Free auxiliary arrays.
    free(sample_counts);
    free(array_objects);
    return (PyObject *) result;
}


static PyMethodDef module_methods[] = {
    {
        "hierarchical_bootstrap_mean",
        python_hierarchical_bootstrap_mean_2d,
        METH_VARARGS,
        "Calculates a hierarchical bootstrap mean for a list of Numpy arrays."
    },

    {
        "init_random",
        python_init_random,
        METH_VARARGS,
        "Initializes the internal random number generator using the given seed."
    },

    // Sentinel
    {
        NULL, NULL, 0, NULL
    }
};


static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "bench_app_bench.utils.cmath.fusedboot",
    NULL,
    -1,
    module_methods
};


PyMODINIT_FUNC PyInit_fusedboot(void) {
    // Initialize NumPy and the internal random number generator.
    import_array();

    uint64_t initial_seed = time(NULL);
    init_random(initial_seed);

    return PyModule_Create(&module);
}
