# copy from "@xla//tensorflow:tensorflow.bzl",
load(
    "@tsl/tsl/platform/default:rules_cc.bzl",
    "cc_binary",
}
def ptxla_cc_shared_object(
        name,
        srcs = [],
        deps = [],
        data = [],
        linkopts = select({
            "@tsl//tsl:linux_aarch64": ["-lrt"],
            "@tsl//tsl:linux_x86_64": ["-lrt"],
            "@tsl//tsl:linux_ppc64le": ["-lrt"],
            "//conditions:default": [],
            }),
        framework_so = [], #tf_binary_additional_srcs(),
        soversion = None,
        kernels = [],
        per_os_targets = False,  # Generate targets with SHARED_LIBRARY_NAME_PATTERNS
        visibility = None,
        **kwargs):
    """Configure the shared object (.so) file for PyTorch/XLA."""
    if soversion != None:
        suffix = "." + str(soversion).split(".")[0]
        longsuffix = "." + str(soversion)
    else:
        suffix = ""
        longsuffix = ""

    if per_os_targets:
        names = [
            (
                pattern % (name, ""),
                pattern % (name, suffix),
                pattern % (name, longsuffix),
            )
            for pattern in SHARED_LIBRARY_NAME_PATTERNS
        ]
    else:
        names = [(
            name,
            name + suffix,
            name + longsuffix,
        )]
    # names = [(name, name, name)]

    testonly = kwargs.pop("testonly", False)

    for name_os, name_os_major, name_os_full in names:
        # Windows DLLs cant be versioned
        if name_os.endswith(".dll"):
            name_os_major = name_os
            name_os_full = name_os

        if name_os != name_os_major:
            native.genrule(
                name = name_os + "_sym",
                outs = [name_os],
                srcs = [name_os_major],
                output_to_bindir = 1,
                cmd = "ln -sf $$(basename $<) $@",
            )
            native.genrule(
                name = name_os_major + "_sym",
                outs = [name_os_major],
                srcs = [name_os_full],
                output_to_bindir = 1,
                cmd = "ln -sf $$(basename $<) $@",
            )

        soname = name_os_major.split("/")[-1]

        data_extra = []
        if framework_so != []:
            data_extra = tf_binary_additional_data_deps()

        # from tsl
        cc_binary(
            exec_properties = if_google({"cpp_link.mem": "16g"}, {}),
            name = name_os_full,
            srcs = srcs + framework_so,
            deps = deps,
            linkshared = 1,
            data = data + data_extra,
            linkopts = linkopts + _rpath_linkopts(name_os_full) + select({
                clean_dep("//tsl:ios"): [ # @tsl//tsl:ios
                    "-Wl,-install_name,@rpath/" + soname,
                ],
                clean_dep("//tsl:macos"): [ # @tsl//tsl:macos
                    "-Wl,-install_name,@rpath/" + soname,
                ],
                clean_dep("//tsl:windows"): [], # @tsl//tsl:windows
                "//conditions:default": [
                    "-Wl,-soname," + soname,
                ],
            }),
            testonly = testonly,
            visibility = visibility,
            **kwargs
        )

    flat_names = [item for sublist in names for item in sublist]
    if name not in flat_names:
        native.filegroup(
            name = name,
            srcs = select({
                clean_dep("//tsl:windows"): [":%s.dll" % (name)], # @tsl//tsl:windows
                clean_dep("//tsl:macos"): [":lib%s%s.dylib" % (name, longsuffix)], # @tsl//tsl:macos
                "//conditions:default": [":lib%s.so%s" % (name, longsuffix)],
            }),
            visibility = visibility,
            testonly = testonly,
        )
#####

# Bazel-generated shared objects which must be linked into TensorFlow binaries
# to define symbols from //tensorflow/core:framework and //tensorflow/core:lib.
VERSION = "2.13.0"
VERSION_MAJOR = VERSION.split(".")[0]
def tf_binary_additional_srcs(fullversion = False):
    if fullversion:
        suffix = "." + VERSION #.2.13.0
    else:
        suffix = "." + VERSION_MAJOR #.2

    return if_static(
        extra_deps = [],
        macos = [
            clean_dep("//tensorflow:libtensorflow_framework%s.dylib" % suffix),
            # //tensorflow:libtensorflow_framework.2.dylib
        ],
        otherwise = [
            clean_dep("//tensorflow:libtensorflow_framework.so%s" % suffix),
            # //tensorflow:libtensorflow_framework.so.2







SHARED_LIBRARY_NAME_PATTERN_LINUX = "lib%s.so%s"
SHARED_LIBRARY_NAME_PATTERN_MACOS = "lib%s%s.dylib"
SHARED_LIBRARY_NAME_PATTERN_WINDOWS = "%s%s.dll"
SHARED_LIBRARY_NAME_PATTERNS = [
    SHARED_LIBRARY_NAME_PATTERN_LINUX,
    SHARED_LIBRARY_NAME_PATTERN_MACOS,
    SHARED_LIBRARY_NAME_PATTERN_WINDOWS,
]



def tf_binary_additional_data_deps():
    return if_static(
        extra_deps = [],
        macos = [
            clean_dep("//tensorflow:libtensorflow_framework.dylib"),
            clean_dep("//tensorflow:libtensorflow_framework.%s.dylib" % VERSION_MAJOR),
            clean_dep("//tensorflow:libtensorflow_framework.%s.dylib" % VERSION),
        ],
        otherwise = [
            clean_dep("//tensorflow:libtensorflow_framework.so"),
            clean_dep("//tensorflow:libtensorflow_framework.so.%s" % VERSION_MAJOR),
            clean_dep("//tensorflow:libtensorflow_framework.so.%s" % VERSION),
        ],
    )

load(
    "//tensorflow/core/platform:rules_cc.bzl",
    "cc_binary",
    "cc_library",
    "cc_shared_library",
    "cc_test",
)
load(
    "//tensorflow/tsl/platform/default:rules_cc.bzl",
    _cc_binary = "cc_binary",
    _cc_import = "cc_import",
    _cc_library = "cc_library",
    _cc_shared_library = "cc_shared_library",
    _cc_test = "cc_test",
)