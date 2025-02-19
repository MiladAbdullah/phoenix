/*
 * Vectorized xoshiro256+ 1.0 random number generator.
 *
 * This code is derived from the code written by
 * David Blackman and Sebastiano Vigna (vigna@acm.org).
 *
 * The authors of xoshiro256+ consider it their best and fastest generator
 * for floating-point numbers (for which we only need the upper 53 bits),
 * because it is slightly faster than xoshiro256++/xoshiro256**. It passed
 * all tests the authors were aware of at the time of publication, with the
 * exception of the lowest three bits, which might fail linearity tests (and
 * just those). If low linear complexity is not considered an issue (as is
 * usually the case), it can be used to generate 64-bit outputs.
 *
 * The authors suggest to use a sign test (the highest bit) to generate
 * boolean values, and right shifts to extract subsets of bits.
 *
 * The state must be seeded so that it is not everywhere zero, ideally by
 * a RNG of a different family. The authors recommend to use a 64-bit seed
 * for the splitmix64 generator and use its output to initialize the state.
 */

#ifndef XOSHIRO256PV_H_GUARD
#define XOSHIRO256PV_H_GUARD

#include "common.h"

#include <stdint.h>


// Vectorized Xoshiro256+ with state only.
// Should be compiled at least with -O2 -ftree-vectorize.
// The vector width can be adjusted for the architecture.

#ifndef XOSHIRO256PV_WIDTH
#define XOSHIRO256PV_WIDTH (8)
#endif


typedef struct {
    uint64_t data[4][XOSHIRO256PV_WIDTH];
} xoshiro256pv_t;



inline ALWAYS
static void __xoshiro256pv_copy(
    const unsigned count, const uint64_t src[count], uint64_t dst[count]
) {
    for (unsigned ui = 0; ui < count; ui++) dst[ui] = src[ui];
}


inline ALWAYS
static void __xoshiro256pv_init(xoshiro256pv_t * const restrict state, const uint64_t seed[4][XOSHIRO256PV_WIDTH]) {
    for (unsigned di = 0; di < 4; di++) {
        __xoshiro256pv_copy(XOSHIRO256PV_WIDTH, &seed[di][0], &state->data[di][0]);
    }
}


inline ALWAYS
static void __xoshiro256pv_next_bulk(
    xoshiro256pv_t * const restrict state,
    const unsigned unroll_factor, uint64_t results[unroll_factor]
) {
    for (unsigned ui = 0; ui < unroll_factor; ui++) results[ui] = state->data[0][ui] + state->data[3][ui];

    uint64_t t[unroll_factor];
    for (unsigned ui = 0; ui < unroll_factor; ui++) t[ui] = state->data[1][ui] << 17;

    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[2][ui] ^= state->data[0][ui];
    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[3][ui] ^= state->data[1][ui];
    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[1][ui] ^= state->data[2][ui];
    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[0][ui] ^= state->data[3][ui];

    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[2][ui] ^= t[ui];

    for (unsigned ui = 0; ui < unroll_factor; ui++) state->data[3][ui] = __rotate_left_uint64(state->data[3][ui], 45);
}

#endif // XOSHIRO256PV_H_GUARD
