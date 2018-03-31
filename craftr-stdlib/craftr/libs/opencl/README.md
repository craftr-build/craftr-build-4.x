## craftr/libs/opencl

Generic build module for using with OpenCL from various vendors.

### Options

| Option | Description | Required | Default |
| ------ | ----------- | -------- | ------- |
| `:vendor` | The name of the OpenCL vendor, can be `pkg-config`, `amd`, `intel` or `nvidia`. | yes (Windows) | `pkg-config` (Linux) |
| `:intelSdk` | Used when `:vendor=intel`, the path to the Intel SDK. | no | `C:\Intel\OpenCL\sdk` (Windows) |

### Note

* `:vendor` is a required option on Windows &ndash; not setting it causes an error.
* `:vendor=amd` is currently not implemented.
* Using `:vendor=nvidia` uses the `craftr/libs/cuda` module. Check this module
  for options to influence the OpenCL build when using the NVidia OpenCL SDK.

### Resources

* [OpenCL: Graphics Interop](http://sa10.idav.ucdavis.edu/docs/sa10-dg-opencl-gl-interop.pdf)
