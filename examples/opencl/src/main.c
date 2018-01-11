
#define _CRT_SECURE_NO_WARNINGS
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <time.h>

#include <GL/glew.h>
#include <glfw3.h>

#ifdef __APPLE__
  #include <OpenCL/opencl.h>
  #include <OpenCL/opencl_gl.h>
#else
  #include <CL/cl.h>
  #include <CL/cl_gl.h>
#endif


/* Returns a handle to the platform dependent current OpenGL context. */
void* getCurrentGLC();

/* Returns a handle to the platform's current draw context. */
void* getCurrentDC();

/* The #cl_context_properties value for the current platform's DC context. */
cl_context_properties CURRENT_DISPLAY_PROP;


#ifdef _WIN32
  #include <Windows.h>

  void* getCurrentGLC() {
    return (void*) wglGetCurrentContext();
  }

  void* getCurrentDC() {
    return (void*) wglGetCurrentDC();
  }

  cl_context_properties CURRENT_DISPLAY_PROP = CL_WGL_HDC_KHR;
#else
  #error "Unsupported Platform"
#endif


unsigned char ClKernel[];
size_t ClKernel_size;

unsigned char ScreenVert[];
size_t ScreenVert_size;

unsigned char ScreenFrag[];
size_t ScreenFrag_size;

GLFWwindow* g_window;
cl_context g_clContext;


char const* getErrorString(cl_int error) {
  switch(error) {
    // run-time and JIT compiler errors
    case 0: return "CL_SUCCESS";
    case -1: return "CL_DEVICE_NOT_FOUND";
    case -2: return "CL_DEVICE_NOT_AVAILABLE";
    case -3: return "CL_COMPILER_NOT_AVAILABLE";
    case -4: return "CL_MEM_OBJECT_ALLOCATION_FAILURE";
    case -5: return "CL_OUT_OF_RESOURCES";
    case -6: return "CL_OUT_OF_HOST_MEMORY";
    case -7: return "CL_PROFILING_INFO_NOT_AVAILABLE";
    case -8: return "CL_MEM_COPY_OVERLAP";
    case -9: return "CL_IMAGE_FORMAT_MISMATCH";
    case -10: return "CL_IMAGE_FORMAT_NOT_SUPPORTED";
    case -11: return "CL_BUILD_PROGRAM_FAILURE";
    case -12: return "CL_MAP_FAILURE";
    case -13: return "CL_MISALIGNED_SUB_BUFFER_OFFSET";
    case -14: return "CL_EXEC_STATUS_ERROR_FOR_EVENTS_IN_WAIT_LIST";
    case -15: return "CL_COMPILE_PROGRAM_FAILURE";
    case -16: return "CL_LINKER_NOT_AVAILABLE";
    case -17: return "CL_LINK_PROGRAM_FAILURE";
    case -18: return "CL_DEVICE_PARTITION_FAILED";
    case -19: return "CL_KERNEL_ARG_INFO_NOT_AVAILABLE";

    // compile-time errors
    case -30: return "CL_INVALID_VALUE";
    case -31: return "CL_INVALID_DEVICE_TYPE";
    case -32: return "CL_INVALID_PLATFORM";
    case -33: return "CL_INVALID_DEVICE";
    case -34: return "CL_INVALID_CONTEXT";
    case -35: return "CL_INVALID_QUEUE_PROPERTIES";
    case -36: return "CL_INVALID_COMMAND_QUEUE";
    case -37: return "CL_INVALID_HOST_PTR";
    case -38: return "CL_INVALID_MEM_OBJECT";
    case -39: return "CL_INVALID_IMAGE_FORMAT_DESCRIPTOR";
    case -40: return "CL_INVALID_IMAGE_SIZE";
    case -41: return "CL_INVALID_SAMPLER";
    case -42: return "CL_INVALID_BINARY";
    case -43: return "CL_INVALID_BUILD_OPTIONS";
    case -44: return "CL_INVALID_PROGRAM";
    case -45: return "CL_INVALID_PROGRAM_EXECUTABLE";
    case -46: return "CL_INVALID_KERNEL_NAME";
    case -47: return "CL_INVALID_KERNEL_DEFINITION";
    case -48: return "CL_INVALID_KERNEL";
    case -49: return "CL_INVALID_ARG_INDEX";
    case -50: return "CL_INVALID_ARG_VALUE";
    case -51: return "CL_INVALID_ARG_SIZE";
    case -52: return "CL_INVALID_KERNEL_ARGS";
    case -53: return "CL_INVALID_WORK_DIMENSION";
    case -54: return "CL_INVALID_WORK_GROUP_SIZE";
    case -55: return "CL_INVALID_WORK_ITEM_SIZE";
    case -56: return "CL_INVALID_GLOBAL_OFFSET";
    case -57: return "CL_INVALID_EVENT_WAIT_LIST";
    case -58: return "CL_INVALID_EVENT";
    case -59: return "CL_INVALID_OPERATION";
    case -60: return "CL_INVALID_GL_OBJECT";
    case -61: return "CL_INVALID_BUFFER_SIZE";
    case -62: return "CL_INVALID_MIP_LEVEL";
    case -63: return "CL_INVALID_GLOBAL_WORK_SIZE";
    case -64: return "CL_INVALID_PROPERTY";
    case -65: return "CL_INVALID_IMAGE_DESCRIPTOR";
    case -66: return "CL_INVALID_COMPILER_OPTIONS";
    case -67: return "CL_INVALID_LINKER_OPTIONS";
    case -68: return "CL_INVALID_DEVICE_PARTITION_COUNT";

    // extension errors
    case -1000: return "CL_INVALID_GL_SHAREGROUP_REFERENCE_KHR";
    case -1001: return "CL_PLATFORM_NOT_FOUND_KHR";
    case -1002: return "CL_INVALID_D3D10_DEVICE_KHR";
    case -1003: return "CL_INVALID_D3D10_RESOURCE_KHR";
    case -1004: return "CL_D3D10_RESOURCE_ALREADY_ACQUIRED_KHR";
    case -1005: return "CL_D3D10_RESOURCE_NOT_ACQUIRED_KHR";
    default: return "Unknown OpenCL error";
  }
}

int initWindow() {
  if (!glfwInit()) {
    fprintf(stderr, "fatal: failed to initialize GLFW.\n");
    return 1;
  }

  glfwWindowHint(GLFW_SAMPLES, 4);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE); /* To make MacOS happy; should not be needed. */
	glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

	/* Open a window and create its OpenGL context. */
  g_window = glfwCreateWindow(1024, 768, "Mandelbrot", NULL, NULL);
	if (!g_window){
		fprintf(stderr, "Failed to open GLFW window. If you have an Intel GPU, they are not 3.3 compatible. Try the 2.1 version of the tutorials.\n");
		getchar();
		glfwTerminate();
		return 1;
	}
  glfwMakeContextCurrent(g_window);

	/* Initialize GLEW. */
	if (glewInit() != GLEW_OK) {
		fprintf(stderr, "Failed to initialize GLEW\n");
		getchar();
		glfwTerminate();
		return 1;
	}

	/* Ensure we can capture the escape key being pressed below. */
  glfwSetInputMode(g_window, GLFW_STICKY_KEYS, GL_TRUE);

  return 0;
}

void destroyWindow() {
  glfwTerminate();
}

GLuint createShader(GLenum shaderType, char const* code) {
  GLuint shader = glCreateShader(shaderType);
  if (shader != 0) {
    glShaderSource(shader, 1, &code, NULL);
    glCompileShader(shader);
    GLint infoLength = 0;
    glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &infoLength);
    if (infoLength > 0) {
      char* data = calloc(infoLength+1, 1);
      if (data) {
        glGetShaderInfoLog(shader, infoLength, NULL, data);
        fprintf(stderr, "SHADER: %s\n", data);
        free(data);
      }
    }
  }
  return shader;
}

GLuint createProgram(char const* vert, char const* frag) {
  GLuint vertShader = createShader(GL_VERTEX_SHADER, vert);
  if (vertShader == 0) return 0;
  GLuint fragShader = createShader(GL_FRAGMENT_SHADER, frag);
  if (fragShader == 0) return 0;
  GLuint program = glCreateProgram();
  glAttachShader(program, vertShader);
  glAttachShader(program, fragShader);
  glLinkProgram(program);
  GLint infoLength;
  glGetProgramiv(program, GL_INFO_LOG_LENGTH, &infoLength);
  if (infoLength > 0) {
    char* data = calloc(infoLength+1, 1);
    if (data) {
      glGetProgramInfoLog(program, infoLength, NULL , data);
      fprintf(stderr, "PROGRAM: %s\n", data);
      free(data);
    }
  }
  return program;
}

int main(int argc, char** argv) {
  if (initWindow() != 0) return 1;

  /* Select the first OpenCL platform. */
  printf("Looking for OpenCL platform ...\n");
  cl_platform_id platform;
  cl_uint num_platforms;
  clGetPlatformIDs(1, &platform, &num_platforms);
  if (num_platforms == 0) {
    fprintf(stderr, "error: no OpenCL platforms available.\n");
    return 1;
  }

  /* Get the first OpenCL device. */
  printf("Looking for OpenCL device ...\n");
  cl_device_id device;
  cl_uint num_devices;
  clGetDeviceIDs(platform, CL_DEVICE_TYPE_DEFAULT, 1, &device, &num_devices);
  if (num_devices == 0) {
    fprintf(stderr, "error: no OpenCL device available.\n");
    return 1;
  }

  /* Create an OpenCL context that has access to the OpenGL context. */
  printf("Looking for OpenCL context ...\n");
  cl_context_properties props[] = {
    CL_CONTEXT_PLATFORM, (cl_context_properties) platform,
    CURRENT_DISPLAY_PROP, (cl_context_properties) getCurrentDC(),
    CL_GL_CONTEXT_KHR, (cl_context_properties) getCurrentGLC(),
    0
  };
  cl_int error = CL_SUCCESS;
  g_clContext = clCreateContext(props, 1, &device, NULL, NULL, &error);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: OpenCL context could not be created: %d\n", error);
    return 1;
  }

  /* Compile the OpenCL kernel. */
  printf("Compiling OpenCL kernel ...\n");
  char const* kernelSource = (char*)ClKernel;
  cl_program program = clCreateProgramWithSource(
    g_clContext, 1, &kernelSource, &ClKernel_size, &error);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: OpenCL program could not be created: %d\n", error);
    return 1;
  }
  error = clBuildProgram(program, 1, &device, NULL, NULL, NULL);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: OpenCL program could not be built: %d\n", error);
    size_t logSize = 0;
    clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, 0, NULL, &logSize);
    char* data = calloc(logSize + 1, 1);
    if (data) {
      clGetProgramBuildInfo(program, device, CL_PROGRAM_BUILD_LOG, logSize, data, NULL);
      fprintf(stderr, "%s\n", data);
      free(data);
    }
    return 1;
  }

  /* Load the OpenGL shader which just plainly renders a texture. */
  printf("Compiling OpenGL shader program ...\n");
  GLuint shaderProgram = createProgram((char*)ScreenVert, (char*)ScreenFrag);
  if (shaderProgram == 0) {
    fprintf(stderr, "error: OpenGL shader program could not be created.\n");
    return 1;
  }

  int iwidth, iheight;
  glfwGetWindowSize(g_window, &iwidth, &iheight);
  cl_uint width = iwidth;
  cl_uint height = iheight;

  /* Create an OpenGL texture. */
  printf("Creating OpenGL texture ...\n");
  GLuint texture;
  glGenTextures(1, &texture);
  glBindTexture(GL_TEXTURE_2D, texture);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_FLOAT, NULL);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glBindTexture(GL_TEXTURE_2D, 0);

  /* Create an OpenCL image from the OpenGL texture. */
  printf("Creating OpenCL image from OpenGL texture ...\n");
  cl_mem cltex = clCreateFromGLTexture(g_clContext, CL_MEM_WRITE_ONLY, GL_TEXTURE_2D, 0, texture, &error);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: OpenGL=>OpenCL image could not be created: %d\n", error);
    return 1;
  }

  /* Execute the OpenCL program in a kernel. */
  cl_kernel kernel = clCreateKernel(program, "mandelbrot", &error);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: Could not create OpenCL kernel: %d\n", error);
    return 1;
  }

  /* Create a command-queue. */
  cl_command_queue queue = clCreateCommandQueue(g_clContext, device, 0, &error);
  if (error != CL_SUCCESS) {
    fprintf(stderr, "error: Could not create OpenCL command queue: %d\n", error);
    return 1;
  }

  /* Create a buffer that contains the screen coordinates. */
  GLfloat screen[] = {0.0f, 0.0f, 100.0f, 0.0f, 100.0f, 100.0f, 0.0f, 100.0f};
  GLuint vbo;
  glGenBuffers(1, &vbo);
  glBindBuffer(GL_ARRAY_BUFFER, vbo);
  glBufferData(GL_ARRAY_BUFFER, sizeof(screen), screen, GL_STATIC_DRAW);

  /* Bind the vertex buffer to the program. */
  GLint verts = glGetAttribLocation(shaderProgram, "vertices");
  if (verts == -1) {
    fprintf(stderr, "shader 'vertices' attribute not found\n");
    return 1;
  }
  glEnableVertexAttribArray(verts);
  glVertexAttribPointer(verts, 2, GL_FLOAT, GL_FALSE, 0, NULL);

  /* Bind the OpenGL/OpenCL texture to the program. */
  GLint tex = glGetUniformLocation(shaderProgram, "tex");
  if (tex == -1) {
    fprintf(stderr, "shader 'tex' uniform not found\n");
    return 1;
  }
  glUniform1i(tex, 0);
  glActiveTexture(GL_TEXTURE0);
  glBindTexture(GL_TEXTURE_2D, texture);

  /* VAO -- necessary for any rendering context. Multiple VAOs could
   * be used to efficiently switch between states. */
  GLuint vao;
	glGenVertexArrays(1, &vao);
	glBindVertexArray(vao);

  /* Create a vertex buffer for a rectangle with screen coordinates .*/
  static const GLfloat screenVertices[] = {
		 1.0f, -1.0f, 0.0f,
		 1.0f,  1.0f, 0.0f,
		-1.0f, -1.0f, 0.0f,
		-1.0f,  1.0f, 0.0f,
  };
  GLuint screenVerticesBuffer;
	glGenBuffers(1, &screenVerticesBuffer);
	glBindBuffer(GL_ARRAY_BUFFER, screenVerticesBuffer);
  glBufferData(GL_ARRAY_BUFFER, sizeof(screenVertices), screenVertices, GL_STATIC_DRAW);

  /* Mainloop. */
  double zoom = 1.0;
  double offsetx = 0.0;
  double offsety = 0.0;
  float bound = 2.0f;
  int bailout = 200;
  float tstart = clock() / (float) CLOCKS_PER_SEC;
  while (glfwGetKey(g_window, GLFW_KEY_ESCAPE) != GLFW_PRESS &&
         glfwWindowShouldClose(g_window) == 0)
  {
    glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
		glClear(GL_COLOR_BUFFER_BIT);

    if (glfwGetKey(g_window, GLFW_KEY_UP) == GLFW_PRESS) {
      offsety += 0.1 * zoom;
    }
    if (glfwGetKey(g_window, GLFW_KEY_DOWN) == GLFW_PRESS) {
      offsety -= 0.1 * zoom;
    }
    if (glfwGetKey(g_window, GLFW_KEY_LEFT) == GLFW_PRESS) {
      offsetx -= 0.1 * zoom;
    }
    if (glfwGetKey(g_window, GLFW_KEY_RIGHT) == GLFW_PRESS) {
      offsetx += 0.1 * zoom;
    }
    if (glfwGetKey(g_window, 'Q') == GLFW_PRESS) {
      bailout += 1;
    }
    if (glfwGetKey(g_window, 'W') == GLFW_PRESS) {
      bailout -= 1;
    }
    if (glfwGetKey(g_window, 'X') == GLFW_PRESS) {
      zoom += 0.1 * zoom;
    }
    if (glfwGetKey(g_window, 'Z') == GLFW_PRESS) {
      zoom -= 0.1 * zoom;
    }
    if (glfwGetKey(g_window, ' ') == GLFW_PRESS) {
      offsetx = 0.0;
      offsety = 0.0;
      zoom = 1.0;
      bailout = 200;
    }

    /* Run the kernel to render the Mandelbrot into the OpenGL texture. */
    float ox = (float) offsetx;
    float oy = (float) offsety;
    float zo = (float) zoom;
    clSetKernelArg(kernel, 0, sizeof(cltex), &cltex);
    clSetKernelArg(kernel, 1, sizeof(width), &width);
    clSetKernelArg(kernel, 2, sizeof(height), &height);
    clSetKernelArg(kernel, 3, sizeof(float), &ox);
    clSetKernelArg(kernel, 4, sizeof(float), &oy);
    clSetKernelArg(kernel, 5, sizeof(float), &zo);
    clSetKernelArg(kernel, 6, sizeof(bound), &bound);
    clSetKernelArg(kernel, 7, sizeof(bailout), &bailout);
    size_t global_work_offset[2] = {0, 0};
    size_t global_work_size[2] = {width, height};
    error = clEnqueueNDRangeKernel(queue, kernel, 2,
      global_work_offset, global_work_size, NULL, 0, NULL, NULL);
    if (error != CL_SUCCESS) {
      fprintf(stderr, "error: Could not queue kernel: %d\n", error);
      return 1;
    }
    clFinish(queue);

		glUseProgram(shaderProgram);

    /* Bind the screenspace vertices to the shader. */
		glEnableVertexAttribArray(0);
		glBindBuffer(GL_ARRAY_BUFFER, screenVerticesBuffer);
		glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, NULL);

    /* Draw the rectangle. */
		glDrawArrays(GL_TRIANGLE_STRIP, 0, 4); // 3 indices starting at 0 -> 1 triangle

		glDisableVertexAttribArray(0);

    glfwSwapBuffers(g_window);
		glfwPollEvents();
  }

  printf("Destroying window ...\n");
  destroyWindow();
  return 0;
}
