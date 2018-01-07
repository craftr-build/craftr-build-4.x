// Copyright (c) 2009-2013 Intel Corporation
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


#include <iostream>
#include <vector>
#include <cassert>
#include <stdexcept>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <CL/cl.h>

#include "oclobject.hpp"
#include "basic.hpp"

using std::cerr;
using std::vector;


OpenCLBasic::OpenCLBasic (
    const string& platform_name_or_index,
    const string& device_type,
    const string& device_name_or_index,
    cl_command_queue_properties queue_properties,
    const cl_context_properties* additional_context_props
) :
    platform(0),
    device(0),
    context(0),
    queue(0)
{
    selectPlatform(platform_name_or_index);
    selectDevice(device_name_or_index, device_type);
    createContext(additional_context_props);
    createQueue(queue_properties);
}


OpenCLBasic::~OpenCLBasic ()
{
    try
    {
        // Release objects in the opposite order of creation

        if(queue)
        {
            cl_int err = clReleaseCommandQueue(queue);
            SAMPLE_CHECK_ERRORS(err);
        }

        if(context)
        {
            cl_int err = clReleaseContext(context);
            SAMPLE_CHECK_ERRORS(err);
        }
    }
    catch(...)
    {
        destructorException();
    }
}


cl_platform_id selectPlatform (const string& platform_name_or_index)
{
    using namespace std;

    cl_uint num_of_platforms = 0;
    // get total number of available platforms:
    cl_int err = clGetPlatformIDs(0, 0, &num_of_platforms);
    SAMPLE_CHECK_ERRORS(err);

    // use vector for automatic memory management
    vector<cl_platform_id> platforms(num_of_platforms);
    // get IDs for all platforms:
    err = clGetPlatformIDs(num_of_platforms, &platforms[0], 0);
    SAMPLE_CHECK_ERRORS(err);

    cl_uint selected_platform_index = num_of_platforms;
    bool by_index = false;

    if(is_number(platform_name_or_index))
    {
        // Select platform by index:
        by_index = true;
        selected_platform_index = str_to<int>(platform_name_or_index);
        // does not return here; need to look at the complete platfrom list
    }

    // this is ignored in case when we have platform already selected by index
    string required_platform_subname = platform_name_or_index;

    cout << "Platforms (" << num_of_platforms << "):\n";

    // TODO In case of empty platform name select the default platform or 0th platform?

    for(cl_uint i = 0; i < num_of_platforms; ++i)
    {
        // Get the length for the i-th platform name
        size_t platform_name_length = 0;
        err = clGetPlatformInfo(
            platforms[i],
            CL_PLATFORM_NAME,
            0,
            0,
            &platform_name_length
        );
        SAMPLE_CHECK_ERRORS(err);

        // Get the name itself for the i-th platform
        // use vector for automatic memory management
        vector<char> platform_name(platform_name_length);
        err = clGetPlatformInfo(
            platforms[i],
            CL_PLATFORM_NAME,
            platform_name_length,
            &platform_name[0],
            0
        );
        SAMPLE_CHECK_ERRORS(err);

        cout << "    [" << i << "] " << &platform_name[0];

        // decide if this i-th platform is what we are looking for
        // we select the first one matched skipping the next one if any
        //
        if(
            selected_platform_index == i || // we already selected the platform by index
            string(&platform_name[0]).find(required_platform_subname) != string::npos &&
            selected_platform_index == num_of_platforms // haven't selected yet
        )
        {
            cout << " [Selected]";
            selected_platform_index = i;
            // do not stop here, just want to see all available platforms
        }

        // TODO Something when more than one platform matches a given subname

        cout << endl;
    }

    if(by_index && selected_platform_index >= num_of_platforms)
    {
        throw Error(
            "Given index of platform (" + platform_name_or_index + ") "
            "is out of range of available platforms"
        );
    }

    if(!by_index && selected_platform_index >= num_of_platforms)
    {
        throw Error(
            "There is no found platform with name containing \"" +
            required_platform_subname + "\" as a substring\n"
        );
    }

    return platforms[selected_platform_index];
}

//function to compare 2 device to sort
static bool device_comp(cl_device_id id1, cl_device_id id2)
{
    cl_int err;
    size_t len1, len2;
    err = clGetDeviceInfo(id1,CL_DEVICE_NAME,0,NULL,&len1);
    SAMPLE_CHECK_ERRORS(err);
    err = clGetDeviceInfo(id2,CL_DEVICE_NAME,0,NULL,&len2);
    SAMPLE_CHECK_ERRORS(err);
    vector<char>    name1(len1);
    vector<char>    name2(len2);
    err = clGetDeviceInfo(id1,CL_DEVICE_NAME,len1,&name1[0],NULL);
    SAMPLE_CHECK_ERRORS(err);
    err = clGetDeviceInfo(id2,CL_DEVICE_NAME,len2,&name2[0],NULL);
    SAMPLE_CHECK_ERRORS(err);
    return strcmp(&name1[0],&name2[0])>0;
}

void OpenCLBasic::selectDevice (const string& device_name_or_index, const string& device_type_name)
{
    using namespace std;

    if(!platform)
    {
        throw Error("Platform is not selected");
    }

    // List devices of a given type only
    cl_device_type device_type = parseDeviceType(device_type_name);

    cl_uint num_of_devices = 0;
    cl_int err = clGetDeviceIDs(
        platform,
        device_type,
        0,
        0,
        &num_of_devices
    );

    SAMPLE_CHECK_ERRORS(err);

    vector<cl_device_id> devices(num_of_devices);

    err = clGetDeviceIDs(
        platform,
        device_type,
        num_of_devices,
        &devices[0],
        0
    );
    SAMPLE_CHECK_ERRORS(err);

    if(num_of_devices>1)
    {// sort devices by name to be sure that order is not changed from run to run
     // it is supposed that different devices have different names
        sort(devices.begin(),devices.end(), device_comp);
    }

    cl_uint selected_device_index = num_of_devices;
    bool by_index = false;

    if(is_number(device_name_or_index))
    {
        // Select device by index:
        by_index = true;
        selected_device_index = str_to<int>(device_name_or_index);
        // does not return here; need to look at the complete devices list
    }

    // this is ignored in case when we have device already selected by index
    string required_device_subname = device_name_or_index;

    cout << "Devices (" << num_of_devices;
    if(device_type != CL_DEVICE_TYPE_ALL)
    {
        cout << "; filtered by type " << device_type_name;
    }
    cout << "):\n";

    for(cl_uint i = 0; i < num_of_devices; ++i)
    {
        // Get the length for the i-th device name
        size_t device_name_length = 0;
        err = clGetDeviceInfo(
            devices[i],
            CL_DEVICE_NAME,
            0,
            0,
            &device_name_length
        );
        SAMPLE_CHECK_ERRORS(err);

        // Get the name itself for the i-th device
        // use vector for automatic memory management
        vector<char> device_name(device_name_length);
        err = clGetDeviceInfo(
            devices[i],
            CL_DEVICE_NAME,
            device_name_length,
            &device_name[0],
            0
        );
        SAMPLE_CHECK_ERRORS(err);

        cout << "    [" << i << "] " << &device_name[0];

        // decide if this i-th device is what you are looking for
        // select the first matched skipping the next one if any
        if(
            (
                by_index &&
                selected_device_index == i  // we already selected the device by index
            ) || 
            (
                !by_index &&
                string(&device_name[0]).find(required_device_subname) != string::npos &&
                selected_device_index == num_of_devices   // haven't selected yet
            )
        )
        {
            cout << " [Selected]";
            selected_device_index = i;
            // do not stop here, just see all available devices
        }

        // TODO Something when more than one device matches a given subname

        cout << endl;
    }

    if(by_index && selected_device_index >= num_of_devices)
    {
        throw Error(
            "Given index of device (" + device_name_or_index + ") "
            "is out of range of available devices" +
            (device_type != CL_DEVICE_TYPE_ALL ?
                " (among devices of type " + device_type_name + ")" :
                string("")
            )
        );
    }

    if(!by_index && selected_device_index >= num_of_devices)
    {
        throw Error(
            "There is no found device with name containing \"" +
            required_device_subname + "\" as a substring\n"
        );
    }

    device = devices[selected_device_index];
}


std::vector<cl_device_id> selectDevices (
    cl_platform_id platform,
    const string& device_type_name
)
{
    using namespace std;

    // List devices of a given type only
    cl_device_type device_type = parseDeviceType(device_type_name);

    cl_uint num_of_devices = 0;
    cl_int err = clGetDeviceIDs(
        platform,
        device_type,
        0,
        0,
        &num_of_devices
    );

    SAMPLE_CHECK_ERRORS(err);

    vector<cl_device_id> devices(num_of_devices);

    err = clGetDeviceIDs(
        platform,
        device_type,
        num_of_devices,
        &devices[0],
        0
    );
    SAMPLE_CHECK_ERRORS(err);

    cout << "Devices (" << num_of_devices;
    if(device_type != CL_DEVICE_TYPE_ALL)
    {
        cout << "; filtered by type " << device_type_name;
    }
    cout << "):\n";

    for(cl_uint i = 0; i < num_of_devices; ++i)
    {
        // Get the length for the i-th device name
        size_t device_name_length = 0;
        err = clGetDeviceInfo(
            devices[i],
            CL_DEVICE_NAME,
            0,
            0,
            &device_name_length
        );
        SAMPLE_CHECK_ERRORS(err);

        // Get the name itself for the i-th device
        // use vector for automatic memory management
        vector<char> device_name(device_name_length);
        err = clGetDeviceInfo(
            devices[i],
            CL_DEVICE_NAME,
            device_name_length,
            &device_name[0],
            0
        );
        SAMPLE_CHECK_ERRORS(err);

        cout << "    [" << i << "] " << &device_name[0] << '\n';
    }

    return devices;
}


void OpenCLBasic::createContext (const cl_context_properties* additional_context_props)
{
    using namespace std;

    if(!platform)
    {
        throw Error("Platform is not selected");
    }

    if(!device)
    {
        throw Error("Device is not selected");
    }

    size_t number_of_additional_props = 0;
    if(additional_context_props)
    {
        // count all additional props including terminating 0
        while(additional_context_props[number_of_additional_props++]);
        number_of_additional_props--;   // now exclude terminating 0
    }

    // allocate enough space for platform and all additional props if any
    std::vector<cl_context_properties> context_props(
        2 + // for CL_CONTEXT_PLATFORM and platform itself
        number_of_additional_props +
        1   // for terminating zero
    );

    context_props[0] = CL_CONTEXT_PLATFORM;
    context_props[1] = cl_context_properties(platform);
    
    std::copy(
        additional_context_props,
        additional_context_props + number_of_additional_props,
        context_props.begin() + 2   // +2 -- skipping already initialized platform entries
    );

    context_props.back() = 0;

    cl_int err = 0;
    context = clCreateContext(&context_props[0], 1, &device, 0, 0, &err);
    SAMPLE_CHECK_ERRORS(err);
}

void OpenCLBasic::createQueue (cl_command_queue_properties queue_properties)
{
    using namespace std;

    if(!device)
    {
        throw Error("Device is not selected");
    }

    cl_int err = 0;
    queue = clCreateCommandQueue(context, device, queue_properties, &err);
    SAMPLE_CHECK_ERRORS(err);
}


void readFile (const std::wstring& file_name, vector<char>& data)
{
    using namespace std;

    // Read program from a file

    // First, determine where file exists; look at two places:
    //   - current/default directory; also suitable for full paths
    //   - directory where executable is placed
#ifdef __linux__
    //Store current locale and set default locale
    CTYPELocaleHelper locale_helper;

    ifstream file(
        wstringToString(file_name).c_str(),
        ios_base::ate | ios_base::binary
    );
#else
    ifstream file(
        file_name.c_str(),
        ios_base::ate | ios_base::binary
    );
#endif

    if(!file)
    {
        // There are no file at current/default directory or absolute
        // path. Try to open it relatively from the directory where
        // executable binary is placed.


        cerr
            << "[ WARNING ] Unable to load OpenCL source code file "
            << inquotes(wstringToString(file_name)) << " at "
            << "the default location.\nTrying to open the file "
            << "from the directory with executable...";

        file.clear();

#ifdef __linux__
        std::string dir = exe_dir();
        file.open(
            (dir + wstringToString(file_name)).c_str(),
            ios_base::ate | ios_base::binary
        );

        if(!file)
        {
            cerr << " FAILED\n";
            throw Error(
                "Cannot open file " + inquotes(dir + wstringToString(file_name))
            );
        }
        else
        {
            cerr << " OK\n";
        }
        cerr << "Full file path is " << inquotes(dir + wstringToString(file_name)) <<"\n";
#else
        std::wstring dir = exe_dir_w();
        file.open(
            (dir + file_name).c_str(),
            ios_base::ate | ios_base::binary
        );

        if(!file)
        {
            cerr << " FAILED\n";
            throw Error(
                "Cannot open file " + wstringToString(dir + file_name)
            );
        }
        else
        {
            cerr << " OK\n";
        }
        cerr << "Full file path is " << wstringToString(inquotes_w(dir + file_name)) <<"\n";
#endif

    }

    // Second, determine the file length
    std::streamoff file_length = file.tellg();

    if(file_length == -1)
    {
        throw Error(
            "Cannot determine the length of file " +
            wstringToString(inquotes_w(file_name))
        );
    }

    file.seekg(0, ios_base::beg);   // go to the file beginning
    data.resize(static_cast<size_t>(file_length));  
    file.read(&data[0], file_length);
}

void readProgramFile (const std::wstring& program_file_name, vector<char>& program_text_prepared)
{
    readFile (program_file_name, program_text_prepared);
    program_text_prepared.push_back(0); // terminatig zero

}

cl_program createAndBuildProgram (
    const std::vector<char>& program_text_prepared,
    cl_context context,
    size_t num_of_devices,
    const cl_device_id* devices,
    const string& build_options
)
{
    // Create OpenCL program and build it
    const char* raw_text = &program_text_prepared[0];
    cl_int err;
    // TODO Using prepared length and not terminating by 0 is better way?
    cl_program program = clCreateProgramWithSource(context, 1, &raw_text, 0, &err);
    SAMPLE_CHECK_ERRORS(err);

    err = clBuildProgram(program, (cl_uint)num_of_devices, devices, build_options.c_str(), 0, 0);

    if(err == CL_BUILD_PROGRAM_FAILURE)
    {
        for(size_t i = 0; i < num_of_devices; ++i)
        {
            size_t log_length = 0;
            err = clGetProgramBuildInfo(
                program,
                devices[i],
                CL_PROGRAM_BUILD_LOG,
                0,
                0,
                &log_length
            );
            SAMPLE_CHECK_ERRORS(err);

            vector<char> log(log_length);

            err = clGetProgramBuildInfo(
                program,
                devices[i],
                CL_PROGRAM_BUILD_LOG,
                log_length,
                &log[0],
                0
            );
            SAMPLE_CHECK_ERRORS(err);

            throw Error(
                "Error happened during the build of OpenCL program.\n"
                "Build log:\n" +
                string(&log[0])
            );
        }
    }

    SAMPLE_CHECK_ERRORS(err);

    return program;
}

OpenCLProgram::OpenCLProgram (
    OpenCLBasic& oclobjects,
    const std::wstring& program_file_name,
    const string& program_text,
    const string& build_options
) :
    program(0)
{
    using namespace std;

    if(!program_file_name.empty() && !program_text.empty())
    {
        throw Error(
            "Both program file name and program text are specified. "
            "Should be one of them only."
        );
    }

    if(program_file_name.empty() && program_text.empty())
    {
        throw Error(
            "Neither of program file name or program text are specified. "
            "One of them is required."
        );
    }

    assert(program_file_name.empty() + program_text.empty() == 1);

    // use vector for automatic memory management
    vector<char> program_text_prepared;

    if(!program_file_name.empty())
    {
        readProgramFile(program_file_name, program_text_prepared);
    }
    else
    {
        program_text_prepared.resize(program_text.length() + 1);  // +1 for terminating zero
        copy(program_text.begin(), program_text.end(), program_text_prepared.begin());
    }

    program = createAndBuildProgram(program_text_prepared, oclobjects.context, 1, &oclobjects.device, build_options);
}


OpenCLProgram::~OpenCLProgram ()
{
    try
    {
        if(program)
        {
            clReleaseProgram(program);
        }
    }
    catch(...)
    {
        destructorException();
    }
}

OpenCLProgramOneKernel::OpenCLProgramOneKernel (
    OpenCLBasic& oclobjects,
    const std::wstring& program_file_name,
    const string& program_text,
    const string& kernel_name,
    const string& build_options
) :
    OpenCLProgram(oclobjects, program_file_name, program_text, build_options),
    kernel(0)
{
    using namespace std;

    cl_int err = 0;
    kernel = clCreateKernel(program, kernel_name.c_str(), &err);
    SAMPLE_CHECK_ERRORS(err);
}


OpenCLProgramOneKernel::~OpenCLProgramOneKernel ()
{
    try
    {
        if(kernel)
        {
            clReleaseKernel(kernel);
        }
    }
    catch(...)
    {
        destructorException();
    }
}

OpenCLProgramMultipleKernels::OpenCLProgramMultipleKernels (
    OpenCLBasic& oclobjects,
    const std::wstring& program_file_name,
    const string& program_text,
    const string& build_options
) :
    OpenCLProgram(oclobjects, program_file_name, program_text, build_options)
{
}

OpenCLProgramMultipleKernels::~OpenCLProgramMultipleKernels ()
{
    try
    {
        for(KernelMap::iterator it = kMap.begin(); it != kMap.end() ; ++it)
        {
            cl_kernel krnl = it->second;
            if(krnl)
            {
                clReleaseKernel(krnl);
            }
        }
    }
    catch(...)
    {
        destructorException();
    }
}

cl_kernel OpenCLProgramMultipleKernels::operator[](const std::string& kernel_name)
{
    using namespace std;

    cl_kernel krnl = 0;
    KernelMap::iterator it = kMap.find(kernel_name);

    if(kMap.end() == it)    //this kernel hasn't been used yet
    {
        cl_int err = 0;
        krnl = clCreateKernel(program, kernel_name.c_str(), &err);
        SAMPLE_CHECK_ERRORS(err);

        kMap[kernel_name] = krnl;
        return krnl;
    }
    else
        return it->second;
}

cl_device_type parseDeviceType (const string& device_type_name)
{
    cl_device_type  device_type = 0;
    for(size_t pos=0,next=0; next != string::npos; pos = next+1)
    {
        next = device_type_name.find_first_of("+|",pos);
        size_t substr_len = (next!=string::npos)?(next-pos):(string::npos);
        string name = device_type_name.substr(pos,substr_len);
        if(
            name == "all" ||
            name == "ALL" ||
            name == "CL_DEVICE_TYPE_ALL"
        )
        {
            device_type |= CL_DEVICE_TYPE_ALL;
            continue;
        }

        if(
            name == "default" ||
            name == "DEFAULT" ||
            name == "CL_DEVICE_TYPE_DEFAULT"
        )
        {
            device_type |= CL_DEVICE_TYPE_DEFAULT;
            continue;
        }

        if(
            name == "cpu" ||
            name == "CPU" ||
            name == "CL_DEVICE_TYPE_CPU"
        )
        {
            device_type |= CL_DEVICE_TYPE_CPU;
            continue;
        }

        if(
            name == "gpu" ||
            name == "GPU" ||
            name == "CL_DEVICE_TYPE_GPU"
        )
        {
            device_type |= CL_DEVICE_TYPE_GPU;
            continue;
        }

        if(
            name == "acc" ||
            name == "ACC" ||
            name == "accelerator" ||
            name == "ACCELERATOR" ||
            name == "CL_DEVICE_TYPE_ACCELERATOR"
        )
        {
            device_type |= CL_DEVICE_TYPE_ACCELERATOR;
            continue;
        }

        throw Error(
            "Cannot recognize " + device_type_name + " as a device type"
        );
    }
    return device_type;
}
