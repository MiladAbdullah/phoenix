/*
 * Scalar splitmix64 random number generator.
 *
 * This code is derived from the code written by
 * David Blackman and Sebastiano Vigna (vigna@acm.org).
 *
 * This generator is primarily used to seed other random number generators.
 */

#ifndef SPLITMIX64_H_GUARD
#define SPLITMIX64_H_GUARD

#include "common.h"

#include <stdint.h>


// Scalar SplitMix64 with state only.

typedef struct {
    uint64_t data;
} splitmix64_t;


inline ALWAYS
static void __splitmix64_init(splitmix64_t * const restrict state, const uint64_t seed) {
    state->data = seed;
}


inline ALWAYS
static uint64_t __splitmix64_next(splitmix64_t * const restrict state) {
    uint_fast64_t z = state->data;
    z += UINT64_C(0x9e3779b97f4a7c15);
    state->data = z;

    z ^= (z >> 30);
    z *= UINT64_C(0xbf58476d1ce4e5b9);
    z ^= (z >> 27);
    z *= UINT64_C(0x94d049bb133111eb);
    z ^= (z >> 31);

    return z;
}

#endif // SPLITMIX64_H_GUARD
