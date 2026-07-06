#include <cuda_runtime.h>
#include <stdlib.h>
#include <time.h>

__global__ void vecsum_k( const float* __restrict__ A, const float* __restrict__ B, float* C, size_t n )
{
  int idx = threadIdx.x + blockIdx.x * blockDim.x;
  if( idx < n )
    C[idx] = A[idx] + B[idx];
}

int main( void )
{
  const size_t N = 1 << 9;
  srand( (unsigned int)time( NULL ) );

  float *h_A, *h_B, *h_C;
  size_t vecbytes = N * sizeof(float);
  h_A = (float *)malloc( vecbytes );
  h_B = (float *)malloc( vecbytes );
  h_C = (float *)malloc( vecbytes );

  for( size_t i = 0; i < N; ++i )
  {
    h_A[i] = (float)rand() / (float)RAND_MAX;
    h_B[i] = (float)rand() / (float)RAND_MAX;
  }

  float *d_A, *d_B, *d_C;
  cudaMalloc( (void**)&d_A, vecbytes );
  cudaMalloc( (void**)&d_B, vecbytes );
  cudaMalloc( (void**)&d_C, vecbytes );

  cudaMemcpy( d_A, h_A, vecbytes, cudaMemcpyHostToDevice );
  cudaMemcpy( d_B, h_B, vecbytes, cudaMemcpyHostToDevice );

  vecsum_k<<< (N + 255) / 256, 256 >>>( d_A, d_B, d_C, N );
  cudaDeviceSynchronize();

  cudaMemcpy( h_C, d_C, vecbytes, cudaMemcpyDeviceToHost );

  free( h_A );
  free( h_B );
  free( h_C );
  cudaFree( d_A );
  cudaFree( d_B );
  cudaFree( d_C );

  return 0;
}