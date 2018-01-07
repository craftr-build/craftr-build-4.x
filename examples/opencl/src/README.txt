******************************************************************************
**              Intel(R) SDK for OpenCL* Applications - Samples             **
**                                 README                                   **
******************************************************************************

*****  Contents  *****

  - Overview
  - Software Requirements
  - Sample Directory Content
  - Building the Sample
  - Running the Sample
  - Disclaimer and Legal Information


*****  Overview  *****

This package contains the sample that targets the Intel Processor Graphics
device. The sample is supported on Microsoft Windows* OS.

Refer to the sample User's Guide for details about the sample.

For the complete list of supported operating systems and hardware, refer to
the release notes.

*****  Software Requirements  *****

The following software is required to correctly build and run the sample:

  - Intel OpenCL implementation for target hardware set (including fresh GPU drivers)
  - Microsoft Visual Studio* 2008, 2010, or 2012

Visit the SDK website at http://software.intel.com/en-us/vcsource/tools/opencl
to get the relevant SDK version.

*****  Sample Directory Content  *****

Sample files reside in the dedicated sample directory and in the 'common'
directory in the root-level (where the sample is extracted) directory.

  - common                 -- directory with common utilities and helpers;
                              this functionality is used as a basic
                              infrastructure in the sample code
        - GL\glew.c        -- open-source OpenGL extension loading library
                              GLEW provides mechanisms for determining
                              which OpenGL extensions are supported on the target platform. 
        - cmdparser.cpp    -- command-line parameters parsing routines
          cmdparser.hpp
        - utils.cpp        -- general routines like writing bmp files
          utils.h
        - oclobject.cpp    -- general OpenCL* initialization routine
          oclobject.hpp

  - templates              -- project Property files

  - OpenGLInterop    sample directory
     - OpenGLInterop.cpp
        This is the main application source file.
     - kernel.cl
        This is the file with OpenCL kernels used in the app.
    - OpenGLInterop_2008.vcproj, OpenGLInterop_2010.vcproj, etc
        These are the main project files for the respective Visual Studio

        - OpenGLInterop.rc
        This is a listing of all of the Microsoft Windows resources that the
        program uses. It includes the icons, bitmaps, cursors,etc.
     - Resource.h
        This is the standard header file, which defines new resource IDs.
        Microsoft Visual C++ reads and updates this file.
     - OpenGLInterop.ico, small.ico         
        These are icon files, for the application (32x32 and 16x16 versions).
  - user_guide.pdf         -- sample User's Guide
  - README.TXT             -- readme file


*****  Building the Sample *****

The sample package contains the Microsoft Visual Studio solution files for
Visual Studio IDE version 2008, 2010, and 2012.
To build the sample, do the following:

1. Open the relevant solution file.
2. In Microsoft Visual Studio select Build > Build Solution.


***** Running the Sample *****

You can run the sample application using the standard interface of the
Microsoft Visual Studio IDE, or using the command line.

To run the sample using the Visual Studio IDE, do the following:

1. Open and build the appropriate solution file.
2. Press Ctrl+F5 to run the application.
To run the application in debug mode, press F5.

To run the sample using command line, do the following:

1. Open the command prompt.
2. Navigate to the sample directory.
3. Then go to the directory according to the configuration you built in the
previous step:
    - \Win32 - for Win32 configuration
    - \x64 - for x64 configuration
4. Select the appropriate configuration folder  (Debug or Release).
5. Run the sample by entering the name of the executable.
6. You can run the sample with command-line option -h or --help to print
   available command line options for the sample.


*****  Disclaimer and Legal Information *****

THESE MATERIALS ARE PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL INTEL OR ITS
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THESE
MATERIALS, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

INFORMATION IN THIS DOCUMENT IS PROVIDED IN CONNECTION WITH INTEL
PRODUCTS. NO LICENSE, EXPRESS OR IMPLIED, BY ESTOPPEL OR OTHERWISE,
TO ANY INTELLECTUAL PROPERTY RIGHTS IS GRANTED BY THIS DOCUMENT.
EXCEPT AS PROVIDED IN INTEL'S TERMS AND CONDITIONS OF SALE FOR SUCH
PRODUCTS, INTEL ASSUMES NO LIABILITY WHATSOEVER AND INTEL DISCLAIMS
ANY EXPRESS OR IMPLIED WARRANTY, RELATING TO SALE AND/OR USE OF INTEL
PRODUCTS INCLUDING LIABILITY OR WARRANTIES RELATING TO FITNESS FOR
A PARTICULAR PURPOSE, MERCHANTABILITY, OR INFRINGEMENT OF ANY PATENT,
COPYRIGHT OR OTHER INTELLECTUAL PROPERTY RIGHT.

A "Mission Critical Application" is any application in which failure
of the Intel Product could result, directly or indirectly, in personal
injury or death. SHOULD YOU PURCHASE OR USE INTEL'S PRODUCTS FOR ANY
SUCH MISSION CRITICAL APPLICATION, YOU SHALL INDEMNIFY AND HOLD INTEL
AND ITS SUBSIDIARIES, SUBCONTRACTORS AND AFFILIATES, AND THE DIRECTORS,
OFFICERS, AND EMPLOYEES OF EACH, HARMLESS AGAINST ALL CLAIMS COSTS,
DAMAGES, AND EXPENSES AND REASONABLE ATTORNEYS' FEES ARISING OUT OF,
DIRECTLY OR INDIRECTLY, ANY CLAIM OF PRODUCT LIABILITY, PERSONAL INJURY,
OR DEATH ARISING IN ANY WAY OUT OF SUCH MISSION CRITICAL APPLICATION,
WHETHER OR NOT INTEL OR ITS SUBCONTRACTOR WAS NEGLIGENT IN THE DESIGN,
MANUFACTURE, OR WARNING OF THE INTEL PRODUCT OR ANY OF ITS PARTS.

Intel may make changes to specifications and product descriptions at
any time, without notice. Designers must not rely on the absence or
characteristics of any features or instructions marked "reserved" or
"undefined". Intel reserves these for future definition and shall have
no responsibility whatsoever for conflicts or incompatibilities arising
from future changes to them. The information here is subject to change
without notice. Do not finalize a design with this information.

The products described in this document may contain design defects or
errors known as errata which may cause the product to deviate from
published specifications. Current characterized errata are available
on request.

Contact your local Intel sales office or your distributor to obtain the
latest specifications and before placing your product order.

Copies of documents which have an order number and are referenced in
this document, or other Intel literature, may be obtained
by calling 1-800-548-4725, or go to:
http://www.intel.com/design/literature.htm

Intel Corporation is the author of the Materials, and requests that all
problem reports or change requests be submitted to it directly.

Intel Core, HD Graphics and Iris Graphics are trademarks of Intel
Corporation in the U.S. and/or other countries.

* Other names and brands may be claimed as the property of others.

OpenCL and the OpenCL logo are trademarks of Apple Inc. used by
permission from Khronos.

Copyright (c) 2014 Intel Corporation. All rights reserved.