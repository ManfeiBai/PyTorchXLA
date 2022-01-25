#pragma once

#include "torch_xla/csrc/ir.h"

namespace torch_xla {
namespace ir {
namespace ops {

class TopK : public Node {
 public:
  TopK(const Value& input, xla::int64_t k, xla::int64_t dim, bool largest,
       bool sorted, bool stable);

  std::string ToString() const override;

  NodePtr Clone(OpList operands) const override;

  XlaOpVector Lower(LoweringContext* loctx) const override;

  xla::int64_t k() const { return k_; };

  xla::int64_t dim() const { return dim_; };

  bool largest() const { return largest_; }

  bool sorted() const { return sorted_; }

  bool stable() const { return stable_; }

 private:
  xla::int64_t k_;
  xla::int64_t dim_;
  bool largest_;
  bool sorted_;
  bool stable_;
};

}  // namespace ops
}  // namespace ir
}  // namespace torch_xla
