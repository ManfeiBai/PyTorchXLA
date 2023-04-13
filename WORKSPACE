load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# To update OpenXLA to a new revision,
# a) update URL and strip_prefix to the new git commit hash
# b) get the sha256 hash of the commit by running:
#    curl -L https://github.com/openxla/xla/archive/<git hash>.tar.gz | sha256sum
#    and update the sha256 with the result.
http_archive(
    name = "xla",
    <!-- patch_args = [
        "-l",
        "-p1",
    ],
    patch_tool = "patch",
    patches = [
        "//openxla_patches:cache_urls.diff",
        "//openxla_patches:cudnn_int8x32.diff",
        "//openxla_patches:f16_abi_clang.diff",
        "//openxla_patches:gpu_race_condition.diff",
        "//openxla_patches:grpc_version.diff",
        "//openxla_patches:stream_executor.diff",
        "//openxla_patches:thread_local_random.diff",
        "//openxla_patches:xplane.diff",
    ], -->
    sha256 = "15a91b3ea25f51037adb11edc7b7fe94e6ab83219fce803c621f7a58ea934c29",
    strip_prefix = "xla-8c0a24805ae5a88bebd9ac53f7f20f78dabc1cc2",
    strip_prefix = "tensorflow-f7759359f8420d3ca7b9fd19493f2a01bd47b4ef",
    urls = [
        "https://github.com/openxla/xla/archive/8c0a24805ae5a88bebd9ac53f7f20f78dabc1cc2.tar.gz",
    ],
)

# For development, one often wants to make changes to the TF repository as well
# as the PyTorch/XLA repository. You can override the pinned repository above with a
# local checkout by either:
# a) overriding the TF repository on the build.py command line by passing a flag
#    like:
#    bazel --override_repository=xla=/path/to/xla
#    or
# b) by commenting out the http_archive above and uncommenting the following:
# local_repository(
#    name = "xla",
#    path = "/path/to/xla",
# )

# Initialize TensorFlow's external dependencies.
load("@xla//:workspace4.bzl", "xla_workspace4")

xla_workspace4()

load("@xla//:workspace3.bzl", "xla_workspace3")

xla_workspace3()

load("@xla//:workspace2.bzl", "xla_workspace2")

xla_workspace2()

load("@xla//:workspace1.bzl", "xla_workspace1")

xla_workspace1()

load("@xla//:workspace0.bzl", "xla_workspace0")

xla_workspace0()
