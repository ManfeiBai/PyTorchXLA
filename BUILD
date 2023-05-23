load("@tsl//tsl/platform:rules_cc.bzl", "cc_library")


cc_binary(
    name = "_XLAC.so",
    copts = [
        "-DTORCH_API_INCLUDE_EXTENSION_H",
        "-DTORCH_EXTENSION_NAME=_XLAC",
        "-DC10_USING_CUSTOM_GENERATED_MACROS",
        "-fopenmp",
        "-fPIC",
        "-fwrapv",
    ],
    linkopts = [
        "-Wl,-rpath,$$ORIGIN/torch_xla/lib",  # for libtpu
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//third_party/xla_client:computation_client",
        "//third_party/xla_client:mesh_service",
        "//third_party/xla_client:metrics",
        "//third_party/xla_client:metrics_analysis",
        "//third_party/xla_client:metrics_reader",
        "//third_party/xla_client:multi_wait",
        "//third_party/xla_client:profiler",
        "//third_party/xla_client:record_reader",
        "//third_party/xla_client:sys_util",
        "//third_party/xla_client:thread_pool",
        "//third_party/xla_client:util",
        "//third_party/xla_client:xla_util",
        "//torch_xla/csrc:computation",
        "//torch_xla/csrc:device",
        "//torch_xla/csrc:init_python_bindings",
        "//torch_xla/csrc:tensor",
        "//torch_xla/csrc:version",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/strings",
        "@com_google_absl//absl/types:variant",
        "@xla//xla/python/profiler/internal:traceme_wrapper",
        "@xla//xla/service:hlo_parser",
        "@xla//xla/service:hlo_pass_pipeline",
        "@xla//xla/service:hlo_verifier",
        "@xla//xla/service:sharding_propagation",
        "@xla//xla/service/spmd:spmd_partitioner",
#         "@org_tensorflow//tensorflow/core",
#         "@org_tensorflow//tensorflow/core:protos_all_cc",
#         "@org_tensorflow//tensorflow/core/platform:env",
#         "@org_tensorflow//tensorflow/core/profiler/lib:traceme",
#         "@org_tensorflow//tensorflow/python/profiler/internal:profiler_pywrap_impl",
        "@torch//:headers",
        "@torch//:libc10",
        "@torch//:libtorch",
        "@torch//:libtorch_cpu",
        "@torch//:libtorch_python",
    ],
)
