

#pragma OPENCL_EXTENSION cl_khr_gl_sharing : enable

#if defined(cl_khr_fp64)  // Khronos extension available?
    #pragma OPENCL EXTENSION cl_khr_fp64 : enable
    #define DOUBLE_SUPPORT_AVAILABLE
#elif defined(cl_amd_fp64)  // AMD extension available?
    #pragma OPENCL EXTENSION cl_amd_fp64 : enable
    #define DOUBLE_SUPPORT_AVAILABLE
#else
    #error "Double not supported"
#endif

typedef double2 Complex;

Complex multiply(Complex a, Complex b) {
    return (Complex)(a.s0*b.s0-a.s1*b.s1, a.s1*b.s0+a.s0*b.s1);
}

float normalized_iterations(int n, Complex zn, int bailout) {
    return n + (log(log(convert_float(bailout)))-log(log(length(zn))))/log(2.0f);
}

float boundedorbit(Complex seed, Complex c, float bound, int bailout) {
    Complex z = multiply(seed, seed) + c;
    for (int k = 0; k < bailout; k++) {
        if (length(z) > bound)
            return normalized_iterations(k, z, bailout);
        z = multiply(z, z) + c;
    }
    return FLT_MIN;
}

unsigned char grayvalue(float n) {
    return convert_uchar_sat_rte(n);
}


__kernel void mandelbrot(
    __write_only image2d_t out,
    unsigned int width,
    unsigned int height,
    float offsetx,
    float offsety,
    float zoom,
    float bound, /* = 2.0f */
    int bailout /* = 200 */
){
    float x = get_global_id(0) / (float) width;
    float y = get_global_id(1) / (float) height;

    Complex c = (Complex)((-2.5 + 3.5 * x) * zoom + offsetx, (-1.25 + 2.5 * y) * zoom + offsety);
    float count = boundedorbit((0, 0), c, 2.0, bailout);
    float value = grayvalue(count) / 255.0f;

    int2 coord = (int2)(get_global_id(0), get_global_id(1));
    write_imagef(out, coord, (float4)(value, 0.0, 0.0, 1.0));
}
