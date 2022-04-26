#pragma once

#include <ATen/core/interned_strings.h>

#include <functional>
#include <iostream>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "absl/hash/hash.h"
#include "absl/types/span.h"
#include "tensorflow/compiler/xla/client/xla_builder.h"
#include "tensorflow/compiler/xla/xla_client/types.h"
#include "tensorflow/core/lib/gtl/inlined_vector.h"
#include "torch/csrc/lazy/core/hash.h"
#include "torch/csrc/lazy/core/ir.h"

namespace torch_xla {
namespace ir {

static const uint32_t default_hash_seed = (uint32_t)0x5a2d296e9;

class Node;
class LoweringContext;

using XlaOpVector = tensorflow::gtl::InlinedVector<xla::XlaOp, 1>;

template <typename T>
using OutputMap =
    std::unordered_map<torch::lazy::Output, T, torch::lazy::Output::Hasher>;

// Represents an input/operand for a Node object.
struct Value : public torch::lazy::Value {
  Value() = default;
  Value(torch::lazy::NodePtr node, size_t index = 0)
      : torch::lazy::Value(std::dynamic_pointer_cast<torch::lazy::Node>(node),
                           index) {}

  // Retrieves the shape of this value. If the IR Node generating the value is a
  // multi-output node, the shape returned by this API will not be the full
  // tuple shape, but only the shape at index referred by this value.
  // To retrieve the full tuple shape in that case, use the node_shape() API.
  const xla::Shape& xla_shape() const;
  const xla::Shape& xla_node_shape() const;
};

using OpList = absl::Span<const Value>;

// A node in the graph. Nodes for operations which requires extra data to be
// stored for lowering, should inherit from this class and add operation
// specific member there. For example, a constant might create a new
// NodeConstant class (inheriting from Node) with an extra xla::Literal field,
// or a tensor value might create a new NodeTensor with computation client data
// handle in it.
class Node : public torch::lazy::Node {
 public:
  // Creates a new node with the given op name. The op is a unique identifier
  // for the operation. The num_outputs tells how many outputs a given operation
  // generates.
  Node(torch::lazy::OpKind op, OpList operands,
       std::vector<torch::lazy::Shape>&& shapes, xla::Shape xla_shape,
       size_t num_outputs = 1,
       torch::lazy::hash_t hash_seed = default_hash_seed);

  Node(torch::lazy::OpKind op, OpList operands, torch::lazy::Shape shape,
       xla::Shape xla_shape, size_t num_outputs = 1,
       torch::lazy::hash_t hash_seed = default_hash_seed);

  // Legacy constructor that does not handle torch::lazy::shape.
  Node(torch::lazy::OpKind op, OpList operands, xla::Shape shape,
       size_t num_outputs = 1,
       torch::lazy::hash_t hash_seed = default_hash_seed);

  // Same as the constructor above, but the shape is generated by a function,
  // only if needed (shape cache miss).
  Node(torch::lazy::OpKind op, OpList operands,
       const std::function<torch::lazy::Shape()>& shape_fn,
       const std::function<xla::Shape()>& xla_shape_fn, size_t num_outputs = 1,
       torch::lazy::hash_t hash_seed = default_hash_seed);

  // Legacy constructor that does not handle torch::lazy::shape.
  Node(torch::lazy::OpKind op, OpList operands,
       const std::function<xla::Shape()>& xla_shape_fn, size_t num_outputs = 1,
       torch::lazy::hash_t hash_seed = default_hash_seed);

  // Contructor used to create leaf nodes.
  Node(torch::lazy::OpKind op, torch::lazy::Shape shape, xla::Shape xla_shape,
       size_t num_outputs, torch::lazy::hash_t hash_seed);

  // Legacy constructor that does not handle torch::lazy::shape.
  Node(torch::lazy::OpKind op, xla::Shape xla_shape, size_t num_outputs,
       torch::lazy::hash_t hash_seed);

  virtual ~Node();

  // Retrieves the full shape of the IR Node. Note that if this is a
  // multi-output node, the returned shape will be a tuple.
  const xla::Shape& xla_shape() const { return xla_shape_; }

  // Retrieves the shape of the output at a given index. If the node is not a
  // multi-output node, output_index must be zero.
  const xla::Shape& xla_shape(size_t output_index) const;

  virtual torch::lazy::NodePtr Clone(OpList operands) const;

  virtual XlaOpVector Lower(LoweringContext* loctx) const;

  XlaOpVector ReturnOp(xla::XlaOp op, LoweringContext* loctx) const;

  XlaOpVector ReturnOps(absl::Span<const xla::XlaOp> ops,
                        LoweringContext* loctx) const;

  torch::lazy::hash_t node_hash() const { return node_hash_; }

  torch::lazy::hash_t hash() const override { return dag_hash_; }

  torch::lazy::hash_t shapeHash() const override { return dag_hash_; }

 private:
  xla::Shape GetOpShape(const std::function<xla::Shape()>& shape_fn) const;

  static torch::lazy::hash_t GetOpHash(torch::lazy::OpKind op,
                                       const xla::Shape& shape,
                                       torch::lazy::hash_t hash_seed);

  static std::vector<torch::lazy::SourceLocation> GetFrameInfo();

  xla::Shape xla_shape_;
  torch::lazy::hash_t node_hash_;
  torch::lazy::hash_t dag_hash_;
};

// RAII data structure to be used a stack variable to enter a new IR scope. IR
// scope names will appear in the IR and will help identifying the source of the
// single IR nodes.
struct ScopePusher {
  explicit ScopePusher(const std::string& name);
  ~ScopePusher();

  static void ResetScopes();
};

inline std::ostream& operator<<(std::ostream& stream, const Node& node) {
  stream << node.ToString();
  return stream;
}

template <typename T, typename... Args>
torch::lazy::NodePtr MakeNode(Args&&... args) {
  return std::make_shared<T>(std::forward<Args>(args)...);
}

template <typename T>
T* NodeCast(const torch::lazy::Node* node, torch::lazy::OpKind op) {
  if (op != node->op()) {
    return nullptr;
  }
  const T* casted;
#ifdef NDEBUG
  casted = static_cast<const T*>(node);
#else
  casted = &dynamic_cast<const T&>(*node);
#endif
  return const_cast<T*>(casted);
}

}  // namespace ir
}  // namespace torch_xla
