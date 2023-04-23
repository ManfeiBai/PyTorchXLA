#pragma once

#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>

#include "c10/core/SymNodeImpl.h"
#include "tensorflow/compiler/xla/client/xla_builder.h"
#include "tensorflow/compiler/xla/status.h"
#include "tensorflow/compiler/xla/types.h"
#include "tensorflow/compiler/xla/xla_client/async_task.h"
#include "tensorflow/compiler/xla/xla_client/cache.h"
#include "tensorflow/compiler/xla/xla_client/computation_client.h"
#include "tensorflow/compiler/xla/xla_client/multi_wait.h"
#include "tensorflow/compiler/xla/xla_client/util.h"
#include "torch/csrc/autograd/variable.h"
#include "torch/csrc/lazy/core/ir_util.h"
#include "torch_xla/csrc/computation.h"
#include "torch_xla/csrc/cross_replica_reduces.h"
#include "torch_xla/csrc/device.h"
#include "torch_xla/csrc/ir.h"
#include "torch_xla/csrc/ir_util.h"
#include "torch_xla/csrc/lowering_context.h"
#include "torch_xla/csrc/torch_util.h"
#include "torch_xla/csrc/view.h"

namespace torch_xla {

class TORCH_API XLASymNodeImpl : public c10::SymNodeImpl {
 public:
  XLASymNodeImpl(torch::lazy::NodePtr ptr) : node_(std::move(ptr)) {}
  bool is_int() override;
  bool is_float() override;
  c10::SymNode eq(const c10::SymNode& other) override;
  c10::SymNode add(const c10::SymNode& other) override;
  c10::SymNode mul(const c10::SymNode& other) override;
  c10::SymNode floordiv(const c10::SymNode& other) override;
  c10::SymNode wrap_int(int64_t num) override;

  torch::lazy::NodePtr node() { return node_; }
  std::string str() override;

  bool bool_() override;
  int64_t int_() override;

 private:
  torch::lazy::NodePtr node_;
};

class XLATensor;
using XLATensorPtr = c10::intrusive_ptr<XLATensor>;

class XLATensor : public torch::lazy::LazyTensor {
 public:
  // This is the core XLA tensor data structure where all the tensor data is
  // held. The XLA tensor is nothing more than a shared pointer to a Data
  // object.
  struct Data {
    Data(torch::lazy::BackendDataPtr xla_data,
         const torch::lazy::BackendDevice& device,
         c10::optional<at::ScalarType> logical_element_type)
        : xla_data(std::move(xla_data)),
          logical_element_type(logical_element_type),
          device(device),
          unique_id(GetNextTensorId()) {}
    Data(torch::lazy::Value ir_value, const torch::lazy::BackendDevice& device,
         c10::optional<at::ScalarType> logical_element_type)
        : ir_value(std::move(ir_value)),
          logical_element_type(logical_element_type),
          device(device),
          unique_id(GetNextTensorId()) {}
    Data(std::shared_ptr<View> view, const torch::lazy::BackendDevice& device,
         c10::optional<at::ScalarType> logical_element_type)
        : view(std::move(view)),
          logical_element_type(logical_element_type),
          device(device),
          unique_id(GetNextTensorId()) {}
    Data(at::Tensor tensor_data, const torch::lazy::BackendDevice& device)
        : logical_element_type(tensor_data.scalar_type()),
          tensor_data(std::move(tensor_data)),
          device(device),
          unique_id(GetNextTensorId()) {}

    ~Data();

    torch::lazy::BackendDataPtr xla_data;
    torch::lazy::Value ir_value;
    std::shared_ptr<View> view;
    // TODO: remove this in favor of torch::lazy::Shape within ir_value.
    c10::optional<at::ScalarType> logical_element_type;
    c10::optional<at::Tensor> tensor_data;
    const torch::lazy::BackendDevice device;
    const int64_t unique_id = 0;
    size_t generation = 1;
  };

  static XLATensorPtr Create(const at::Tensor& tensor,
                             const torch::lazy::BackendDevice& device);
  static XLATensorPtr Create(
      torch::lazy::BackendDataPtr xla_data,
      c10::optional<at::ScalarType> logical_element_type = c10::nullopt);

  static XLATensorPtr Create(
      torch::lazy::Value ir_value, const torch::lazy::BackendDevice& device,
      c10::optional<at::ScalarType> logical_element_type = c10::nullopt);

  // Create a new XLA tensor with the same metadata of the input tensor (with
  // possible overrides), and the new IR value.
  XLATensorPtr CreateFrom(torch::lazy::Value ir_value) const;
  XLATensorPtr CreateFrom(
      torch::lazy::Value ir_value,
      c10::optional<at::ScalarType> logical_element_type_opt) const;
  // TODO: We should remove this one once MaybeCastIrValue is no longer needed.
  XLATensorPtr CreateFrom(torch::lazy::Value ir_value,
                          const torch::lazy::BackendDevice& device,
                          at::ScalarType logical_element_type) const;

  // The default ctor previously created a null LazyTensor (one with no 'data'
  // obj). Creating a null XLATensor is no longer possible, since the same can
  // be achieved by creating a null LazyTensorPtr and it is way too confusing to
  // have to check both lazy_tensor_ptr && *lazy_tensor_ptr, so everywhere that
  // used to rely on a LazyTensor obj with a null Data can now rely on a null
  // LazyTensorPtr instead.
  XLATensor() = delete;

  size_t generation() const { return data()->generation; }

  XLATensorPtr alias() const {
    return c10::make_intrusive<XLATensor>(XLATensor(data_ptr()));
  }

  int64_t size(int64_t dim) const;

  at::Tensor ToTensor(bool detached);

  void ShallowCopyTo(XLATensorPtr dest) const;

  // Assigns the tensor value to the XLA tensor.
  void SetTensor(at::Tensor tensor);

  void UpdateFromTensor(at::Tensor tensor, bool sync);
  void UpdateFromTensorOut(at::Tensor tensor);
  void UpdateFromTensorOut(const XLATensorPtr& tensor);

  at::ScalarType dtype() const;
  c10::optional<at::ScalarType> dtype_optional() const;

  // Set logical_element_type which is visible to upstream PyTorch.
  void SetScalarType(c10::optional<at::ScalarType> logical_element_type);

  xla::util::MaybeRef<xla::Shape> shape() const;

  const torch::lazy::BackendDevice& GetDevice() const;
  int64_t GetUniqueId() const;

  // Retrieves an opaque ID of the alias object upon which the tensor's view is
  // rooted, or 0 if this tensor is not a view.
  std::ptrdiff_t GetViewAliasId() const;

  // Fetches the XLA data behind the tensor. If the tensor has a graph defining
  // its current value, executes the graph and fetches the XLA data result.
  torch::lazy::BackendDataPtr GetXlaData();

  // Fetches the current value of the XLA data, which can be missing (nullptr)
  // in case the tensor has a graph defining its current value,
  torch::lazy::BackendDataPtr CurrentXlaData() const;

  void SetXlaData(torch::lazy::BackendDataPtr xla_data);

  // Retrieves the current IR XlaNode, or nullptr in case no active IR XlaNode
  // is available.
  torch::lazy::Value CurrentIrValue() const;

  // Retrieves the IR Node representing this XLATensor. One will be created if
  // missing. Note that although this is a const API, it actually changes the
  // internal state of the object.
  torch::lazy::Value GetIrValue() const;

  void SetIrValue(torch::lazy::Value ir_value, bool inplace = true);
  void SetInPlaceIrValue(torch::lazy::Value ir_value);

  c10::optional<at::Tensor> CurrentTensorData() const;

  std::vector<XLATensorPtr> MakeOutputTensors(
      torch::lazy::NodePtr node, bool inherit_logical_type = true) const;

  void SetSubView(ViewInfo view_info) const;
  void ModifyCurrentView(ViewInfo view_info) const;
  XLATensorPtr CreateViewTensor(ViewInfo view_info) const;

  XLATensorPtr CopyTensorToDevice(const torch::lazy::BackendDevice& device);

  // Applies the queue of operations in preparation for using the data.
  void ApplyPendingGraph();

  Data* data() const;

  // XLA SPMD sharding spec annoation. The XLA tensor uses this to create
  // HloSharding for replication, manual and tile shardings.
  struct ShardingSpec {
    ShardingSpec(const xla::OpSharding& sharding) : sharding(sharding) {}

    xla::OpSharding sharding;
  };
  using ShardingSpecPtr = std::shared_ptr<ShardingSpec>;

  // Annotate the IR value with ShardingSpec.
  void SetShardingSpec(const ShardingSpec& sharding_spec);
  // Clear sharding annotation attached to the IR value and transfer sharded
  // data back to host.
  void ClearShardingSpec();
  ShardingSpecPtr sharding_spec() const;

  void SetStorage(const c10::Storage& storage) { storage_ = storage; }
  const c10::Storage& Storage() const { return storage_; }

  int64_t GetOpaqueHandle() const;

 private:
  XLATensor(const at::Tensor& tensor, const torch::lazy::BackendDevice& device);
  XLATensor(torch::lazy::BackendDataPtr xla_data,
            c10::optional<at::ScalarType> logical_element_type = c10::nullopt);
  XLATensor(torch::lazy::Value ir_value,
            const torch::lazy::BackendDevice& device,
            c10::optional<at::ScalarType> logical_element_type = c10::nullopt);
  XLATensor(std::shared_ptr<View> view,
            const torch::lazy::BackendDevice& device,
            c10::optional<at::ScalarType> logical_element_type = c10::nullopt);

  // TODO: This is temporarily until we fully inherit LazyTensor and
  // LazyGraphExecutor.
 public:
  XLATensor(std::shared_ptr<Data> data);

 private:
  static XLATensorPtr Create(
      std::shared_ptr<View> view, const torch::lazy::BackendDevice& device,
      c10::optional<at::ScalarType> logical_element_type = c10::nullopt);

  std::shared_ptr<Data> data_ptr() const { return data_; }

  void SetXlaData(torch::lazy::BackendDataPtr xla_data, bool sync);

  void AssignIrValue(torch::lazy::Value ir_value) const;

  void SetTensorData(at::Tensor tensor_data);

  torch::lazy::Value CreateTensorNode(torch::lazy::BackendDataPtr data,
                                      bool read_only) const;

  View::IrNode GetViewUpdate(const std::shared_ptr<View>& view) const;

  std::shared_ptr<View> UpdateView(std::shared_ptr<View> view,
                                   torch::lazy::Value ir_value) const;

  std::shared_ptr<View> CreateView(ViewInfo view_info) const;

  torch::lazy::Value MaybeCastIrValue(
      torch::lazy::Value ir_value, const torch::lazy::BackendDevice& device,
      c10::optional<at::ScalarType> logical_element_type) const;

  // We build an XLA graph accumulating XLA operations, but at a given point we
  // need to force a rendering, otherwise the graph can grow without control.
  // Think:
  //   for i in range(0, 100000):
  //     a = a + b
  void TryLimitGraphSize();

  torch::lazy::Value GetIrValueForTensor(
      const at::Tensor& tensor, const torch::lazy::BackendDevice& device) const;

  static int64_t GetNextTensorId();

  static bool UseEagerDebugMode();

  bool ShouldSyncIrNode();

  std::shared_ptr<Data> data_;
  // Temporarily used to suport Tensor.is_alias_of().
  // This is a fake storage that doesn't store anything.
  // Instead it serves as a marker to mark LazyTensors that
  // points to the same storage, and thus alias of each other.
  // FIXME(alanwaketan): Remove this once we have functionalization (bdhirsh).
  c10::Storage storage_;

  // TODO: This is temporarily until we fully inherit LazyTensor and
  // LazyGraphExecutor.
  friend class XLAGraphExecutor;
};

}  // namespace torch_xla
