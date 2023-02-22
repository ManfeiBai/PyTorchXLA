load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# To update TensorFlow to a new revision,
# a) update URL and strip_prefix to the new git commit hash
# b) get the sha256 hash of the commit by running:
#    curl -L https://github.com/tensorflow/tensorflow/archive/<git hash>.tar.gz | sha256sum
#    and update the sha256 with the result.
http_archive(
    name = "org_tensorflow",
    patch_args = [
        "-l",
        "-p1",
    ],
    patch_tool = "patch",
    patches = [
        "//tf_patches:bazel.diff",
        "//tf_patches:cache_urls.diff",
        "//tf_patches:cudnn_int8x32.diff",
        "//tf_patches:f16_abi_clang.diff",
        "//tf_patches:gpu_race_condition.diff",
        "//tf_patches:grpc_version.diff",
        "//tf_patches:stream_executor.diff",
        "//tf_patches:thread_local_random.diff",
        "//tf_patches:xplane.diff",
    ],
    sha256 = "0fdf5067cd9827be2ae14c2ac59cd482e678134b125943be278ad23ea5342181",
    strip_prefix = "tensorflow-f7759359f8420d3ca7b9fd19493f2a01bd47b4ef",
    urls = [
        "https://github.com/tensorflow/tensorflow/archive/f7759359f8420d3ca7b9fd19493f2a01bd47b4ef.tar.gz",
    ],
)

# For development, one often wants to make changes to the TF repository as well
# as the PyTorch/XLA repository. You can override the pinned repository above with a
# local checkout by either:
# a) overriding the TF repository on the build.py command line by passing a flag
#    like:
#    bazel --override_repository=org_tensorflow=/path/to/tensorflow
#    or
# b) by commenting out the http_archive above and uncommenting the following:
# local_repository(
#    name = "org_tensorflow",
#    path = "/path/to/tensorflow",
# )

# Initialize TensorFlow's external dependencies.
load("@org_tensorflow//tensorflow:workspace3.bzl", "tf_workspace3")

tf_workspace3()

load("@org_tensorflow//tensorflow:workspace2.bzl", "tf_workspace2")

tf_workspace2()

load("@org_tensorflow//tensorflow:workspace1.bzl", "tf_workspace1")

tf_workspace1()

load("@org_tensorflow//tensorflow:workspace0.bzl", "tf_workspace0")

tf_workspace0()

# OpenXLA
# To update OpenXLA to a new revision,
# a) update URL and strip_prefix to the new git commit hash
# b) get the sha256 hash of the commit by running:
#    curl -L https://github.com/tensorflow/tensorflow/archive/<git hash>.tar.gz | sha256sum
#    and update the sha256 with the result.
## b200756333d3cddba095de50725c987308c626ea
http_archive(
    name = "org_openxla",
    patch_args = [
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
    ],
    sha256 = "7b9c06d0c034b169f93359196a14014fb6abe35c782283dd7e602bb439a9c14b",
    strip_prefix = "openxla-8faf3d859c0d8ca9fc8b6ce56836c705a94d4265",
    urls = ["https://github.com/openxla/xla/archive/8faf3d859c0d8ca9fc8b6ce56836c705a94d4265.tar.gz"],
)

# Initialize OpenXLA's external dependencies.
load("@org_openxla//openxla:workspace4.bzl", "openxla_workspace4")

openxla_workspace3()

load("@org_openxla//openxla:workspace3.bzl", "openxla_workspace3")

openxla_workspace3()

load("@org_openxla//openxla:workspace2.bzl", "openxla_workspace2")

openxla_workspace2()

load("@org_openxla//openxla:workspace1.bzl", "openxla_workspace1")

openxla_workspace1()

load("@org_openxla//openxla:workspace0.bzl", "openxla_workspace0")

openxla_workspace0()