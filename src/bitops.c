#include "chemfp.h"
#include <stdio.h>

/* Bit operations related to byte and hex fingerprints

  A byte fingerprint is a length and a sequence of bytes where each byte
  stores 8 fingerprints bits, in the usual order. (That is, the byte 'A',
  which is the hex value 0x41, is the bit pattern "01000001".)


  A hex fingerprint is also stored as a length and a sequence of bytes
  but each byte encode 4 bits of the fingerprint as a hex character. The
  only valid byte values are 0-9, A-F and a-f. Other values will cause
  an error value to be returned.

/***** Functions for hex fingerprints ******/

/* Map from ASCII value to bit count. Used with hex fingerprints.
   BIG is used in cumulative bitwise-or tests to check for non-hex input */

#define BIG 16
static int hex_to_value[256] = {
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  0,     1,   2,   3,   4,   5,   6,   7,   8,   9, BIG, BIG, BIG, BIG, BIG, BIG,

  /* Upper-case A-F */
  BIG,  10,  11,  12,  13,  14,  15, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,

  /* Lower-case a-f */
  BIG,  10,  11,  12,  13,  14,  15, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,

  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,

  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
  BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG, BIG,
};

/* Map from ASCII value to popcount. Used with hex fingerprints. */

static int hex_to_popcount[256] = {
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
   0,   1,   1,   2,   1,   2,   2,   3,   1,   2,    0,   0,   0,   0,   0,   0,

    0,  2,   3,   2,   3,   3,   4,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,  2,   3,   2,   3,   3,   4,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,

    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,

    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
    0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
};

/* Map from an integer to its popcount. The maximum possible valid hex
   input is 'f'/'F', which is 15, but non-hex input will set bit 0x10, so
   I include the range 16-31 as well. */

int _popcount[32] = {
  0, 1, 1, 2, 1, 2, 2, 3,
  1, 2, 2, 3, 2, 3, 3, 4,
  0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0,
};

/* Return 1 if the string contains only hex characters; 0 otherwise */
int chemfp_hex_isvalid(int len, const unsigned char *fp) {
  int i, union_w=0;

  /* Out of range values set 0x10 so do cumulative bitwise-or and see if that
     bit is set. Optimize for the expected common case of validfingerprints. */
  for (i=0; i<len; i++) {
	union_w |= hex_to_value[fp[i]];
  }
  return (union_w < BIG) ? 1 : 0;
}

/* Return the population count of a hex fingerprint, otherwise return -1 */
int chemfp_hex_popcount(int len, const unsigned char *fp) {
  int i, union_w=0, popcount=0;

  for (i=0; i<len; i++) {
    /* Keep track of the cumulative popcount and the cumulative bitwise-or */
	popcount += hex_to_popcount[fp[i]];
	union_w |= hex_to_value[fp[i]];
  }
  if (union_w >= BIG) {
    return -1;  /* Then this was an invalid fingerprint (contained non-hex characters) */
  }
  return popcount;
}

/* Return the population count of the intersection of two hex fingerprints,
   otherwise return -1. */
int chemfp_hex_intersect_popcount(int len, const unsigned char *fp1,
								  const unsigned char *fp2) {
  int i, union_w=0, intersect_popcount=0;
  int w1, w2;

  for (i=0; i<len; i++) {
    /* Get the popcount for each hex value. (Or 0 for non-hex values.) */
	w1 = hex_to_value[fp1[i]];
	w2 = hex_to_value[fp2[i]];
    /* Cumulative bitwise-or to check for non-hex values  */
	union_w = union_w | (w1|w2);
	intersect_popcount = intersect_popcount + _popcount[w1 & w2];
  }
  if (union_w >= BIG) {
	return -1;
  }
  return intersect_popcount;
}

/* Return the Tanitoto between two hex fingerprints, or -1.0 for invalid fingerprints
   If neither fingerprint has any set bits then return 1.0 instead of inf or NaN */
/* I spent a lot of time trying out different ways to optimize this code.
   This is quite fast, but feel free to point out better ways! */
double chemfp_hex_tanimoto(int len, const unsigned char *fp1,
						   const unsigned char *fp2) {
  int i=0, union_w=0;
  int union_popcount=0, intersect_popcount=0;
  int w1, w2;
  int w3, w4;
  int upper_bound = len - (len%2);

  /* Hex fingerprints really should be even-length since two hex characters
     are used for a single fingerprint byte and all chemfp fingerprints must
	 be a multiple of 8 bits. I'll allow odd-lengths since I don't see how
     that's a bad idea and I can see how some people will be confused by
     expecting odd lengths to work. More specifically, I was confused because
     I used some odd lengths in my tests. ;) */

  /* I'll process two characters at a time. Loop-unrolling was about 4% faster. */
  for (; i<upper_bound; i+=2) {
	w1 = hex_to_value[fp1[i]];
	w2 = hex_to_value[fp2[i]];
	w3 = hex_to_value[fp1[i+1]];
	w4 = hex_to_value[fp2[i+1]];
	/* Check for illegal characters */
	union_w |= (w1|w2|w3|w4);
	/* The largest possible index is w1|w2 = (16 | 15) == 31 and */
    /* is only possible when the input is not a legal hex character. */
	union_popcount += _popcount[w1|w2]+_popcount[w3|w4];
	/* The largest possible index is w1&w2 = (16 & 16) == 16 */
	intersect_popcount += _popcount[w1&w2]+_popcount[w3&w4];
  }
  /* Handle the final byte for the case of odd fingerprint length */
  for (; i<len; i++) {
	w1 = hex_to_value[fp1[i]];
	w2 = hex_to_value[fp2[i]];
	// Check for illegal characters
	union_w |= (w1|w2);
	// The largest possible index is (16 | 15) == 31
	// (and only when the input isn't a legal hex character)
	union_popcount += _popcount[w1|w2];
	// The largest possible index is (16 & 16) == 16
	intersect_popcount += _popcount[w1&w2];
  }
  /* Check for illegal character */
  if (union_w >= BIG) {
	return -1.0;
  }
  /* Special case define that 0/0 = 1.0. This agrees with OpenEye and after
     looking and asking around seems to be the generally accepted choice. */
  if (union_popcount == 0) {
	return 1.0;
  }
  return (intersect_popcount + 0.0) / union_popcount;  /* +0.0 to coerce to double */
}

/* Return 1 if the query fingerprint is contained in the target, 0 if it isn't,
   and -1 if the inputs aren't valid fingerprints */
/* This is written for the cases that 1) most tests fail and 2) most fingerprints are valid
int chemfp_hex_contains(int len, const unsigned char *query_fp,
						const unsigned char *target_fp) {
  int i, query_w, target_w;
  int union_w=0;
  for (i=0; i<len; i++) {
    /* Subset test is easy; check if query & target == query */
	/* I'll do word-by-word tests, where the word can also overflow to BIG */
	/* Do the normal test against BIG to see if there was a non-hex input */
	query_w = hex_to_value[query_fp[i]];
	target_w = hex_to_value[target_fp[i]];
	union_w |= (query_w|target_w);
	if ((query_w & target_w) != query_w) {
      /* Not a subset, but first, check if there was a a non-hex input */
	  if (union_w >= BIG) {
		return -1;
	  }
	  return 0;
	}
  }
  /* This was a subset, but there might have been a non-hex input */
  if (union_w >= BIG) {
	return -1;
  }
  return 1;
}

/****** byte fingerprints *******/

/* These algorithms are a lot simpler than working with hex fingeprints.
   There are a number of performance tweaks I could put in, especially
   if I know the inputs are word aligned, but I'll leave those for later. */

static int byte_popcounts[] = {
  0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4,1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,
  1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
  1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
  2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
  1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5,2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,
  2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
  2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6,3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,
  3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7,4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8  };


/* Return the population count of a byte fingerprint */
/* There are faster algorithms but this one is fast and simple, and it doesn't
   place any requirements on word alignment. */
int chemfp_byte_popcount(int len, const unsigned char *fp) {
  int i, popcount = 0;
  for (i=0; i<len; i++) {
	popcount += byte_popcounts[fp[i]];
  }
  return popcount;
}

/* Return the population count of the intersection of two byte fingerprints */
int chemfp_byte_intersect_popcount(int len, const unsigned char *fp1,
								   const unsigned char *fp2) {
  int i, intersect_popcount = 0;
  for (i=0; i<len; i++) {
	intersect_popcount += byte_popcounts[fp1[i]&fp2[i]];
  }
  return intersect_popcount;
}

/* Return the Tanitoto between two byte fingerprints, or -1.0 for invalid fingerprints
   If neither fingerprint has any set bits then return 1.0 instead of inf or NaN */
double chemfp_byte_tanimoto(int len, const unsigned char *fp1,
							const unsigned char *fp2) {
  int i, union_popcount=0, intersect_popcount=0;
  /* Accumulate the total union and intersection popcounts */
  for (i=0; i<len; i++) {
	union_popcount += byte_popcounts[fp1[i] | fp2[i]];
	intersect_popcount += byte_popcounts[fp1[i] & fp2[i]];
  }
  /* Special case for when neither fingerprint has any bytes set */
  if (union_popcount == 0) {
	return 1.0;
  }
  return (intersect_popcount + 0.0) / union_popcount;  /* +0.0 to coerce to double */
}

#if 0
// Some experimental code for testing a higher-performance popcount
// This is for 1024 bit fingerprints which are 32-bit aligned.
// It uses 64-bit words internally.
typedef unsigned long long uint64;  //assume this gives 64-bits
typedef unsigned int uint32;  //assume this gives 32-bits
const uint64 m1  = 0x5555555555555555ULL; //binary: 0101...
const uint64 m2  = 0x3333333333333333ULL; //binary: 00110011..
const uint64 m4  = 0x0f0f0f0f0f0f0f0fULL; //binary:  4 zeros,  4 ones ...
const uint64 m8  = 0x00ff00ff00ff00ffULL; //binary:  8 zeros,  8 ones ...
const uint64 m16 = 0x0000ffff0000ffffULL; //binary: 16 zeros, 16 ones ...
const uint64 m32 = 0x00000000ffffffffULL; //binary: 32 zeros, 32 ones
const uint64 hff = 0xffffffffffffffffULL; //binary: all ones
const uint64 h01 = 0x0101010101010101ULL; //the sum of 256 to the power of 0,1,2,3...

// uintptr_t -- an int long enough for a pointer

// 1024 bits is 128 bytes is 16 uint64s
double chemfp_byte_tanimoto_128(const unsigned char *fp1,
								const unsigned char *fp2) {
  uint32 *ifp1 = (uint32 *) fp1;
  uint32 *ifp2 = (uint32 *) fp2;
  uint64 u, i;
  int union_popcount=0;
  int intersect_popcount=0;

  //  if ((fp1 & 0x7) != 4 || (fp2 & 0x7 != 4)) {
  //	printf("SKIP!\n");
  //	return chemfp_byte_tanimoto(128, fp1, fp2);
  //  }
  int n=16;
  do {
	u = (((uint64)(ifp1[0] | ifp2[0])) << 32) + (ifp1[1] | ifp2[1]);
	i = (((uint64)(ifp1[0] & ifp2[0])) << 32) + (ifp1[1] & ifp2[1]);
    u -= (u >> 1) & m1;             //put count of each 2 bits into those 2 bits
    i -= (i >> 1) & m1;
    u = (u & m2) + ((u >> 2) & m2); //put count of each 4 bits into those 4 bits 
    i = (i & m2) + ((i >> 2) & m2);
    u = (u + (u >> 4)) & m4;        //put count of each 8 bits into those 8 bits 
    i = (i + (i >> 4)) & m4;
    union_popcount += (u * h01)>>56;  //returns left 8 bits of x + (x<<8) + (x<<16) + (x<<24)+...
    intersect_popcount += (i * h01)>>56;
	ifp1+=2;
	ifp2+=2;
  } while (--n);
  if (union_popcount == 0) {
	return 1.0;
  }
  return (intersect_popcount + 0.0) / union_popcount;
}

#endif


/* Return 1 if the query fingerprint is contained in the target, 0 if it isn't */
int chemfp_byte_contains(int len, const unsigned char *query_fp,
						 const unsigned char *target_fp) {
  int i;
  for (i=0; i<len; i++) {
	if ((query_fp[i] & target_fp[i]) != query_fp[i]) {
	  return 0;
	}
  }
  return 1;
}

