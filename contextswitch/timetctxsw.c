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

#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <linux/futex.h>
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

static const int iterations = 500000;

static void* thread(void* restrict ftx) {
  int* futex = (int*) ftx;
  for (int i = 0; i < iterations; i++) {
    sched_yield();
    while (syscall(SYS_futex, futex, FUTEX_WAIT, 0xA, NULL, NULL, 42)) {
      // retry
      sched_yield();
    }
    *futex = 0xB;
    while (!syscall(SYS_futex, futex, FUTEX_WAKE, 1, NULL, NULL, 42)) {
      // retry
      sched_yield();
    }
  }
  return NULL;
}

int main(int argc, char **argv) {
  struct timespec ts;
  const int shm_id = shmget(IPC_PRIVATE, sizeof (int), IPC_CREAT | 0666);
  int* futex = shmat(shm_id, NULL, 0);

  unsigned int *results = malloc(sizeof(unsigned int) * iterations);
  memset(results, 0, sizeof(unsigned int) * iterations);
  int ret = mlock(results, sizeof(unsigned int) * iterations); 

  pthread_t thd;
  if (pthread_create(&thd, NULL, thread, futex)) {
    return 1;
  }
  *futex = 0xA;
  const long long unsigned start_ns = time_ns(&ts);

  unsigned long long start, stop;
  start=rdtsc();
  for (int i = 0; i < iterations; i++) {
    *futex = 0xA;
    
    while (!syscall(SYS_futex, futex, FUTEX_WAKE, 1, NULL, NULL, 42)) {
      // retry
      sched_yield();
    }
    sched_yield();
    while (syscall(SYS_futex, futex, FUTEX_WAIT, 0xB, NULL, NULL, 42)) {
      // retry
      sched_yield();
    }
    stop = rdtsc();
    results[i] = (unsigned int)(stop-start);
    start = stop;
  }
  const long long unsigned delta = time_ns(&ts) - start_ns;

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


  wait(futex);
  return 0;
}
