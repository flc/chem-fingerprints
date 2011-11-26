/* The original version of this code was written by Imran Haque and is
   in the supplementary information to

      Haque IS, Pande VS, and Walters WP. Anatomy of High-Performance
      2D Similarity Calculations. Journal of Chemical Information and
      Modeling 2011

See http://cs.stanford.edu/people/ihaque/


Kim Walisch make a few modifications to adapt it for work with chemfp.

*/

/*  Written by Imran S. Haque (ihaque@cs.stanford.edu)

 Copyright (c) 2011 Stanford University.
 All rights reserved.

 Redistribution and use in source and binary forms, with or without modification,
 are permitted provided that the following conditions are met:

     * Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.
     * Redistributions in binary form must reproduce the above copyright notice,
       this list of conditions and the following disclaimer in the documentation
       and/or other materials provided with the distribution.
     * Neither the name of Stanford University nor the names of its contributors
       may be used to endorse or promote products derived from this software without
       specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 POSSIBILITY OF SUCH DAMAGE.
*/


#include "popcount.h"

#if defined(GENERATE_SSSE3)

#include <emmintrin.h>
#include <tmmintrin.h>

static __m128i popcount_SSSE3_helper(const unsigned *buf, int N) {
  /* LUT of count of set bits in each possible 4-bit nibble,
     from low-to-high: 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4 */
  const __m128i LUT   = _mm_set_epi32(0x02010100, 0x03020201, 0x03020201, 0x04030302);
  const __m128i mask  = _mm_set1_epi32(0x0F0F0F0F);
  const __m128i *vbuf = (__m128i*) buf;

  __m128i total = _mm_setzero_si128();

  int i;
  for (i = 0; i < N; i += 4) {
    __m128i v0 = _mm_load_si128(vbuf+i+0);
    __m128i v1 = _mm_load_si128(vbuf+i+1);
    __m128i v2 = _mm_load_si128(vbuf+i+2);
    __m128i v3 = _mm_load_si128(vbuf+i+3);

    /* Split each byte into low and high nibbles */
    __m128i v0_lo = _mm_and_si128(mask, v0);
    __m128i v1_lo = _mm_and_si128(mask, v1);
    __m128i v2_lo = _mm_and_si128(mask, v2);
    __m128i v3_lo = _mm_and_si128(mask, v3);

    __m128i v0_hi = _mm_and_si128(mask, _mm_srli_epi16(v0, 4));
    __m128i v1_hi = _mm_and_si128(mask, _mm_srli_epi16(v1, 4));
    __m128i v2_hi = _mm_and_si128(mask, _mm_srli_epi16(v2, 4));
    __m128i v3_hi = _mm_and_si128(mask, _mm_srli_epi16(v3, 4));

    /* Compute POPCNT of each byte in two halves using PSHUFB instruction for LUT */
    __m128i count0 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v0_lo), _mm_shuffle_epi8(LUT, v0_hi));
    __m128i count1 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v1_lo), _mm_shuffle_epi8(LUT, v1_hi));
    __m128i count2 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v2_lo), _mm_shuffle_epi8(LUT, v2_hi));
    __m128i count3 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v3_lo), _mm_shuffle_epi8(LUT, v3_hi));

    total = _mm_add_epi8(total,_mm_add_epi8(_mm_add_epi8(count0, count1),
                                            _mm_add_epi8(count2, count3)));
  }

  /* Reduce 16*8b -> {-,-,-,16b,-,-,-,16b} */
  return _mm_sad_epu8(total, _mm_setzero_si128());
}

static __m128i intersect_popcount_SSSE3_helper(const unsigned *buf, const unsigned *buf2, int N) {
  /* LUT of count of set bits in each possible 4-bit nibble,
     from low-to-high: 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4 */
  const __m128i LUT    = _mm_set_epi32(0x02010100, 0x03020201, 0x03020201, 0x04030302);
  const __m128i mask   = _mm_set1_epi32(0x0F0F0F0F);
  const __m128i *vbuf  = (__m128i*) buf;
  const __m128i *vbuf2 = (__m128i*) buf2;

  __m128i total  = _mm_setzero_si128();

  int i;
  for (i = 0; i < N; i += 4) {
    __m128i v0 = _mm_and_si128(_mm_load_si128(vbuf+i+0), _mm_load_si128(vbuf2+i+0));
    __m128i v1 = _mm_and_si128(_mm_load_si128(vbuf+i+1), _mm_load_si128(vbuf2+i+1));
    __m128i v2 = _mm_and_si128(_mm_load_si128(vbuf+i+2), _mm_load_si128(vbuf2+i+2));
    __m128i v3 = _mm_and_si128(_mm_load_si128(vbuf+i+3), _mm_load_si128(vbuf2+i+3));

    /* Split each byte into low and high nibbles */
    __m128i v0_lo = _mm_and_si128(mask, v0);
    __m128i v1_lo = _mm_and_si128(mask, v1);
    __m128i v2_lo = _mm_and_si128(mask, v2);
    __m128i v3_lo = _mm_and_si128(mask, v3);

    __m128i v0_hi = _mm_and_si128(mask, _mm_srli_epi16(v0, 4));
    __m128i v1_hi = _mm_and_si128(mask, _mm_srli_epi16(v1, 4));
    __m128i v2_hi = _mm_and_si128(mask, _mm_srli_epi16(v2, 4));
    __m128i v3_hi = _mm_and_si128(mask, _mm_srli_epi16(v3, 4));

    /* Compute POPCNT of each byte in two halves using PSHUFB instruction for LUT */
    __m128i count0 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v0_lo), _mm_shuffle_epi8(LUT, v0_hi));
    __m128i count1 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v1_lo), _mm_shuffle_epi8(LUT, v1_hi));
    __m128i count2 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v2_lo), _mm_shuffle_epi8(LUT, v2_hi));
    __m128i count3 = _mm_add_epi8(_mm_shuffle_epi8(LUT, v3_lo), _mm_shuffle_epi8(LUT, v3_hi));

    total = _mm_add_epi8(total,_mm_add_epi8(_mm_add_epi8(count0, count1),
                                            _mm_add_epi8(count2, count3)));
  }

  /* Reduce 16*8b -> {-,-,-,16b,-,-,-,16b} */
  return _mm_sad_epu8(total, _mm_setzero_si128());
}

#endif /* GENERATE_SSSE3 */

/**
 * Count the number of bits set in a fingerprint using the SSSE3
 * instruction set (available in x86 CPUs >= 2006).
 * @warning  1) fp must be aligned to a 16 byte boundary.
 *           2) Use (get_cpuid_flags() & bit_SSSE3) from cpuid.h to
 *              test if the CPU supports the SSSE3 instructions.
 */
int _chemfp_popcount_SSSE3(int size, const unsigned *fp) {
  /* 2^5 loop iters might overflow 8-bit counter,
     so cap it at 2^4 iters per chunk */
  const int iters = 1 << 4;
  const int N = (size + 3) / 4;
  const int limit = N - N % (iters * 4);
  int i, count;
#if defined(GENERATE_SSSE3)
  __m128i count32 = _mm_setzero_si128();
  for (i = 0; i < limit; i += iters * 4) {
    count32 = _mm_add_epi32(count32, popcount_SSSE3_helper(&fp[i], iters));
  }
  if (i < N) {
    count32 = _mm_add_epi32(count32, popcount_SSSE3_helper(&fp[i], (N - i) / 4));
  }
  /* Layout coming from PSADBW accumulation is 2*{0,32}: 0 S1 0 S0 */
  _mm_store_ss((float*)&count, _mm_cvtepi32_ps(_mm_add_epi32(
      count32, _mm_shuffle_epi32(count32, _MM_SHUFFLE(2, 2, 2, 2)))));
#endif
  return count;
}

/**
 * Count the number of bits set within the intersection of two
 * fingerprints using the SSSE3 instruction set.
 * @warning  1) fp1 & fp2 must be aligned to 16 byte boundaries.
 *           2) Use (get_cpuid_flags() & bit_SSSE3) from cpuid.h to
 *              test if the CPU supports the SSSE3 instructions.
 */
int _chemfp_intersect_popcount_SSSE3(int size, const unsigned *fp1, const unsigned *fp2) {
  /* 2^5 loop iters might overflow 8-bit counter,
     so cap it at 2^4 iters per chunk */
  const int iters = 1 << 4;
  const int N = (size + 3) / 4;
  const int limit = N - N % (iters * 4);
  int i, count;
#if defined(GENERATE_SSSE3)
  __m128i count32 = _mm_setzero_si128();
  for (i = 0; i < limit; i += iters * 4) {
    count32 = _mm_add_epi32(count32, intersect_popcount_SSSE3_helper(&fp1[i], &fp2[i], iters));
  }
  if (i < N) {
    count32 = _mm_add_epi32(count32, intersect_popcount_SSSE3_helper(&fp1[i], &fp2[i], (N - i) / 4));
  }
  /* Layout coming from PSADBW accumulation is 2*{0,32}: 0 S1 0 S0 */
  _mm_store_ss((float*)&count, _mm_cvtepi32_ps(_mm_add_epi32(
      count32, _mm_shuffle_epi32(count32, _MM_SHUFFLE(2, 2, 2, 2)))));
#endif
  return count;
}
