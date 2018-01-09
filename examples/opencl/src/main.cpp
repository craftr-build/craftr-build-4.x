/* Derived from http://distrustsimplicity.net/articles/mandelbrot-speed-comparison/ */

#define _CRT_SECURE_NO_WARNINGS
#include <iostream>
#include <fstream>
#include <chrono>

#define __CL_ENABLE_EXCEPTIONS
#include <CL/cl.hpp>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

extern "C" unsigned char Kernel[];
extern "C" size_t Kernel_size;


struct MandelbrotContext {
  std::vector<cl::Platform> platforms;
  std::vector<cl::Device> devices;
  cl::Context context;
  cl::Program program;
  cl::Kernel kernel;
  std::vector<cl::CommandQueue> queues;
  std::vector<cl::Buffer> buffers;

  size_t width;
  size_t height;
  size_t batchSize;

  MandelbrotContext() {
    cl::Platform::get(&platforms);

    std::vector<cl::Device> platformDevices;
    platforms[0].getDevices(CL_DEVICE_TYPE_GPU, &platformDevices);

    context = cl::Context(platformDevices);
    devices = context.getInfo<CL_CONTEXT_DEVICES>();

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
    program = cl::Program(context, std::string((char*)Kernel, Kernel_size));
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
      throw;
    }

    /* Create a CommandQueue for every devices. */
    queues.clear();
    for (cl::Device device : devices) {
      queues.push_back({context, device, CL_QUEUE_PROFILING_ENABLE});
    }

    setSize(3500, 2500);
  }

  inline void setSize(size_t width_, size_t height_) {
    width = width_;
    height = height_;
    /* Partition the Y-dimensions of the output image. */
    batchSize = height / queues.size();
    if (batchSize * queues.size() < height) {
      batchSize += height % queues.size();
    }
    buffers.clear();
    for (cl::CommandQueue queue : queues) {
      buffers.push_back({context, CL_MEM_WRITE_ONLY, (size_t)width * batchSize, nullptr});
    }
    std::cout << "Batch Size: " << batchSize << "\n";
  }

  inline void render() {
    kernel = cl::Kernel(program, "mandelbrot");
    for (size_t i = 0; i < queues.size(); ++i) {
      cl::NDRange offset(0, i * batchSize);
      cl::NDRange global_size(width, batchSize);
      cl::NDRange local_size(10, 10);
      kernel.setArg(0, buffers[i]);  // output
      kernel.setArg(1, width);   // height
      kernel.setArg(2, height);  // width
      kernel.setArg(3, 2.0f);    // bound
      kernel.setArg(4, 200);     // bailout
      queues[i].enqueueNDRangeKernel(kernel, offset, global_size, local_size);
    }
  }

  inline std::vector<cl::Event> readout(unsigned char* buffer) const {
    std::vector<cl::Event> eventList;
    for (int i = 0; i < queues.size(); ++i) {
      size_t offset = i * width * batchSize;
      cl::Event readDoneEvent;
      queues[i].enqueueReadBuffer(buffers[i], CL_FALSE, 0, width * batchSize, &(buffer[offset]), NULL, &readDoneEvent);
      eventList.push_back(readDoneEvent);
    }
    return eventList;
  }

};


int realMain() {
  MandelbrotContext ctx;
  ctx.render();
  auto* result = new unsigned char[ctx.width * ctx.height];
  cl::Event::waitForEvents(ctx.readout(result));
  stbi_write_png("mandelbrot_cl.png", ctx.width, ctx.height, 1, result, 0);
  return 0;
}

int main(int argc, char** argv) {
  try {
    return realMain();
  }
  catch (cl::Error e) {
    std::cerr << "fatal: " << e.what() << "\n";
    return 1;
  }
  catch (std::exception e) {
    std::cerr << "fatal: " << e.what() << "\n";
    return 1;
  }
  catch (...) {
    std::cerr << "fatal: unknown exception\n";
    return 1;
  }
}
