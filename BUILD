load(
    "@org_tensorflow//tensorflow:tensorflow.bzl",
    "tf_cc_shared_object",
)

tf_cc_shared_object(
    name = "_XLAC.so",
    copts = [
        "-DTORCH_API_INCLUDE_EXTENSION_H",
        "-DTORCH_EXTENSION_NAME=_XLAC",
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
        "@org_tensorflow//tensorflow/compiler/xla/python/profiler/internal:traceme_wrapper",
        "@org_tensorflow//tensorflow/compiler/xla/python:xla_extension",
        "@org_tensorflow//tensorflow/compiler/xla/service:hlo_parser",
        "@org_tensorflow//tensorflow/compiler/xla/service:hlo_pass_pipeline",
        "@org_tensorflow//tensorflow/compiler/xla/service:hlo_verifier",
        "@org_tensorflow//tensorflow/compiler/xla/service:sharding_propagation",
        "@org_tensorflow//tensorflow/compiler/xla/service/spmd:spmd_partitioner",
        "@org_tensorflow//tensorflow/core",
        "@org_tensorflow//tensorflow/core:protos_all_cc",
        "@org_tensorflow//tensorflow/core/platform:env",
        "@org_tensorflow//tensorflow/core/profiler/lib:traceme",
        "@org_tensorflow//tensorflow/python/profiler/internal:profiler_pywrap_impl",
        "@torch//:headers",
        "@torch//:libc10",
        "@torch//:libtorch",
        "@torch//:libtorch_cpu",
        "@torch//:libtorch_python",
    ],
)
