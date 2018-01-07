// Copyright (c) 2009-2011 Intel Corporation
// All rights reserved.
//
// WARRANTY DISCLAIMER
//
// THESE MATERIALS ARE PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL INTEL OR ITS
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
// EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
// PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
// PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
// OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY OR TORT (INCLUDING
// NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THESE
// MATERIALS, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
// Intel Corporation is the author of the Materials, and requests that all
// problem reports or change requests be submitted to it directly

#include <stdio.h>
#include <stdlib.h>
#include <memory.h>
#include "CL/cl.h"
#include "CL/cl_ext.h"
#include "utils.h"
#include <assert.h>
#include "basic.hpp"
#include <vector>
#include <math.h>

#pragma warning( push )

#ifdef __linux__
char *ReadSources(const char *fileName)
#else
char *ReadSources(const wchar_t *fileName)
#endif
{
#ifdef __linux__
    FILE *file = fopen(fileName, "rb");
    if (!file)
    {
        printf("ERROR: Failed to open file '%s'\n", fileName);
        return NULL;
    }
#else
    FILE *file = _wfopen(fileName, L"rb");
    if (!file)
    {
        printf("ERROR: Failed to open file '%ls'\n", fileName);
        return NULL;
    }
#endif


    if (fseek(file, 0, SEEK_END))
    {
        printf("ERROR: Failed to seek file '%ls'\n", fileName);
        fclose(file);
        return NULL;
    }

    long size = ftell(file);
    if (size == 0)
    {
        printf("ERROR: Failed to check position on file '%ls'\n", fileName);
        fclose(file);
        return NULL;
    }

    rewind(file);

    char *src = (char *)malloc(sizeof(char) * size + 1);
    if (!src)
    {
        printf("ERROR: Failed to allocate memory for file '%ls'\n", fileName);
        fclose(file);
        return NULL;
    }

    printf("Reading file '%ls' (size %ld bytes)\n", fileName, size);
    size_t res = fread(src, 1, sizeof(char) * size, file);
    if (res != sizeof(char) * size)
    {
        printf("ERROR: Failed to read file '%ls'\n", fileName);
        fclose(file);
        free(src);
        return NULL;
    }

    src[size] = '\0'; /* NULL terminated */
    fclose(file);

    return src;
}

cl_platform_id GetIntelOCLPlatform()
{
    cl_platform_id pPlatforms[10] = { 0 };
    char pPlatformName[128] = { 0 };

    cl_uint uiPlatformsCount = 0;
    cl_int err = clGetPlatformIDs(10, pPlatforms, &uiPlatformsCount);
    for (cl_uint ui = 0; ui < uiPlatformsCount; ++ui)
    {
        err = clGetPlatformInfo(pPlatforms[ui], CL_PLATFORM_NAME, 128 * sizeof(char), pPlatformName, NULL);
        if ( err != CL_SUCCESS )
        {
            printf("ERROR: Failed to retreive platform vendor name.\n", ui);
            return NULL;
        }

        if (!strcmp(pPlatformName, "Intel(R) OpenCL"))
            return pPlatforms[ui];
    }

    return NULL;
}


void BuildFailLog( cl_program program,
                  cl_device_id device_id )
{
    size_t paramValueSizeRet = 0;
    clGetProgramBuildInfo(program, device_id, CL_PROGRAM_BUILD_LOG, 0, NULL, &paramValueSizeRet);

    char* buildLogMsgBuf = (char *)malloc(sizeof(char) * paramValueSizeRet + 1);
    if( buildLogMsgBuf )
    {
        clGetProgramBuildInfo(program, device_id, CL_PROGRAM_BUILD_LOG, paramValueSizeRet, buildLogMsgBuf, &paramValueSizeRet);
        buildLogMsgBuf[paramValueSizeRet] = '\0';    // mark end of message string

        printf("Build Log:\n");
        puts(buildLogMsgBuf);
        fflush(stdout);

        free(buildLogMsgBuf);
    }
}

bool SaveImageAsBMP ( unsigned int* ptr, int width, int height, const char* fileName)
{
    FILE* stream = NULL;
    int* ppix = (int*)ptr;
    printf("Save Image: %s \n", fileName);
    stream = fopen( fileName, "wb" );

    if( NULL == stream )
        return false;

    BITMAPFILEHEADER_OWN fileHeader;
    BITMAPINFOHEADER_OWN infoHeader;

    int alignSize  = width * 4;
    alignSize ^= 0x03;
    alignSize ++;
    alignSize &= 0x03;

    int rowLength = width * 4 + alignSize;

    fileHeader.bfReserved1  = 0x0000;
    fileHeader.bfReserved2  = 0x0000;

    infoHeader.biSize          = sizeof(BITMAPINFOHEADER_OWN);
    infoHeader.biWidth         = width;
    infoHeader.biHeight        = height;
    infoHeader.biPlanes        = 1;
    infoHeader.biBitCount      = 32;
    infoHeader.biCompression   = 0L;//BI_RGB;
    infoHeader.biSizeImage     = rowLength * height;
    infoHeader.biXPelsPerMeter = 0;
    infoHeader.biYPelsPerMeter = 0;
    infoHeader.biClrUsed       = 0; // max available
    infoHeader.biClrImportant  = 0; // !!!
    fileHeader.bfType       = 0x4D42;
    fileHeader.bfSize       = sizeof(BITMAPFILEHEADER_OWN) + sizeof(BITMAPINFOHEADER_OWN) + rowLength * height;
    fileHeader.bfOffBits    = sizeof(BITMAPFILEHEADER_OWN) + sizeof(BITMAPINFOHEADER_OWN);

    if( sizeof(BITMAPFILEHEADER_OWN) != fwrite( &fileHeader, 1, sizeof(BITMAPFILEHEADER_OWN), stream ) ) {
        // cann't write BITMAPFILEHEADER
        goto ErrExit;
    }

    if( sizeof(BITMAPINFOHEADER_OWN) != fwrite( &infoHeader, 1, sizeof(BITMAPINFOHEADER_OWN), stream ) ) {
        // cann't write BITMAPINFOHEADER_OWN
        goto ErrExit;
    }

    unsigned char buffer[4];
    int x, y;

    for (y=0; y<height; y++)
    {
        for (x=0; x<width; x++, ppix++)
        {
            if( 4 != fwrite(ppix, 1, 4, stream)) {
                goto ErrExit;
            }
        }
        memset( buffer, 0x00, 4 );

        fwrite( buffer, 1, alignSize, stream );
    }

    fclose( stream );
    return true;
ErrExit:
    fclose( stream );
    return false;
}

bool SaveImageAsBMP_32FC4(cl_float* p_buf, cl_float scale, cl_uint array_width, cl_uint array_height, const char* p_file_name)
{
    return SaveImageAsBMP_32FC4_Pitch(p_buf, scale, array_width, array_height, p_file_name, array_width, false);
}
static float RGB2sRGB(float c)
{
    if(c<= 0.0031308f)
        return c * 12.92f;
    else
        return 1.055f*pow(c,1/2.4f)-0.055f;
}

// this function convert float RGBA data into uchar RGBA data and save it into BMP file as image
bool SaveImageAsBMP_32FC4_Pitch(cl_float* p_buf, cl_float scale, cl_uint array_width, cl_uint array_height, const char* p_file_name, cl_uint array_pitch, bool convert_RGB_to_sRGB)
{
using namespace std;
    // save results in bitmap files
    float fTmpFVal = 0.0f;
    cl_uint* outUIntBuf = (cl_uint*)malloc(array_width*array_height*sizeof(cl_uint));
    if(!outUIntBuf)
    {
        printf("Failed to allocate memory for output BMP image!\n");
        return false;
    }

    for(cl_uint y = 0; y < array_height; y++)
    {
        for(cl_uint x = 0; x < array_width; x++)
        {
            // Ensure that no value is greater than 255.0
            cl_uint uiTmp[4];
            fTmpFVal = (scale*p_buf[(y*array_pitch+x)*4+0]);
            if(convert_RGB_to_sRGB)
                fTmpFVal = 255.0f*RGB2sRGB(fTmpFVal/255.0f);
            fTmpFVal = max(0.0f, min(255.0f,fTmpFVal));
            uiTmp[0] = (cl_uint)(fTmpFVal);

            fTmpFVal = (scale*p_buf[(y*array_pitch+x)*4+1]);
            if(convert_RGB_to_sRGB)
                fTmpFVal = 255.0f*RGB2sRGB(fTmpFVal/255.0f);
            fTmpFVal = max(0.0f, min(255.0f,fTmpFVal));
            uiTmp[1] = (cl_uint)(fTmpFVal);

            fTmpFVal = (scale*p_buf[(y*array_pitch+x)*4+2]);
            if(convert_RGB_to_sRGB)
                fTmpFVal = 255.0f*RGB2sRGB(fTmpFVal/255.0f);
            fTmpFVal = max(0.0f, min(255.0f,fTmpFVal));
            uiTmp[2] = (cl_uint)(fTmpFVal);

            fTmpFVal = (scale*p_buf[(y*array_width+x)*4+3]);
            fTmpFVal = max(0.0f, min(255.0f,fTmpFVal));
            uiTmp[3] = 1;    //Alfa

            outUIntBuf[(array_height-1-y)*array_width+x] = 0x000000FF & uiTmp[2];
            outUIntBuf[(array_height-1-y)*array_width+x] |= 0x0000FF00 & ((uiTmp[1]) << 8);
            outUIntBuf[(array_height-1-y)*array_width+x] |= 0x00FF0000 & ((uiTmp[0]) << 16);
            outUIntBuf[(array_height-1-y)*array_width+x] |= 0xFF000000 & ((uiTmp[3]) << 24);
        }
    }
    //----
    bool res = SaveImageAsBMP( outUIntBuf, array_width, array_height, p_file_name);
    free(outUIntBuf);
    return res;
}

// return random number of any size
#define RAND_FLOAT(max) max*2.0f*((float)rand() / (float)RAND_MAX) - max
void rand_clfloatn(void* out, size_t type_size,float max)
{
    cl_types val;
    switch(type_size)
    {
    case(sizeof(cl_float)):
        val.f_val = RAND_FLOAT(max) ;
        break;
    case(sizeof(cl_float2)):
        for(unsigned int i=0; i<2; i++)
            val.f2_val.s[i] = RAND_FLOAT(max) ;
        break;
    case(sizeof(cl_float4)):
        for(unsigned int i=0; i<4; i++)
            val.f4_val.s[i] = RAND_FLOAT(max) ;
        break;
    case(sizeof(cl_float8)):
        for(unsigned int i=0; i<8; i++)
            val.f8_val.s[i] = RAND_FLOAT(max) ;
        break;
    case(sizeof(cl_float16)):
        for(unsigned int i=0; i<16; i++)
            val.f16_val.s[i] = RAND_FLOAT(max) ;
        break;
    default:
        break;
    }

    memcpy(out,&val,type_size);
}

// return random number of any size
void line_clfloatn(void* out, float frand, size_t type_size)
{
    cl_types val;
    switch(type_size)
    {
    case(sizeof(cl_float)):
        val.f_val = frand;
        break;
    case(sizeof(cl_float2)):
        for(unsigned int i=0; i<2; i++)
            val.f2_val.s[i] = frand;
        break;
    case(sizeof(cl_float4)):
        for(unsigned int i=0; i<4; i++)
            val.f4_val.s[i] = frand;
        break;
    case(sizeof(cl_float8)):
        for(unsigned int i=0; i<8; i++)
            val.f8_val.s[i] = frand;
        break;
    case(sizeof(cl_float16)):
        for(unsigned int i=0; i<16; i++)
            val.f16_val.s[i] = frand;
        break;
    default:
        break;
    }

    memcpy(out,&val,type_size);
}

cl_mem createRandomFloatVecBuffer(cl_context* context,
                                  cl_mem_flags flags,
                                  size_t atomic_size,
                                  cl_uint num,
                                  cl_int *errcode_ret,
                                  float randmax )
{

    // fill input buffer with random values
    unsigned char* randTmp;
    unsigned char* randomInput = (unsigned char*)malloc(atomic_size*num);
    for(unsigned int i=0; i<num; i++)
    {
        randTmp = randomInput + i*atomic_size;
        rand_clfloatn(randTmp,atomic_size,randmax);
    }

    // create input/output buffers
    cl_mem outBuff;
    outBuff = clCreateBuffer(*context,
        CL_MEM_COPY_HOST_PTR | flags,
        num*atomic_size,
        randomInput,
        errcode_ret);

    free(randomInput);

    return outBuff;
}



cl_int fillRandomFloatVecBuffer(cl_command_queue* cmdqueue,
                                cl_mem* buffer,
                                size_t atomic_size,
                                cl_uint num,
                                cl_event *ev,
                                float randmax)
{

    // fill input buffer with random values
    unsigned char* randTmp;
    unsigned char* randomInput = (unsigned char*)malloc(atomic_size*num);
    for(unsigned int i=0; i<num; i++)
    {
        randTmp = randomInput + i*atomic_size;
        rand_clfloatn(randTmp,atomic_size,randmax);
    }

    // create input/output buffers
    cl_int err = clEnqueueWriteBuffer(*cmdqueue,
        *buffer,
        1,
        0,
        num*atomic_size,
        randomInput,
        0,
        NULL,
        ev);

    free(randomInput);

    return err;
}

const char* OCL_GetErrorString(cl_int error)
{
    switch (error)
    {
    case CL_SUCCESS:
        return "CL_SUCCESS";
    case CL_DEVICE_NOT_FOUND:
        return "CL_DEVICE_NOT_FOUND";
    case CL_DEVICE_NOT_AVAILABLE:
        return "CL_DEVICE_NOT_AVAILABLE";
    case CL_COMPILER_NOT_AVAILABLE:
        return "CL_COMPILER_NOT_AVAILABLE";
    case CL_MEM_OBJECT_ALLOCATION_FAILURE:
        return "CL_MEM_OBJECT_ALLOCATION_FAILURE";
    case CL_OUT_OF_RESOURCES:
        return "CL_OUT_OF_RESOURCES";
    case CL_OUT_OF_HOST_MEMORY:
        return "CL_OUT_OF_HOST_MEMORY";
    case CL_PROFILING_INFO_NOT_AVAILABLE:
        return "CL_PROFILING_INFO_NOT_AVAILABLE";
    case CL_MEM_COPY_OVERLAP:
        return "CL_MEM_COPY_OVERLAP";
    case CL_IMAGE_FORMAT_MISMATCH:
        return "CL_IMAGE_FORMAT_MISMATCH";
    case CL_IMAGE_FORMAT_NOT_SUPPORTED:
        return "CL_IMAGE_FORMAT_NOT_SUPPORTED";
    case CL_BUILD_PROGRAM_FAILURE:
        return "CL_BUILD_PROGRAM_FAILURE";
    case CL_MAP_FAILURE:
        return "CL_MAP_FAILURE";
    case CL_INVALID_VALUE:
        return "CL_INVALID_VALUE";
    case CL_INVALID_DEVICE_TYPE:
        return "CL_INVALID_DEVICE_TYPE";
    case CL_INVALID_PLATFORM:
        return "CL_INVALID_PLATFORM";
    case CL_INVALID_DEVICE:
        return "CL_INVALID_DEVICE";
    case CL_INVALID_CONTEXT:
        return "CL_INVALID_CONTEXT";
    case CL_INVALID_QUEUE_PROPERTIES:
        return "CL_INVALID_QUEUE_PROPERTIES";
    case CL_INVALID_COMMAND_QUEUE:
        return "CL_INVALID_COMMAND_QUEUE";
    case CL_INVALID_HOST_PTR:
        return "CL_INVALID_HOST_PTR";
    case CL_INVALID_MEM_OBJECT:
        return "CL_INVALID_MEM_OBJECT";
    case CL_INVALID_IMAGE_FORMAT_DESCRIPTOR:
        return "CL_INVALID_IMAGE_FORMAT_DESCRIPTOR";
    case CL_INVALID_IMAGE_SIZE:
        return "CL_INVALID_IMAGE_SIZE";
    case CL_INVALID_SAMPLER:
        return "CL_INVALID_SAMPLER";
    case CL_INVALID_BINARY:
        return "CL_INVALID_BINARY";
    case CL_INVALID_BUILD_OPTIONS:
        return "CL_INVALID_BUILD_OPTIONS";
    case CL_INVALID_PROGRAM:
        return "CL_INVALID_PROGRAM";
    case CL_INVALID_PROGRAM_EXECUTABLE:
        return "CL_INVALID_PROGRAM_EXECUTABLE";
    case CL_INVALID_KERNEL_NAME:
        return "CL_INVALID_KERNEL_NAME";
    case CL_INVALID_KERNEL_DEFINITION:
        return "CL_INVALID_KERNEL_DEFINITION";
    case CL_INVALID_KERNEL:
        return "CL_INVALID_KERNEL";
    case CL_INVALID_ARG_INDEX:
        return "CL_INVALID_ARG_INDEX";
    case CL_INVALID_ARG_VALUE:
        return "CL_INVALID_ARG_VALUE";
    case CL_INVALID_ARG_SIZE:
        return "CL_INVALID_ARG_SIZE";
    case CL_INVALID_KERNEL_ARGS:
        return "CL_INVALID_KERNEL_ARGS";
    case CL_INVALID_WORK_DIMENSION:
        return "CL_INVALID_WORK_DIMENSION";
    case CL_INVALID_WORK_GROUP_SIZE:
        return "CL_INVALID_WORK_GROUP_SIZE";
    case CL_INVALID_WORK_ITEM_SIZE:
        return "CL_INVALID_WORK_ITEM_SIZE";
    case CL_INVALID_GLOBAL_OFFSET:
        return "CL_INVALID_GLOBAL_OFFSET";
    case CL_INVALID_EVENT_WAIT_LIST:
        return "CL_INVALID_EVENT_WAIT_LIST";
    case CL_INVALID_EVENT:
        return "CL_INVALID_EVENT";
    case CL_INVALID_OPERATION:
        return "CL_INVALID_OPERATION";
    case CL_INVALID_GL_OBJECT:
        return "CL_INVALID_GL_OBJECT";
    case CL_INVALID_BUFFER_SIZE:
        return "CL_INVALID_BUFFER_SIZE";
    case CL_INVALID_MIP_LEVEL:
        return "CL_INVALID_MIP_LEVEL";
    case CL_INVALID_GLOBAL_WORK_SIZE:
        return "CL_INVALID_GLOBAL_WORK_SIZE";
    case CL_PLATFORM_NOT_FOUND_KHR:
        return "CL_PLATFORM_NOT_FOUND_KHR";

        // unknown
    default:
        return "unknown error code";
    }
}

#pragma warning( pop )
