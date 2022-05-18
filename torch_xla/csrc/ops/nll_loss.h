#pragma once

#include "absl/types/optional.h"
#include "torch_xla/csrc/ir.h"
#include "torch_xla/csrc/reduction.h"

namespace torch_xla {

class NllLoss : public XlaNode {
 public:
  NllLoss(const torch::lazy::Value& logits, const torch::lazy::Value& labels,
          const absl::optional<torch::lazy::Value>& weight,
          ReductionMode reduction, int ignore_index);

  std::string ToString() const override;

  torch::lazy::NodePtr Clone(OpList operands) const override;

  XlaOpVector Lower(LoweringContext* loctx) const override;

  ReductionMode reduction() const { return reduction_; }

  int ignore_index() const { return ignore_index_; }

 private:
  ReductionMode reduction_;
  int ignore_index_;
};

}  // namespace torch_xla
