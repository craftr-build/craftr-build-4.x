/* Derived from http://distrustsimplicity.net/articles/mandelbrot-speed-comparison/ */

#include <iostream>
#include <fstream>
#include <chrono>

#define __CL_ENABLE_EXCEPTIONS
#include <CL/cl.hpp>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

extern "C" unsigned char Kernel[];
extern "C" size_t Kernel_size;

int main(int argc, char** argv) {
  /* Width and height of the output image. */
  static int const width = 350;
  static int const height = 250;

  std::vector<cl::Platform> platforms;
  cl::Platform::get(&platforms);

  std::vector<cl::Device> platformDevices;
  platforms[0].getDevices(CL_DEVICE_TYPE_GPU, &platformDevices);

  cl::Context context(platformDevices);
  auto devices = context.getInfo<CL_CONTEXT_DEVICES>();

  /* Show which devices we'll use for the computation. */
  std::cout << "OpenCL Devices:\n";
  for (cl::Device device : devices) {
    std::cout << "  - " << device.getInfo<CL_DEVICE_NAME>() << "\n";
    std::cout << "    - CL_DEVICE_MAX_WORK_ITEM_DIMENSIONS: " << device.getInfo<CL_DEVICE_MAX_WORK_ITEM_DIMENSIONS>() << "\n";
    std::vector<size_t> dimensions = device.getInfo<CL_DEVICE_MAX_WORK_ITEM_SIZES>();
    std::cout << "    - CL_DEVICE_MAX_WORK_ITEM_SIZES: ";
    for (size_t v : dimensions) std::cout << v << ", ";
    std::cout << "\n";
  }

  /* Compile the mandelbrot kernel. */
  cl::Program program(context, std::string((char*)Kernel, Kernel_size));
  try {
    program.build(devices);
  }
  catch (cl::Error e) {
    std::cerr << "fatal: failed to compile kernel\n";
    if (e.err() == CL_BUILD_PROGRAM_FAILURE) {
      /* Find the build log for the device that the compilation failed for. */
      for (cl::Device device : devices) {
        cl_build_status status = program.getBuildInfo<CL_PROGRAM_BUILD_STATUS>(device);
        if (status != CL_BUILD_ERROR) {
          continue;
        }
        std::cerr << program.getBuildInfo<CL_PROGRAM_BUILD_LOG>(device) << "\n";
      }
    }
    else {
      throw;
    }
  }

  /* Create a CommandQueue for every devices. */
  std::vector<cl::CommandQueue> queues;
  for (cl::Device device : devices) {
    queues.push_back({context, device, CL_QUEUE_PROFILING_ENABLE});
  }

  auto start = std::chrono::high_resolution_clock::now();

  /* Partition the Y-dimensions of the output image. */
  int batchSize = height / queues.size();
  if (batchSize * queues.size() < height) {
    batchSize += height % queues.size();
  }
  std::cout << "Batch Size: " << batchSize << "\n";

  /* Output buffers for the kernels per device. */
  std::vector<cl::Buffer> outputs;
  cl::Kernel mandelbrot(program, "mandelbrot");
  for (size_t i = 0; i < queues.size(); ++i) {
    cl::NDRange offset(0, i * batchSize);
    cl::NDRange global_size(width, batchSize);
    cl::NDRange local_size(20, 25);

    cl::Buffer output(context, CL_MEM_WRITE_ONLY, (size_t)width*batchSize, (void*)NULL);
    mandelbrot.setArg(0, output);  // output
    mandelbrot.setArg(1, width);   // height
    mandelbrot.setArg(2, height);  // width
    mandelbrot.setArg(3, 2.0f);    // bound
    mandelbrot.setArg(4, 200);     // bailout
    outputs.push_back(output);

    queues[i].enqueueNDRangeKernel(mandelbrot, offset, global_size, local_size);
  }

  /* Read the computation result into a new image buffer. */
  unsigned char* results = new unsigned char[width*height];
  std::vector<cl::Event> readWaitList;
  for (int i = 0; i < queues.size(); ++i) {
    cl::CommandQueue queue = queues[i];
    cl::Buffer buffer = outputs[i];
    size_t offset = i * width * batchSize;

    cl::Event readDoneEvent;
    queue.enqueueReadBuffer(buffer, CL_FALSE, 0, width * batchSize, &(results[offset]), NULL, &readDoneEvent);
    readWaitList.push_back(readDoneEvent);
  }
  cl::Event::waitForEvents(readWaitList);

  auto end = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> elapsed_seconds = end - start;
  std::cout << "Completed in " << elapsed_seconds.count() << "s\n";

  stbi_write_png("mandelbrot_cl.png", width, height, 1, results, 0);
  return 0;
}
