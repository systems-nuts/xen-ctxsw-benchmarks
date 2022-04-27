// Copyright (C) 2010  Benoit Sigoure
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include <sys/mman.h>

static inline unsigned long rdtsc(void) {
  unsigned long low, high;
  asm volatile("rdtsc" : "=a" (low), "=d" (high));
  return ((low) | (high) << 32);
}

static inline long long unsigned time_ns(struct timespec* const ts) {
  if (clock_gettime(CLOCK_REALTIME, ts)) {
    exit(1);
  }
  return ((long long unsigned) ts->tv_sec) * 1000000000LLU
    + (long long unsigned) ts->tv_nsec;
}

int main(int argc, char **argv) {

  const int iterations = 10000000;

  // Array for results
  unsigned int *results = malloc(sizeof(unsigned int) * iterations);
  memset(results, 0, sizeof(unsigned int) * iterations);
  while(0 != mlock(results, sizeof(unsigned int) * iterations));
  
  // For gettime
  struct timespec ts;
  const long long unsigned start_ns = time_ns(&ts);
    
  // For RDTSC
  unsigned long long start, stop;
  start = rdtsc();
  
  // Benchmark
  for (int i = 0; i < iterations; i++) {
    if (syscall(SYS_gettid) <= 1) {
      exit(2);
    }
    stop = rdtsc();
    results[i] = (unsigned int)(stop - start);
    start = stop;
  }
  
  const long unsigned delta = time_ns(&ts) - start_ns;

  if (argc == 2) {
    FILE* out; 
    out = fopen(argv[1], "w");
    if (out == NULL) {
      return 1;
    }
    fwrite(&delta, sizeof(unsigned long long), 1, out);
    fwrite(results, sizeof(unsigned int), iterations, out);
    fclose(out);
  }

  return 0;
}
