// OpenGLInterop.cpp : Defines the entry point for the application.
//

#include <stdio.h>
#include <io.h>
#include <fcntl.h>
#include <tchar.h>
#include <vector>
#include <stdlib.h>
#include "GL/glew.h"
#include <GL/gl.h>
#include <CL/cl_gl.h>
#include <assert.h>

#include "resource.h"
#include "utils.h"
#include "cmdparser.hpp"
#include "basic.hpp"
#include "oclobject.hpp"

#include <Windows.h>

#define MAX_LOADSTRING 100

// This is WIN32 bolierplate code
// Global Variables:
HINSTANCE hInst;                    // current instance
TCHAR szTitle[MAX_LOADSTRING];      // The title bar text
TCHAR szWindowClass[MAX_LOADSTRING];// the main window class name

// Forward declarations of functions included in this code module:
ATOM    MyRegisterClass(HINSTANCE hInstance);
BOOL    InitInstance(HINSTANCE, int, int, const char**);
LRESULT CALLBACK    WndProc(HWND, UINT, WPARAM, LPARAM);

//Iteroperability modes that this tutorial demonstrates
enum INTEROP_MODE
{
    //the least efficient interop mode:
    //it uses mapping of the GL object with glMapBuffer, wraping the resulted ptr with OpenCL buffer for processing
    //thus there is an implicit copy (by GL driver) upon calling glUnmapBuffer
    //as this happenes each frame on the buffer update, it might be especially inefficient
    eModeBufferMap,

    //again, rather inefficient interop mode:
    //now via Pixel-Buffer-Object which relies on clCreateFromGLBuffer for zero-copy with OpenCL
    //the connection between OpenCL and OpenGL objects is specified only once
    //however the actual PBO-texture transfer itself does require staging via glTexSubImage2D on each buffer update
    //so again, the update (and associated copy in GL driver) happenes every frame
    eModeBufferPBO,

    //the most efficient interop mode for sharing OpenGL textures with OpenCL
    //it relies on clCreateFromGLTexture for specifying connection of OpenGL texture with OpenCL image once (at the creation time)
    //no explicit data transfers are required just acquire/release to pass the ownership between APIs
    eModeTexture
} g_mode = eModeTexture;

//windows/texture dimensions
const int g_width = 1024, g_height=1024;
//Win32 API objects
HGLRC g_hRC = NULL;
HDC   g_hDC = NULL;
HWND  g_hWnd = NULL;
//GL objects
GLuint g_pbo = 0, g_texture = 0;

//OpenCL objects
cl_device_id     g_device = NULL;
cl_context       g_context = NULL;
cl_command_queue g_queue = NULL;
cl_mem           g_mem = NULL;
cl_kernel        g_kernel_buffer = NULL;
cl_kernel        g_kernel_image = NULL;
cl_program       g_program = NULL;

bool g_InitDone = false;
//if the OpenCL impl supports cl_khr_gl_event
//there is a guarantee that clEnqueueAcquireGLObjects/clEnqueueReleaseGLObjects
//implicitly synchronize with an OpenGL context bound in the same thread as the OpenCL context
bool g_bImplicitSync = false;

//few counters for the various statisicts the tutorial gathers
float g_full_update_time = 0;
float g_render_time = 0;
float g_kernel_time = 0;
float g_overall_fps = 0;
//this is counter for the iterations
int g_iteration = 0;
//number of frames to average the fps
const int g_iterations_num = 255;


#define GL_API_CHECK(x)do{ \
    x;\
    GLenum err = glGetError(); \
    if (GL_NO_ERROR!=err) \
{ \
    ShowWindow(g_hWnd, SW_MINIMIZE); \
    printf("GL error: %d    Happened for the following expression:\n   %s;\n    file %s, line %d\n press any key to exit...\n", err, #x, __FILE__, __LINE__);\
    return FALSE; \
} \
}while(0)

#define GENERAL_API_CHECK(x, str)do{ \
    if(!(x))\
{ \
    ShowWindow(g_hWnd, SW_MINIMIZE); \
    printf("Critical error: %s  Happened for the following expression:\n   %s;\n    file %s, line %d\n press any key to exit...\n", str, #x, __FILE__, __LINE__);\
    return FALSE; \
}; \
}while(0)

#define CL_API_CHECK(x)do{ \
    cl_int ERR = (x); \
    if(ERR != CL_SUCCESS)\
{\
    ShowWindow(g_hWnd, SW_MINIMIZE); \
    printf("OpenCL error: %s\n   Happened for the following expression:\n   %s;\n file %s, line %d\n  press any key to exit...\n", opencl_error_to_str(ERR).c_str(), #x, __FILE__, __LINE__);\
    return FALSE; \
} \
}while(0)

//creating persistent CL mem objects for the first 2 sharing modes (buffer and image-based respectively), the 3rd mode always creates the buffer on the fly
BOOL CreateCLMemObject()
{
    cl_int res = CL_SUCCESS;
    switch(g_mode)
    {
        case eModeTexture:
            //notice that since our OpenCL kernel overwrites the previous content of the texture, we specify CL_MEM_WRITE_ONLY
            //we can specify CL_MEM_READ_WRITE instead
            //(if we need the current texture contentin the OpenCL kernel, notice that qualifiers for the input OpenCL image should be chnaged accordingly)
            g_mem = clCreateFromGLTexture(g_context, CL_MEM_WRITE_ONLY, GL_TEXTURE_2D, 0, g_texture, &res);
            CL_API_CHECK(res);
            break;
        case eModeBufferPBO:
            //notice that since PBO assumes one-way texture update (the texture bits are always overwritten), we specify CL_MEM_WRITE_ONLY
            g_mem = clCreateFromGLBuffer(g_context, CL_MEM_WRITE_ONLY, g_pbo,  &res);
            CL_API_CHECK(res);
            break;
        case eModeBufferMap:
            //we re-create this buffer object on the fly,re-wrapping potentially different host-side pointer (originated from glMapBuffer) each time
            break;
    }
    return TRUE;
}

BOOL InitCL(int argc, const char** argv)
{
    // Define and parse command-line arguments
    // CmdParserDeviceType supports selecting OpenCL platform and a device by the device type
    // yet, the CmdParserDeviceType doesn not support device selection by the device index (as OpenGL shared context might host sparser set of the devices)
    CmdParserDeviceType cmd (argc, argv);
    cmd.device_type.setValuePlaceholder("cpu | gpu | acc");
    cmd.device_type.setDefaultValue("gpu");
    CmdOptionErrors param_max_error_count(cmd);
    cmd.parse();

    if(cmd.help.isSet())
    {
         return FALSE;
    }

    //for the interop with GL, the OpenCL context should be initialized AFTER OpenGL one
    cl_platform_id platform = selectPlatform(cmd.platform.getValue());
    GENERAL_API_CHECK(platform, "Failed to find the required OpenCL platform");

    std::string device_type_name = cmd.device_type.getValue();
    const cl_device_type device_type = parseDeviceType(device_type_name);

    //here we describe the platform that features sharing with the specific OpenGL context, later we query for the devices this platform offers
    cl_context_properties properties[] =
    {
        CL_CONTEXT_PLATFORM, (cl_context_properties) platform,
        CL_GL_CONTEXT_KHR,   (cl_context_properties) g_hRC,
        CL_WGL_HDC_KHR,      (cl_context_properties) g_hDC,
        0
    };

    clGetGLContextInfoKHR_fn pclGetGLContextInfoKHR = (clGetGLContextInfoKHR_fn) clGetExtensionFunctionAddressForPlatform(platform, "clGetGLContextInfoKHR");
    GENERAL_API_CHECK(pclGetGLContextInfoKHR, "Failed to query proc address for clGetGLContextInfoKHR!");

    //this is important step - getting the CL device(s) capable of sharing with the curent GL context
    size_t devSizeInBytes = 0;
    //CL_CURRENT_DEVICE_FOR_GL_CONTEXT_KHR returns only the device currently associated with the given OGL context
    //so it will return only the GPU device
    //in contrast CL_DEVICES_FOR_GL_CONTEXT_KHR returns all interopbable devices (e.g. CPU in addition to the GPU)
    //we use CL_DEVICES_FOR_GL_CONTEXT_KHR below so that we can potentially experiment by doing interop with CPU as well
    CL_API_CHECK(pclGetGLContextInfoKHR(properties, CL_DEVICES_FOR_GL_CONTEXT_KHR, 0, NULL, &devSizeInBytes));
    const size_t devNum = devSizeInBytes/sizeof(cl_device_id);

	if (devNum)
	{
		std::vector<cl_device_id> devices (devNum);
		CL_API_CHECK(pclGetGLContextInfoKHR( properties, CL_DEVICES_FOR_GL_CONTEXT_KHR, devSizeInBytes, &devices[0], NULL));
		for (size_t i=0;i<devNum; i++)
		{
			cl_device_type t;
			CL_API_CHECK(clGetDeviceInfo(devices[i], CL_DEVICE_TYPE, sizeof(t), &t, NULL));
			if(device_type==t)
			{
				g_device = devices[i];
				size_t device_name_size = 0;
				CL_API_CHECK(clGetDeviceInfo(g_device, CL_DEVICE_NAME, 0, NULL, &device_name_size));
				std::vector<char> device_name (device_name_size);
				CL_API_CHECK(clGetDeviceInfo(g_device, CL_DEVICE_NAME, device_name_size, (void*)&device_name[0], NULL));
				printf("Selecting %s device: %s\n", device_type_name.c_str(), &device_name[0]);

				size_t ext_string_size = 0 ;
				CL_API_CHECK(clGetDeviceInfo(g_device,CL_DEVICE_EXTENSIONS, NULL, NULL, &ext_string_size ));
				std::vector<char> extensions(ext_string_size);
				CL_API_CHECK(clGetDeviceInfo(g_device,CL_DEVICE_EXTENSIONS,ext_string_size,(void*)&extensions[0], NULL));
				if(!strstr(&extensions[0], "cl_khr_gl_sharing"))
				{
					printf("The selected device doesn't support cl_khr_gl_sharing!\n");
					continue;
				}
				if(strstr(&extensions[0], "cl_khr_gl_event"))
				{
					g_bImplicitSync = true;
					printf("\nThe selected device supports cl_khr_gl_event, so clEnqueueAcquireGLObjects and clEnqueueReleaseGLObjects implicitly guarantee synchronization with an OpenGL context bound in the same thread as the OpenCL context. This saves on the expensive glFinish/clFinish() calls\n\n");
				}
				break;
			}
		}
	}
    if(!g_device)
    {
       printf("Cannot find OpenCL device of the desired type (%s) in the GL-shared context!\n", device_type == CL_DEVICE_TYPE_CPU ? "CPU" : device_type == CL_DEVICE_TYPE_GPU ?"GPU": device_type == CL_DEVICE_TYPE_ACCELERATOR ?"ACC": "unknown");
       return FALSE;
    }

    cl_int res;
    g_context = clCreateContext(properties,1,&g_device,0,0,&res);
    GENERAL_API_CHECK((res == CL_SUCCESS && g_context), "clCreateContext failed!");

    g_queue = clCreateCommandQueue(g_context,g_device,CL_QUEUE_PROFILING_ENABLE,&res);
    GENERAL_API_CHECK((res == CL_SUCCESS && g_queue), "clCreateCommandQueue failed!");
    GENERAL_API_CHECK(CreateCLMemObject(), "Creating CL objects failed!");

	std::vector<char> src;
	readProgramFile(L"kernel.cl", src);
	g_program = createAndBuildProgram(src, g_context, 1, &g_device, std::string());

    //eModeBufferPBO and eModeBufferMap operate with the buffers, so both need buffer-based version of the kernel
    g_kernel_buffer = clCreateKernel(g_program,"bufferfill", &res);
    CL_API_CHECK(res);
    //eModeBufferTexture, in contrast operates with images, so it needs slightly different kernel
    g_kernel_image  = clCreateKernel(g_program,"imagefill", &res);
    CL_API_CHECK(res);
    GENERAL_API_CHECK((g_kernel_buffer && g_kernel_image), "Creating kernel(s) failed!");
    return TRUE;
}

BOOL CreateGLObject()
{
    //for true texture sharing we don't need any PBO buffers, as sharing is directly made between OpenGL texture and OpenCL image
    //we need a PBO buffer for the case of sharing via OpenCL buffers only
    if(g_mode!=eModeTexture)
    {
        //create pixel-buffer object
        GL_API_CHECK( glGenBuffers(1, &g_pbo));
        GL_API_CHECK( glBindBuffer(GL_ARRAY_BUFFER, g_pbo));

        //specifying the buffer size, and since buffer data is supposed to change often we specify GL_STREAM_*
        GL_API_CHECK( glBufferData(GL_ARRAY_BUFFER, g_width * g_height * sizeof(cl_uchar4), NULL, GL_STREAM_DRAW));
        GL_API_CHECK( glBindBuffer(GL_ARRAY_BUFFER, 0));
    }
    return TRUE;
}

BOOL InitGL(HWND hWnd)
{
    //this is regular OpenGL init step, just like for any other OpenGL-enabled apps
    PIXELFORMATDESCRIPTOR  pfd;
    pfd.nSize           = sizeof(PIXELFORMATDESCRIPTOR);
    pfd.nVersion        = 1;
    pfd.dwFlags         = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL  | PFD_DOUBLEBUFFER;
    pfd.iPixelType      = PFD_TYPE_RGBA;
    pfd.cColorBits      = 24;
    pfd.cRedBits        = 8;
    pfd.cRedShift       = 0;
    pfd.cGreenBits      = 8;
    pfd.cGreenShift     = 0;
    pfd.cBlueBits       = 8;
    pfd.cBlueShift      = 0;
    pfd.cAlphaBits      = 8;
    pfd.cAlphaShift     = 0;
    pfd.cAccumBits      = 0;
    pfd.cAccumRedBits   = 0;
    pfd.cAccumGreenBits = 0;
    pfd.cAccumBlueBits  = 0;
    pfd.cAccumAlphaBits = 0;
    pfd.cDepthBits      = 24;
    pfd.cStencilBits    = 8;
    pfd.cAuxBuffers     = 0;
    pfd.iLayerType      = PFD_MAIN_PLANE;
    pfd.bReserved       = 0;
    pfd.dwLayerMask     = 0;
    pfd.dwVisibleMask   = 0;
    pfd.dwDamageMask    = 0;

    g_hDC = GetDC(g_hWnd);
    int pfmt = ChoosePixelFormat(g_hDC , &pfd);
    GENERAL_API_CHECK(pfmt,"Failed choosing the requested PixelFormat");
    GENERAL_API_CHECK(SetPixelFormat(g_hDC , pfmt, &pfd), "Failed to set the requested PixelFormat");

    g_hRC = wglCreateContext(g_hDC );
    GENERAL_API_CHECK(g_hRC, "Failed to create a GL context");
    GENERAL_API_CHECK(wglMakeCurrent(g_hDC , g_hRC), "Failed to bind GL rendering context");

    //now create a texture
    GL_API_CHECK(glGenTextures(1, &g_texture));
    GL_API_CHECK(glBindTexture(GL_TEXTURE_2D, g_texture));
    GL_API_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE));
    GL_API_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE));
    GL_API_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST));
    GL_API_CHECK(glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST));
    GL_API_CHECK(glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, g_width, g_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, 0));
    GL_API_CHECK(glBindTexture(GL_TEXTURE_2D, 0));
    GL_API_CHECK(glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE));

    //init glew which is used to get function pointers for the OpenGL APIs
    GENERAL_API_CHECK(GLEW_OK==glewInit(), "glewInit() failed!");
    GENERAL_API_CHECK(glewIsSupported("GL_VERSION_2_1"),"Support for the required OpenGL version is missing");
    // We assume that OpenGL 2.1 and later is supposed, and you may want to try it for OpenGL 2.0 which would require the GL_ARB_pixel_buffer_object OpenGL extension;
    // the GL_ARB_pixel_buffer_object extension defines the GL_PIXEL_UNPACK_BUFFER_ARB, which turned into plain GL_PIXEL_UNPACK_BUFFER with OpenGL 2.1
    //if (! glewIsSupported("GL_VERSION_2_0 GL_ARB_pixel_buffer_object"))
    //{
    //      MessageBox(g_hWnd, L"Support for necessary OpenGL extensions missing", L"Error", MB_ABORTRETRYIGNORE);
    //      return FALSE;
    //}

    //init OpenGL color buffer and viewport
    GL_API_CHECK(glClearColor(0.0, 0.0, 0.0, 1.0));
    GL_API_CHECK(glViewport(0, 0, g_width, g_height));

    //setup camera
    GL_API_CHECK(glMatrixMode( GL_MODELVIEW));
    GL_API_CHECK(glLoadIdentity());
    GL_API_CHECK(glMatrixMode(GL_PROJECTION));
    GL_API_CHECK(glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0));


    //no lighting or depth testing, just texturing please
    GL_API_CHECK(glDisable(GL_DEPTH_TEST));
    GL_API_CHECK(glDisable(GL_LIGHTING));
    GL_API_CHECK(glEnable(GL_TEXTURE_2D));

    GENERAL_API_CHECK(CreateGLObject(), "Creating OpenGL objects!");

    return TRUE;
}

BOOL CallCLKernel()
{
    const double start = time_stamp();
    if(g_mode == eModeTexture)
    {
        const cl_float4 pattern = {(float)g_iteration/g_iterations_num,0.f,0.f,1.f};//float required for write_imagef
        CL_API_CHECK(clSetKernelArg(g_kernel_image ,0, sizeof(pattern), &pattern));
        CL_API_CHECK(clSetKernelArg(g_kernel_image ,1, sizeof(g_mem), &g_mem));
        const size_t gs[2] = {g_width, g_height};
        //eModeBufferTexture, operates with images, so it needs kernel that processes images
        CL_API_CHECK(clEnqueueNDRangeKernel(g_queue,g_kernel_image, 2, 0, gs, NULL, NULL, NULL, NULL));
    }
    else
    {
        const cl_uchar4 pattern = {0,(g_mode == eModeBufferPBO)*g_iteration,(g_mode == eModeBufferMap)*g_iteration,255};
        CL_API_CHECK(clSetKernelArg(g_kernel_buffer,0, sizeof(pattern), &pattern));
        CL_API_CHECK(clSetKernelArg(g_kernel_buffer,1, sizeof(g_mem), &g_mem));
        const size_t gs [] = {g_width*g_height};
        //in contrast to the prev block, eModeBufferPBO and eModeBufferMap modes operate with the buffers, so these need different version of the kernel
        CL_API_CHECK(clEnqueueNDRangeKernel(g_queue,g_kernel_buffer, 1, 0, gs, NULL, NULL, NULL, NULL));
    }
    CL_API_CHECK(clFinish(g_queue));
    g_kernel_time += float(time_stamp()-start);

    return TRUE;
}

BOOL UpdateGLObjectTexture()
{
    //for texture(image) based  sharing this is really easy, as the texture is already connected with the CL mem object (via clCreateFromGLTexture)
    //we just need to acquire it
    //the acquire step is the same as for buffer based sharing (below)
    //first, make sure the GL commands are finished
    if(!g_bImplicitSync)
    {
        GL_API_CHECK(glFinish());
    }

    CL_API_CHECK(clEnqueueAcquireGLObjects(g_queue, 1,  &g_mem, 0, 0, NULL));
    GENERAL_API_CHECK(CallCLKernel(), "CallCLKernel failed!");
    CL_API_CHECK(clEnqueueReleaseGLObjects(g_queue, 1, &g_mem, 0, 0, NULL));

    //all OpenCL operations should be finished before OGL proceeds
    if(!g_bImplicitSync)
    {
        CL_API_CHECK(clFinish(g_queue));
    }
    return TRUE;
}

BOOL UpdateGLObjectBuffer()
{
    //the acquire step is the same for image based sharing
    //first, make sure the GL commands are finished
    if(!g_bImplicitSync)
    {
        glFinish();
    }

    CL_API_CHECK(clEnqueueAcquireGLObjects(g_queue, 1,  &g_mem, 0, 0, NULL));
    GENERAL_API_CHECK(CallCLKernel(), "CallCLKernel failed!");
    CL_API_CHECK(clEnqueueReleaseGLObjects(g_queue, 1, &g_mem, 0, 0, NULL));

    //all OpenCL operations should be finished before OpenGL proceeds
    if(!g_bImplicitSync)
    {
        CL_API_CHECK(clFinish(g_queue));
    }

    //in constrast to true zero-copy image-based sharing (refer to the UpdateGLObjectTexture()), streaming data from the PBO to the texture is required
    //notice that this way we completly overwrite the previous content of the texture
    GL_API_CHECK(glBindBuffer(GL_PIXEL_UNPACK_BUFFER, g_pbo));
    GL_API_CHECK(glBindTexture(GL_TEXTURE_2D, g_texture));
    GL_API_CHECK(glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, g_width, g_height, GL_RGBA, GL_UNSIGNED_BYTE, NULL));
    GL_API_CHECK(glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0));
    return TRUE;
}

BOOL UpdateGLObjectMap()
{
    void* p = NULL;
    GL_API_CHECK(glBindBuffer(GL_PIXEL_UNPACK_BUFFER, g_pbo));
    GL_API_CHECK( p = glMapBuffer(GL_PIXEL_UNPACK_BUFFER, GL_READ_WRITE));
    //we need to create/release new OpenCL buffer each frame (to wrap the potentially different pointer the glMapBuffer returned)
    cl_int res;

    // Check if p is properfly aligned and memory has an appropriate size to enable zero-copy behaviour
    size_t areaSize = g_width*g_height*sizeof(cl_uchar4);
    if(!verifyZeroCopyPtr(p, areaSize))
    {
        printf(
            "[ WARNING ] Pointer alignemnt and/or size of the area do not "
            "satisfy rules to enable zero-copy behaviour.\n"
        );
    }

    //notice that since our OpenCL kernel overwrites the previous content of the texture, we specify CL_MEM_WRITE_ONLY
    g_mem = clCreateBuffer(g_context,CL_MEM_WRITE_ONLY | CL_MEM_USE_HOST_PTR, areaSize, p, &res);
    CL_API_CHECK(res);
    //for map case we don't need acquire/release
    GENERAL_API_CHECK(CallCLKernel(),"CallCLKernel failed!" );

    //the following 2 calls are needed just to force the runtime to update the actual memory behind USE_HOST_PTR pointer
    //since some (descrete) GPUs might mirror a buffer on the host and perform a sync upon map/unmap only
    void* p0 = clEnqueueMapBuffer(g_queue, g_mem,CL_TRUE,CL_MAP_WRITE,0, areaSize, 0,NULL,NULL,NULL);
    GENERAL_API_CHECK(p, "clEnqueueMapBuffer failed!");
    CL_API_CHECK(clEnqueueUnmapMemObject(g_queue,g_mem,p0,0,0,0));
    //we don't need the buffer anymore
    CL_API_CHECK(clReleaseMemObject(g_mem)); g_mem = 0;

    GL_API_CHECK(glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER));
    GL_API_CHECK(glBindTexture(GL_TEXTURE_2D, g_texture));
    GL_API_CHECK(glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, g_width, g_height, GL_RGBA, GL_UNSIGNED_BYTE, NULL));
    GL_API_CHECK(glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0));
    return TRUE;
}

void ResetCounters()
{
    g_iteration=0;
    g_overall_fps = 0;
    g_full_update_time = 0;
    g_kernel_time = 0;
    g_render_time = 0;
}

static bool g_bTip = true;
BOOL Render()
{
    const double start = time_stamp ();
    BOOL res = FALSE;

    switch(g_mode)
    {
    case eModeTexture:
        {
            res = UpdateGLObjectTexture();
            break;
        }
    case eModeBufferPBO:
        {
            res = UpdateGLObjectBuffer();
            break;
        }
    case eModeBufferMap:
        {
            res = UpdateGLObjectMap();
            break;
        }
    default:
        return FALSE;
    }
    const double phase = time_stamp();
    g_full_update_time += float(phase-start);

    GENERAL_API_CHECK(res, "Failed to update GL texture!");
    // render using quad and the g_texture
    GL_API_CHECK(glBindTexture(GL_TEXTURE_2D, g_texture));
    glBegin(GL_QUADS);
    glTexCoord2f(0.0f, 0.0f);
    glVertex3f(-1.0f, -1.0f, 0.1f);

    glTexCoord2f(1.0f, 0.0f);
    glVertex3f(1.0f, -1.0f, 0.1f);

    glTexCoord2f(1.0f, 1.0f);
    glVertex3f(1.0f, 1.0f, 0.1f);

    glTexCoord2f(0.0f, 1.0f);
    glVertex3f(-1.0f, 1.0f, 0.1f);
    glEnd();
    GENERAL_API_CHECK(SwapBuffers(g_hDC), "SwapBuffers failed!");
    g_render_time +=float(time_stamp()-phase);

    if(g_iteration++ == g_iterations_num)
    {
        char title [256];
        _snprintf_s(title, 256, "%sInterop Mode: %s FPS: %.2f",
            g_bTip?"<Press TAB to change mode>" :"",
            ((g_mode == eModeTexture)? "Image-based (zero-copy)" : (g_mode == eModeBufferPBO) ? "PBO sharing with copy" : "plain Map/Unmap"),
            g_overall_fps/g_iterations_num);
        ::SetWindowTextA(g_hWnd,title);
        //below we need to multiply/divide by 1000, to convert from sec to ms
        printf("Average frame time %.3f ms\n", 1000/(g_overall_fps/g_iterations_num));
        printf("   Average time for %s is %.3f ms\n",
            ((g_mode == eModeTexture)? "GL texture acquire/release in OpenCL" :
            (g_mode == eModeBufferPBO) ? "PBO acquire/release in OpenCL+glTexSubImage2D" : "glMap/Unmap+clCreateBuffer+clEnqueueMap/Unmap"),
            (g_full_update_time - g_kernel_time)*1000/g_iterations_num);
        printf("   Average kernel time is %.3f ms\n", g_kernel_time*1000/g_iterations_num);
        printf("   Average render time is %.3f ms\n", g_render_time*1000/g_iterations_num);
        ResetCounters();
    }
    else
    {
        g_overall_fps += 1.0f/float(time_stamp()-start);
    }

    return TRUE;
}

BOOL InitInstance(HINSTANCE hInstance, int nCmdShow, int argc, const char** argv)
{
    hInst = hInstance; // Store instance handle in our global variable
    //we create window sized exactly the texture resolution, we also disable resizing (via ^WS_THICKFRAME) except maximazing
    //to avoid flickering (would require handling WM_ERASEBKGND)
    g_hWnd = CreateWindow(szWindowClass, szTitle, WS_OVERLAPPEDWINDOW^WS_THICKFRAME,
        CW_USEDEFAULT, 0, g_width, g_height, NULL, NULL, hInstance, NULL);

    //for the interop with GL, the OpenCL context should be initialized AFTER OpenGL one
    if (!g_hWnd || !InitGL(g_hWnd) || !InitCL(argc, argv))
    {
        return FALSE;
    }
    g_InitDone =true;
    ShowWindow(g_hWnd, nCmdShow);
    UpdateWindow(g_hWnd);

    return TRUE;
}

//
//  FUNCTION: WndProc(HWND, UINT, WPARAM, LPARAM)
//
//  PURPOSE:  Processes messages for the main window.
//
//  WM_COMMAND	- process the application menu
//  WM_PAINT	- Paint the main window
//  WM_DESTROY	- post a quit message and return
//
//
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    int wmId, wmEvent;

    switch (message)
    {
    case WM_COMMAND:
        wmId    = LOWORD(wParam);
        wmEvent = HIWORD(wParam);
        // Parse the menu selections:
        switch (wmId)
        {
        case IDM_EXIT:
			if (g_mem) CL_API_CHECK(clReleaseMemObject(g_mem));
            CL_API_CHECK(clRetainCommandQueue(g_queue));
            CL_API_CHECK(clReleaseProgram(g_program));
            CL_API_CHECK(clReleaseKernel(g_kernel_buffer));
            CL_API_CHECK(clReleaseKernel(g_kernel_image));
            CL_API_CHECK(clReleaseContext(g_context));
            wglMakeCurrent(NULL, NULL);
            wglDeleteContext(g_hRC);
            DeleteDC(g_hDC);
            DestroyWindow(hWnd);
            break;
        default:
            return DefWindowProc(hWnd, message, wParam, lParam);
        }
        break;
    case WM_SIZE:
        {
            int newWidth = LOWORD(lParam);
            int newHeight= HIWORD(lParam);
            GL_API_CHECK(glViewport(0, 0, newWidth, newHeight));
        }
    case WM_PAINT:
        if(!g_InitDone || !Render())
            PostQuitMessage(0);
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        break;
    case WM_KEYDOWN:
        switch (wParam)
        {
        case VK_TAB:
            {
                g_bTip = false;
                if(eModeTexture == g_mode)
                    g_mode = eModeBufferPBO;
                else if (eModeBufferPBO == g_mode)
                    g_mode = eModeBufferMap;
                else
                    g_mode = eModeTexture;
                if(g_mem)
                {
                    CL_API_CHECK(clReleaseMemObject(g_mem)); g_mem = 0;
                }
                if(g_pbo)
                {
                    GL_API_CHECK( glDeleteBuffers(1, &g_pbo)); g_pbo = 0;
                }
                GENERAL_API_CHECK(CreateGLObject(),    "Switching modes failed!");
                GENERAL_API_CHECK(CreateCLMemObject(), "Switching modes failed!");
                ResetCounters();
                printf("\nMode:%s\n", (g_mode == eModeTexture)? "Image-based (zero-copy)" : (g_mode == eModeBufferPBO ? "PBO sharing with copy" : "Plain Map/Unmap"));
                break;
            }
        default:
            break;
        }
    default:
        return DefWindowProc(hWnd, message, wParam, lParam);
    }
    return 0;
}

int main(int argc, const char*argv[])
{
    MSG msg;
    HACCEL hAccelTable;
    HINSTANCE hInstance =  GetModuleHandle(0);

    // Initialize global strings
    LoadString(hInstance, IDS_APP_TITLE, szTitle, MAX_LOADSTRING);
    LoadString(hInstance, IDC_OPENGLINTEROP, szWindowClass, MAX_LOADSTRING);
    MyRegisterClass(hInstance);

    try
    {
        // Perform application initialization:
        if (!InitInstance (hInstance, SW_SHOWNORMAL, argc, argv))
        {
            return 1;
        }

        hAccelTable = LoadAccelerators(hInstance, MAKEINTRESOURCE(IDC_OPENGLINTEROP));

        // Main message loop:
        while (GetMessage(&msg, NULL, 0, 0))
        {
            if (!TranslateAccelerator(msg.hwnd, hAccelTable, &msg))
            {
                TranslateMessage(&msg);
                DispatchMessage(&msg);
            }
        }
    }
    catch(const CmdParser::Error& error)
    {
        printf("[ ERROR ] In command line: ");
        printf(error.what());
        printf("\n");
        printf("Run with -h for usage info.\n");
        return 1;
    }
    catch(const Error& error)
    {
        printf("[ ERROR ] Sample application specific error: ");printf(error.what());printf("\n");
        return 1;
    }
    catch(const std::exception& error)
    {
        printf("[ ERROR ] ");printf(error.what());printf("\n");
        return 1;
    }
    catch(...)
    {
        printf("[ ERROR ] Unknown/internal error happened.\n");
        return 1;
    }
    return 0;
}



//
//  FUNCTION: MyRegisterClass()
//
//  PURPOSE: Registers the window class.
//
//  COMMENTS:
//
//    This function and its usage are only necessary if you want this code
//    to be compatible with Win32 systems prior to the 'RegisterClassEx'
//    function that was added to Windows 95. It is important to call this function
//    so that the application will get 'well formed' small icons associated
//    with it.
//
ATOM MyRegisterClass(HINSTANCE hInstance)
{
    WNDCLASSEX wcex;

    wcex.cbSize = sizeof(WNDCLASSEX);

    wcex.style			= CS_HREDRAW | CS_VREDRAW;
    wcex.lpfnWndProc	= WndProc;
    wcex.cbClsExtra		= 0;
    wcex.cbWndExtra		= 0;
    wcex.hInstance		= hInstance;
    wcex.hIcon			= LoadIcon(hInstance, MAKEINTRESOURCE(IDI_OPENGLINTEROP));
    wcex.hCursor		= LoadCursor(NULL, IDC_ARROW);
    wcex.hbrBackground	= (HBRUSH)(COLOR_WINDOW+1);
    wcex.lpszMenuName	= MAKEINTRESOURCE(IDC_OPENGLINTEROP);
    wcex.lpszClassName	= szWindowClass;
    wcex.hIconSm		= LoadIcon(wcex.hInstance, MAKEINTRESOURCE(IDI_SMALL));

    return RegisterClassEx(&wcex);
}
