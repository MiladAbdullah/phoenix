#ifndef COMMON_H_GUARD
#define COMMON_H_GUARD

#include <stdint.h>


/*
 * Checks if a compiler supports a specific attribute.
 */
#ifndef __has_attribute
#define __has_attribute(x) 0
#endif


/*
 * Forces the inlining of a function intended for inlining.
 */
#if __has_attribute(always_inline)
#define ALWAYS __attribute__((always_inline))
#else
#define ALWAYS
#endif

//

/**
 * Rotates a 64-bit unsined integer a given number of bits to the left.
 */
inline ALWAYS
static uint64_t __rotate_left_uint64(const uint64_t x, const int k) {
    return (x << k) | (x >> (64 - k));
}

//

/**
 * Converts a (random) 64-bit unsigned integer to a (random) 64-bit floating
 * point number from the (half-open) interval [0, 1). Because the IEEE 754
 * double-precision format uses a 53-bit significand, we only use the top 53
 * bits and discard the lowest 11 bits.
 */
inline ALWAYS
static double __random_uint64_to_float64(const uint64_t random) {
    return (random >> 11) * (double) 0x1.0p-53;
}


/**
 * Restricts a (random) 64-bit unsigned integer to values in the (half-open)
 * interval [0, modulus). Instead of using an integer modulo operation (which
 * also suffers from modulo bias), the random value is converted to a floating
 * point number in the interval [0, 1), multiplied by the modulus and converted
 * back to integer (truncating the floating point number).
 */
inline ALWAYS
static uint64_t __random_uint64_mod_float64(const uint64_t random, const double modulus) {
    return __random_uint64_to_float64(random) * modulus;
}

#endif // COMMON_H_GUARD
